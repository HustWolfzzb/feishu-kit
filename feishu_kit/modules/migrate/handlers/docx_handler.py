"""docx 文档迁移处理器 — blocks 递归复制 + image/file 绑定"""

from __future__ import annotations

import asyncio
import os
import struct
import tempfile
from collections import Counter
from typing import Any

from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.migrate.handlers import BaseHandler
from feishu_kit.modules.wiki.service import WikiService

# ── Block 类型常量 ──────────────────────────────────────────────────

BLOCK_TYPE_NAMES = {
    1: "page", 2: "text", 3: "heading1", 4: "heading2", 5: "heading3",
    6: "heading4", 7: "heading5", 8: "heading6",
    9: "heading7", 10: "heading8", 11: "heading9",
    12: "bullet", 13: "ordered", 14: "code", 15: "quote",
    16: "todo", 17: "todo", 18: "callout",
    23: "file", 24: "grid_column", 25: "embed",
    27: "image", 31: "table", 32: "table_cell",
    33: "view", 34: "grid",
}

# 不支持通过 API 创建但可以尝试的容器类型
UNSUPPORTED_CONTAINER_TYPES = {24, 25, 30, 33, 34, 36, 37, 39, 40, 43, 44}

# 速率控制
BATCH_SIZE = 10
DELAY_BATCH = 1.5
DELAY_PAGE = 0.4
DELAY_CREATE = 2.0


# ── 工具函数 ──────────────────────────────────────────────────────────

def detect_format(data: bytes) -> str:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:2] == b"\xff\xd8":
        return "jpg"
    if data[:4] == b"GIF8":
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    if data[:5] == b"%PDF-" or data[:4] == b"\x25\x50\x44\x46":
        return "pdf"
    return "bin"


def clean_block_for_create(block: dict) -> dict:
    cleaned = {}
    for k, v in block.items():
        if k in ("block_id", "parent_id", "children"):
            continue
        cleaned[k] = v
    return cleaned


async def retry(coro_factory, max_retries=6, label="API"):
    for attempt in range(max_retries):
        result = await coro_factory()
        if not isinstance(result, dict):
            return result
        code = result.get("code", 0)
        if code in (1061046, 131009) or "429" in str(result):
            wait = min(5 * (2 ** attempt), 120)
            await asyncio.sleep(wait)
            continue
        return result
    return {"code": -1, "msg": "max retries exceeded"}


async def fetch_all_blocks(wiki: WikiService, obj_token: str) -> list[dict]:
    all_blocks = []
    page_token = None
    while True:
        resp = await wiki.get_doc_blocks(obj_token, page_size=50, page_token=page_token)
        items = resp.get("data", {}).get("items", [])
        all_blocks.extend(items)
        page_token = resp.get("data", {}).get("page_token")
        if not page_token or not items:
            break
        await asyncio.sleep(DELAY_PAGE)
    return all_blocks


def build_block_tree(all_blocks: list[dict]) -> tuple[str, dict[str, list[dict]]]:
    if not all_blocks:
        return "", {}
    page_id = all_blocks[0].get("block_id", "")
    children_map: dict[str, list[dict]] = {}
    for b in all_blocks[1:]:
        pid = b.get("parent_id", "")
        if pid:
            children_map.setdefault(pid, []).append(b)
    return page_id, children_map


# ── 资源下载 ──────────────────────────────────────────────────────────

async def download_resources(
    wiki: WikiService, blocks: list[dict], tmp_dir: str,
) -> dict[str, dict]:
    resources = {}
    for block in blocks:
        bt = block.get("block_type")
        bid = block.get("block_id", "")
        file_token = ""
        file_name = ""
        res_type = ""

        if bt == 27:
            file_token = block.get("image", {}).get("token", "")
            res_type = "image"
        elif bt == 23:
            fi = block.get("file", {})
            file_token = fi.get("token", "")
            file_name = fi.get("name", "")
            res_type = "file"
        else:
            continue

        if not file_token:
            continue

        try:
            data = await wiki.download_media(file_token)
            fmt = detect_format(data)
            if res_type == "image":
                ext = fmt if fmt in ("png", "jpg", "gif", "webp") else "png"
                local_name = f"img_{bid}.{ext}"
            else:
                local_name = f"file_{bid}_{file_name}" if file_name else f"file_{bid}.{fmt}"

            local_path = os.path.join(tmp_dir, local_name)
            with open(local_path, "wb") as f:
                f.write(data)

            resources[bid] = {
                "local_path": local_path,
                "file_name": local_name,
                "original_name": file_name or local_name,
                "resource_type": res_type,
                "size": len(data),
                "format": fmt,
                "original_token": file_token,
            }
        except Exception:
            pass

        await asyncio.sleep(0.5)

    return resources


# ── 上传 & 绑定 ──────────────────────────────────────────────────────

async def upload_to_block(
    client: FeishuClient, block_id: str,
    file_name: str, file_data: bytes, parent_type: str,
) -> str | None:
    resp = await client.upload(
        "/drive/v1/medias/upload_all",
        file_name=file_name,
        file_data=file_data,
        fields={
            "file_name": file_name,
            "parent_type": parent_type,
            "parent_node": block_id,
            "size": str(len(file_data)),
        },
    )
    if resp.get("code") == 0:
        return resp["data"]["file_token"]
    return None


async def create_and_bind_image(
    wiki: WikiService, client: FeishuClient,
    obj_token: str, parent_block_id: str,
    file_name: str, file_data: bytes,
) -> tuple[str, bool]:
    r = await retry(
        lambda: wiki.create_doc_block(obj_token, parent_block_id, [
            {"block_type": 27, "image": {}}
        ]),
        label=f"create_image:{file_name[:20]}",
    )
    if r.get("code") != 0:
        return "", False

    items = r.get("data", {}).get("children", [])
    block_id = items[0].get("block_id", "") if items else ""
    if not block_id:
        return "", False

    await asyncio.sleep(0.8)

    token = await upload_to_block(client, block_id, file_name, file_data, "docx_image")
    if not token:
        return block_id, False

    await asyncio.sleep(0.5)
    rr = await wiki.update_block(obj_token, block_id, {"replace_image": {"token": token}})
    return block_id, rr.get("code") == 0


async def create_and_bind_file(
    wiki: WikiService, client: FeishuClient,
    obj_token: str, parent_block_id: str,
    file_name: str, file_data: bytes,
) -> tuple[str, str, bool]:
    r = await retry(
        lambda: wiki.create_doc_block(obj_token, parent_block_id, [
            {"block_type": 23, "file": {}}
        ]),
        label=f"create_file:{file_name[:20]}",
    )
    if r.get("code") != 0:
        return "", "", False

    items = r.get("data", {}).get("children", [])
    top_bid = items[0].get("block_id", "") if items else ""
    top_bt = items[0].get("block_type", 0) if items else 0

    view_block_id = None
    file_block_id = ""

    if top_bt == 33:
        view_block_id = top_bid
        view_children_ids = items[0].get("children", [])
        if view_children_ids:
            file_block_id = view_children_ids[0]
        else:
            await asyncio.sleep(1.0)
            all_blocks = await fetch_all_blocks(wiki, obj_token)
            inner = [b for b in all_blocks
                     if b.get("parent_id") == view_block_id and b.get("block_type") == 23]
            file_block_id = inner[0]["block_id"] if inner else ""
    else:
        file_block_id = top_bid

    if not file_block_id:
        return view_block_id or "", "", False

    await asyncio.sleep(0.8)

    token = await upload_to_block(client, file_block_id, file_name, file_data, "docx_file")
    if not token:
        return view_block_id or "", file_block_id, False

    await asyncio.sleep(0.5)
    rr = await wiki.update_block(obj_token, file_block_id, {"replace_file": {"token": token}})
    return view_block_id or "", file_block_id, rr.get("code") == 0


# ── Block 写入 ──────────────────────────────────────────────────────

async def write_batch_get_ids(
    wiki: WikiService, obj_token: str, parent_block_id: str,
    batch: list[dict], id_map: dict[str, str], old_ids: list[str],
) -> list[str]:
    r = await retry(
        lambda b=batch: wiki.create_doc_block(obj_token, parent_block_id, b),
        label=f"batch@{parent_block_id[:8]}",
    )
    if r.get("code", 0) == 0:
        new_blocks = r.get("data", {}).get("children", [])
        new_ids = [b.get("block_id", "") for b in new_blocks]
        for i, old_id in enumerate(old_ids):
            if i < len(new_ids) and new_ids[i]:
                id_map[old_id] = new_ids[i]
        return new_ids
    else:
        # 降级逐个写入
        new_ids = []
        for i, bl in enumerate(batch):
            r2 = await retry(
                lambda b=bl: wiki.create_doc_block(obj_token, parent_block_id, [b]),
                label=f"single:{BLOCK_TYPE_NAMES.get(bl.get('block_type', 0), '?')}",
            )
            bid = ""
            if r2.get("code", 0) == 0:
                items = r2.get("data", {}).get("children", [])
                if items:
                    bid = items[0].get("block_id", "")
            if bid and i < len(old_ids):
                id_map[old_ids[i]] = bid
            new_ids.append(bid)
            await asyncio.sleep(0.8)
        return new_ids


async def write_table_block(
    wiki: WikiService, obj_token: str, parent_new_id: str,
    source_table: dict, children_map: dict[str, list[dict]],
    id_map: dict[str, str],
) -> int:
    prop = source_table.get("table", {}).get("property")
    if not prop:
        return 0

    create_prop = {
        "row_size": prop.get("row_size", 1),
        "column_size": prop.get("column_size", 1),
    }
    if "column_width" in prop:
        create_prop["column_width"] = prop["column_width"]

    new_table = {"block_type": 31, "table": {"property": create_prop}}
    r = await retry(
        lambda: wiki.create_doc_block(obj_token, parent_new_id, [new_table]),
        label="create_table",
    )
    if r.get("code", 0) != 0:
        return 0

    table_new_id = r["data"]["children"][0].get("block_id", "")
    if not table_new_id:
        return 0
    written = 1

    await asyncio.sleep(2.0)

    new_doc_blocks = await fetch_all_blocks(wiki, obj_token)
    new_cells = [b for b in new_doc_blocks
                 if b.get("parent_id") == table_new_id and b.get("block_type") == 32]

    if not new_cells:
        return written

    source_table_id = source_table.get("block_id", "")
    source_cells = children_map.get(source_table_id, [])

    for ci, source_cell in enumerate(source_cells):
        if ci >= len(new_cells):
            break
        new_cell_id = new_cells[ci]["block_id"]

        default_texts = [b for b in new_doc_blocks if b.get("parent_id") == new_cell_id]
        source_cell_id = source_cell.get("block_id", "")
        source_cell_children = children_map.get(source_cell_id, [])

        if not source_cell_children:
            continue

        for si, src_child in enumerate(source_cell_children):
            if si < len(default_texts):
                dt_block = default_texts[si]
                src_cleaned = clean_block_for_create(src_child)
                update_key = None
                for k in ("text", "heading1", "heading2", "heading3",
                          "heading4", "heading5", "heading6", "bullet",
                          "ordered", "code", "quote", "todo", "callout"):
                    if k in src_cleaned:
                        update_key = k
                        break
                if update_key:
                    update_body = {"update_text_elements": {
                        "elements": src_cleaned[update_key].get("elements", []),
                    }}
                    await retry(
                        lambda bid=dt_block["block_id"], ub=update_body:
                            wiki.update_block(obj_token, bid, ub),
                        label=f"update_cell_{ci}_{si}",
                    )
                written += 1
            else:
                src_cleaned = clean_block_for_create(src_child)
                cr = await retry(
                    lambda b=[src_cleaned]: wiki.create_doc_block(obj_token, new_cell_id, b),
                    label=f"create_cell_{ci}_{si}",
                )
                if cr.get("code", 0) == 0:
                    written += 1
                await asyncio.sleep(0.3)

        for di in range(len(source_cell_children), len(default_texts)):
            dt = default_texts[di]
            await retry(
                lambda bid=dt["block_id"]: wiki.delete_block(obj_token, bid),
                label=f"del_extra_{ci}_{di}",
            )
            await asyncio.sleep(0.2)

        await asyncio.sleep(0.3)

    source_bid = source_table.get("block_id", "")
    if source_bid:
        id_map[source_bid] = table_new_id

    return written


async def write_block_tree(
    wiki: WikiService, client: FeishuClient,
    obj_token: str, parent_new_id: str,
    top_blocks: list[dict], children_map: dict[str, list[dict]],
    id_map: dict[str, str],
    resources: dict[str, dict] | None = None,
    migration_report: list[dict] | None = None,
) -> int:
    resources = resources or {}
    migration_report = migration_report if migration_report is not None else []
    written = 0
    batch: list[dict] = []
    batch_old_ids: list[str] = []

    async def _recurse(parent_id: str, old_children: list[dict]) -> int:
        return await write_block_tree(
            wiki, client, obj_token, parent_id,
            old_children, children_map, id_map,
            resources, migration_report,
        )

    async def _flush_batch():
        nonlocal batch, batch_old_ids, written
        if not batch:
            return
        await write_batch_get_ids(
            wiki, obj_token, parent_new_id, batch, id_map, batch_old_ids,
        )
        written += len(batch)
        for old_id in batch_old_ids:
            new_id = id_map.get(old_id, "")
            if new_id:
                ch = children_map.get(old_id, [])
                if ch:
                    written += await _recurse(new_id, ch)
        batch = []
        batch_old_ids = []
        await asyncio.sleep(DELAY_BATCH)

    for block in top_blocks:
        bid = block.get("block_id", "")
        bt = block.get("block_type")

        if bt == 32:
            continue

        if bt == 31:
            await _flush_batch()
            written += await write_table_block(
                wiki, obj_token, parent_new_id, block, children_map, id_map,
            )
            await asyncio.sleep(DELAY_BATCH)
            continue

        if bt == 27:
            await _flush_batch()
            res = resources.get(bid)
            if res and os.path.exists(res["local_path"]):
                with open(res["local_path"], "rb") as f:
                    file_data = f.read()
                file_name = res.get("original_name", res.get("file_name", "image.png"))
                new_bid, ok = await create_and_bind_image(
                    wiki, client, obj_token, parent_new_id,
                    file_name, file_data,
                )
                if new_bid:
                    id_map[bid] = new_bid
                written += 1
                migration_report.append({
                    "block_type": "image", "source_block_id": bid,
                    "target_block_id": new_bid, "success": ok,
                    "file_name": file_name,
                })
            else:
                placeholder = {"block_type": 2, "text": {"elements": [
                    {"text_run": {"content": "[图片缺失]"}}
                ]}}
                r = await retry(
                    lambda b=[placeholder]: wiki.create_doc_block(obj_token, parent_new_id, b),
                    label="image_placeholder",
                )
                if r.get("code", 0) == 0:
                    written += 1
                migration_report.append({
                    "block_type": "image", "source_block_id": bid,
                    "target_block_id": "", "success": False, "error": "资源未下载",
                })
            await asyncio.sleep(DELAY_BATCH)
            continue

        if bt == 23:
            await _flush_batch()
            file_info = block.get("file", {})
            file_name = file_info.get("name", "文件")
            res = resources.get(bid)

            if res and os.path.exists(res["local_path"]):
                with open(res["local_path"], "rb") as f:
                    file_data = f.read()
                view_bid, file_bid, ok = await create_and_bind_file(
                    wiki, client, obj_token, parent_new_id,
                    file_name, file_data,
                )
                id_map[bid] = view_bid or file_bid
                written += 1
                migration_report.append({
                    "block_type": "file", "source_block_id": bid,
                    "target_block_id": view_bid or file_bid,
                    "file_block_id": file_bid,
                    "success": ok, "file_name": file_name,
                    "size": res.get("size", 0),
                })
            else:
                r = await retry(
                    lambda: wiki.create_doc_block(obj_token, parent_new_id, [
                        {"block_type": 23, "file": {}}
                    ]),
                    label=f"file_empty:{file_name[:20]}",
                )
                if r.get("code", 0) == 0:
                    items = r.get("data", {}).get("children", [])
                    if items:
                        id_map[bid] = items[0].get("block_id", "")
                    written += 1
                migration_report.append({
                    "block_type": "file", "source_block_id": bid,
                    "target_block_id": "", "success": False,
                    "error": "资源未下载", "file_name": file_name,
                })
            await asyncio.sleep(DELAY_BATCH)
            continue

        if bt == 33:
            old_children = children_map.get(bid, [])
            if old_children:
                written += await _recurse(parent_new_id, old_children)
            continue

        if bt in UNSUPPORTED_CONTAINER_TYPES:
            old_children = children_map.get(bid, [])
            if old_children:
                type_name = BLOCK_TYPE_NAMES.get(bt, f"type_{bt}")
                placeholder = {"block_type": 2, "text": {"elements": [
                    {"text_run": {"content": f"[{type_name}]"}}
                ]}}
                r = await retry(
                    lambda b=[placeholder]: wiki.create_doc_block(obj_token, parent_new_id, b),
                    label=f"placeholder:{type_name}",
                )
                if r.get("code", 0) == 0:
                    written += 1
                written += await _recurse(parent_new_id, old_children)
            continue

        cleaned = clean_block_for_create(block)
        batch.append(cleaned)
        batch_old_ids.append(bid)

        if len(batch) >= BATCH_SIZE:
            await _flush_batch()

    await _flush_batch()
    return written


# ── 验证 ──────────────────────────────────────────────────────────────

import hashlib


def _extract_text(block: dict) -> str:
    """提取 block 中的纯文本内容（用于 hash 比较）。"""
    # 遍历所有可能的文本字段
    text_fields = (
        "text", "heading1", "heading2", "heading3",
        "heading4", "heading5", "heading6",
        "bullet", "ordered", "code", "quote", "todo", "callout",
    )
    parts = []
    for field in text_fields:
        obj = block.get(field)
        if not obj:
            continue
        elements = obj.get("elements", [])
        for elem in elements:
            tr = elem.get("text_run", {})
            if tr.get("content"):
                parts.append(tr["content"])
    return "".join(parts)


def _block_signature(block: dict) -> str:
    """生成 block 的内容签名：block_type + 文本 hash。"""
    bt = block.get("block_type", 0)
    text = _extract_text(block)
    text_hash = hashlib.md5(text.encode()).hexdigest()[:8] if text else ""

    # 附加资源信息
    extra = ""
    if bt == 27:
        extra = block.get("image", {}).get("token", "")[:12]
    elif bt == 23:
        fi = block.get("file", {})
        extra = fi.get("name", "")[:20]
    elif bt == 31:
        prop = block.get("table", {}).get("property", {})
        extra = f"r{prop.get('row_size', '?')}c{prop.get('column_size', '?')}"

    return f"{bt}:{text_hash}:{extra}"


def _check_resources(blocks: list[dict]) -> dict:
    """检查 image/file block 的资源存在性。"""
    images = [b for b in blocks if b.get("block_type") == 27]
    files = [b for b in blocks if b.get("block_type") == 23]
    tables = [b for b in blocks if b.get("block_type") == 31]

    img_ok = sum(1 for b in images if b.get("image", {}).get("token"))
    file_ok = sum(1 for b in files if b.get("file", {}).get("token"))
    table_ok = len(tables)  # tables always "exist" if block is present

    return {
        "images": {"total": len(images), "with_token": img_ok,
                    "missing_token": len(images) - img_ok},
        "files": {"total": len(files), "with_token": file_ok,
                   "missing_token": len(files) - file_ok},
        "tables": {"total": len(tables)},
    }


async def verify_doc(
    wiki: WikiService, src_obj_token: str, dst_obj_token: str,
) -> dict:
    src_blocks = await fetch_all_blocks(wiki, src_obj_token)
    dst_blocks = await fetch_all_blocks(wiki, dst_obj_token)

    src_content = [b for b in src_blocks if b.get("block_type") != 1]
    dst_content = [b for b in dst_blocks if b.get("block_type") != 1]

    # 1. block 类型序列比较
    src_type_seq = [b.get("block_type", 0) for b in src_content]
    dst_type_seq = [b.get("block_type", 0) for b in dst_content]
    seq_match = src_type_seq == dst_type_seq

    # 2. 按类型统计
    def count_by_type(blocks):
        counts = {}
        for b in blocks:
            name = BLOCK_TYPE_NAMES.get(b.get("block_type", 0), f"type_{b.get('block_type', 0)}")
            counts[name] = counts.get(name, 0) + 1
        return counts

    src_counts = count_by_type(src_content)
    dst_counts = count_by_type(dst_content)

    type_diffs = []
    for t in sorted(set(list(src_counts.keys()) + list(dst_counts.keys()))):
        s, d = src_counts.get(t, 0), dst_counts.get(t, 0)
        if s != d:
            type_diffs.append(f"{t}: source={s} target={d}")

    # 3. 文本内容 hash 比较（仅比较文本类 block）
    src_text_blocks = [b for b in src_content if b.get("block_type") in (2, 3, 4, 5, 6, 7, 8, 12, 13, 14, 15, 17)]
    dst_text_blocks = [b for b in dst_content if b.get("block_type") in (2, 3, 4, 5, 6, 7, 8, 12, 13, 14, 15, 17)]

    src_hashes = [_block_signature(b) for b in src_text_blocks]
    dst_hashes = [_block_signature(b) for b in dst_text_blocks]
    text_mismatches = []
    for i in range(min(len(src_hashes), len(dst_hashes))):
        if src_hashes[i] != dst_hashes[i]:
            text_mismatches.append({
                "index": i,
                "source": src_hashes[i],
                "target": dst_hashes[i],
            })
    text_match = len(text_mismatches) == 0 and len(src_hashes) == len(dst_hashes)

    # 4. 资源存在性检查
    src_resources = _check_resources(src_content)
    dst_resources = _check_resources(dst_content)

    resource_issues = []
    if dst_resources["images"]["missing_token"] > 0:
        resource_issues.append(f"{dst_resources['images']['missing_token']} images missing token")
    if dst_resources["files"]["missing_token"] > 0:
        resource_issues.append(f"{dst_resources['files']['missing_token']} files missing token")

    # 5. 综合判定
    match = (
        seq_match
        and text_match
        and len(type_diffs) == 0
        and len(resource_issues) == 0
    )

    return {
        "match": match,
        "block_counts": {
            "source": len(src_content),
            "target": len(dst_content),
        },
        "type_sequence_match": seq_match,
        "type_diffs": type_diffs,
        "text_hash": {
            "text_blocks_compared": min(len(src_hashes), len(dst_hashes)),
            "source_text_blocks": len(src_hashes),
            "target_text_blocks": len(dst_hashes),
            "text_match": text_match,
            "mismatches": text_mismatches[:10],  # 最多报告前 10 个
        },
        "resources": {
            "source": src_resources,
            "target": dst_resources,
            "issues": resource_issues,
        },
    }


# ── Handler 类 ───────────────────────────────────────────────────────

class DocxHandler(BaseHandler):
    """docx 文档迁移：blocks 递归复制 + image/file 上传绑定。"""

    def can_handle(self, obj_type: str) -> bool:
        return obj_type == "docx"

    async def copy(
        self,
        src_node: dict,
        target_space_id: str,
        target_parent_token: str,
    ) -> dict:
        obj_token = src_node["obj_token"]
        title = src_node.get("title", "未命名文档")

        # 1. 下载所有 blocks
        all_blocks = await fetch_all_blocks(self._wiki, obj_token)
        page_block = next((b for b in all_blocks if b.get("block_type") == 1), None)
        page_id = page_block.get("block_id", obj_token) if page_block else obj_token

        _, children_map = build_block_tree(all_blocks)
        top_blocks = children_map.get(page_id, [])

        # 2. 下载资源
        report_items: list[dict] = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            resources = await download_resources(self._wiki, all_blocks, tmp_dir)

            # 3. 创建目标文档
            doc_title = f"{title}（副本）"
            create_resp = await retry(
                lambda: self._wiki.create_node(
                    space_id=target_space_id, obj_type="docx",
                    title=doc_title, parent_node_token=target_parent_token,
                    node_type="origin",
                ),
                label="create_doc",
            )
            new_node = create_resp.get("data", {}).get("node", {})
            new_obj_token = new_node.get("obj_token", "")
            new_node_token = new_node.get("node_token", "")

            if not new_obj_token:
                return {"success": False, "error": f"创建文档失败: {create_resp.get('msg', '')}",
                        "report": {}, "target_node_token": "", "target_obj_token": ""}

            await asyncio.sleep(DELAY_CREATE)

            new_page_resp = await self._wiki.get_doc_blocks(new_obj_token, page_size=1)
            new_page_items = new_page_resp.get("data", {}).get("items", [])
            new_page_id = new_page_items[0].get("block_id", new_obj_token) if new_page_items else new_obj_token
            await asyncio.sleep(0.5)

            # 4. 写入 block 树
            id_map: dict[str, str] = {}
            written = await write_block_tree(
                self._wiki, self._client, new_obj_token, new_page_id,
                top_blocks, children_map, id_map,
                resources, report_items,
            )

        # 5. 验证
        verify_result = await verify_doc(self._wiki, obj_token, new_obj_token)

        img_ok = sum(1 for r in report_items if r.get("block_type") == "image" and r.get("success"))
        file_ok = sum(1 for r in report_items if r.get("block_type") == "file" and r.get("success"))

        return {
            "success": True,
            "target_node_token": new_node_token,
            "target_obj_token": new_obj_token,
            "report": {
                "source_blocks": len(all_blocks) - 1,
                "written_blocks": written,
                "images_ok": img_ok,
                "files_ok": file_ok,
                "verify": verify_result,
                "block_details": report_items,
            },
            "error": None,
        }
