"""file 文件节点迁移处理器 — 降级为 docx 容器 + embed file block"""

from __future__ import annotations

import asyncio

from feishu_kit.modules.migrate.handlers import BaseHandler
from feishu_kit.modules.migrate.handlers.docx_handler import (
    create_and_bind_file, retry, DELAY_CREATE,
)


class FileHandler(BaseHandler):
    """file 类型节点迁移：下载文件 → 创建 docx 容器 → embed file block。

    飞书 API 不支持直接创建 obj_type=file 的 wiki 节点，
    因此降级为创建 docx 文档并嵌入 file block。
    """

    def can_handle(self, obj_type: str) -> bool:
        return obj_type == "file"

    async def copy(
        self,
        src_node: dict,
        target_space_id: str,
        target_parent_token: str,
    ) -> dict:
        obj_token = src_node["obj_token"]
        title = src_node.get("title", "文件")

        # 1. 下载源文件（file 类型用 /drive/v1/files/ 而非 /medias/）
        file_data = None
        try:
            file_data = await self._client.download(f"/drive/v1/files/{obj_token}/download")
        except Exception:
            try:
                file_data = await self._client.download(f"/drive/v1/medias/{obj_token}/download")
            except Exception as e:
                return {
                    "success": False,
                    "error": f"下载文件失败: {e}",
                    "target_node_token": "",
                    "target_obj_token": "",
                    "report": {},
                }

        if not file_data:
            return {"success": False, "error": "下载文件为空",
                    "target_node_token": "", "target_obj_token": "", "report": {}}

        # 2. 创建 docx 容器
        create_resp = await retry(
            lambda: self._wiki.create_node(
                space_id=target_space_id, obj_type="docx",
                title=title, parent_node_token=target_parent_token,
                node_type="origin",
            ),
            label="create_docx_for_file",
        )
        new_node = create_resp.get("data", {}).get("node", {})
        new_obj_token = new_node.get("obj_token", "")
        new_node_token = new_node.get("node_token", "")

        if not new_obj_token:
            return {"success": False, "error": f"创建文档失败: {create_resp.get('msg', '')}",
                    "target_node_token": "", "target_obj_token": "", "report": {}}

        await asyncio.sleep(DELAY_CREATE)

        # 3. 获取 page block
        page_resp = await self._wiki.get_doc_blocks(new_obj_token, page_size=1)
        page_items = page_resp.get("data", {}).get("items", [])
        page_bid = page_items[0]["block_id"] if page_items else new_obj_token

        # 4. 创建空 file block + 上传 + replace_file
        view_bid, file_bid, ok = await create_and_bind_file(
            self._wiki, self._client, new_obj_token, page_bid,
            title, file_data,
        )

        # 5. 验证
        verified = False
        if ok:
            await asyncio.sleep(1.0)
            try:
                verify_blocks_resp = await self._wiki.get_doc_blocks(new_obj_token, page_size=50)
                blocks = verify_blocks_resp.get("data", {}).get("items", [])
                file_blocks = [b for b in blocks if b.get("block_type") == 23]
                if file_blocks:
                    fi = file_blocks[0].get("file", {})
                    new_tok = fi.get("token", "")
                    if new_tok:
                        dl = await self._wiki.download_media(new_tok)
                        verified = len(dl) == len(file_data)
            except Exception:
                pass

        return {
            "success": ok,
            "target_node_token": new_node_token,
            "target_obj_token": new_obj_token,
            "report": {
                "source_size": len(file_data),
                "verified": verified,
                "view_block_id": view_bid,
                "file_block_id": file_bid,
            },
            "error": None if ok else "file block 绑定失败",
        }
