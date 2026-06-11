"""迁移服务 — 节点复制、子树递归、任务管理"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any

from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.migrate.handlers import BaseHandler
from feishu_kit.modules.migrate.handlers.docx_handler import DocxHandler
from feishu_kit.modules.migrate.handlers.file_handler import FileHandler
from feishu_kit.modules.migrate.handlers.sheet_handler import SheetHandler
from feishu_kit.modules.migrate.handlers.bitable_handler import BitableHandler
from feishu_kit.modules.wiki.service import WikiService

logger = logging.getLogger(__name__)

# 不支持内容 API 的类型
UNSUPPORTED_TYPES = {"mindnote": "只能创建空节点，无公开内容 API", "doc": "已废弃，请使用 docx"}


class MigrateService:
    def __init__(self, wiki: WikiService, client: FeishuClient):
        self._wiki = wiki
        self._client = client
        self._handlers: list[BaseHandler] = [
            DocxHandler(wiki, client),
            FileHandler(wiki, client),
            SheetHandler(wiki, client),
            BitableHandler(wiki, client),
        ]
        # 异步任务存储
        self._tasks: dict[str, dict] = {}

    def _get_handler(self, obj_type: str) -> BaseHandler | None:
        for h in self._handlers:
            if h.can_handle(obj_type):
                return h
        return None

    async def get_capabilities(self) -> dict:
        """返回当前支持的迁移能力矩阵。"""
        capabilities = []
        for obj_type in ["docx", "file", "sheet", "bitable", "mindnote", "doc"]:
            handler = self._get_handler(obj_type)
            if handler:
                capabilities.append({
                    "obj_type": obj_type,
                    "supported": True,
                    "handler": type(handler).__name__,
                })
            elif obj_type in UNSUPPORTED_TYPES:
                capabilities.append({
                    "obj_type": obj_type,
                    "supported": False,
                    "reason": UNSUPPORTED_TYPES[obj_type],
                })
            else:
                capabilities.append({
                    "obj_type": obj_type,
                    "supported": False,
                    "reason": "无对应处理器",
                })
        return {"capabilities": capabilities}

    async def _list_all_children(self, space_id: str, parent_node_token: str) -> list[dict]:
        """分页获取父节点下的全部子节点。"""
        all_children: list[dict] = []
        page_token: str | None = None
        while True:
            params: dict = {"parent_node_token": parent_node_token, "page_size": "50"}
            if page_token:
                params["page_token"] = page_token
            resp = await self._client.request(
                "GET", f"/wiki/v2/spaces/{space_id}/nodes", params=params,
            )
            items = resp.get("data", {}).get("items", [])
            all_children.extend(items)
            has_more = resp.get("data", {}).get("has_more", False)
            page_token = resp.get("data", {}).get("page_token")
            if not has_more or not page_token or not items:
                break
            await asyncio.sleep(0.3)
        return all_children

    def _make_report_entry(
        self,
        node_token: str, title: str, obj_type: str,
        status: str, error: str | None = None,
        target_node_token: str = "", target_obj_token: str = "",
        detail: dict | None = None,
    ) -> dict:
        """生成标准化的迁移报告条目。"""
        entry = {
            "source_node_token": node_token,
            "title": title,
            "obj_type": obj_type,
            "status": status,  # migrated | failed | skipped | unsupported
            "target_node_token": target_node_token,
            "target_obj_token": target_obj_token,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if error:
            entry["error"] = error
        if detail:
            entry["detail"] = detail
        return entry

    async def copy_node(
        self,
        source_node_token: str,
        target_space_id: str,
        target_parent_token: str,
        report: list[dict] | None = None,
    ) -> dict:
        """迁移单个节点，并将结果写入 report。"""
        report = report if report is not None else []

        # 获取源节点信息
        node_resp = await self._wiki.get_node(source_node_token)
        node_data = node_resp.get("data", {}).get("node", {})
        obj_type = node_data.get("obj_type", "")
        title = node_data.get("title", "")

        if not obj_type:
            entry = self._make_report_entry(
                source_node_token, title, obj_type or "unknown",
                "failed", error=f"无法获取节点信息: {node_resp.get('msg', '')}",
            )
            report.append(entry)
            return {"success": False, "error": entry["error"], "report_entry": entry}

        handler = self._get_handler(obj_type)
        if not handler:
            reason = UNSUPPORTED_TYPES.get(obj_type, f"不支持 obj_type={obj_type}")
            entry = self._make_report_entry(
                source_node_token, title, obj_type,
                "unsupported", error=reason,
            )
            report.append(entry)
            return {"success": False, "error": reason, "report_entry": entry}

        try:
            result = await handler.copy(node_data, target_space_id, target_parent_token)
        except Exception as e:
            entry = self._make_report_entry(
                source_node_token, title, obj_type,
                "failed", error=f"handler 异常: {e}",
            )
            report.append(entry)
            return {"success": False, "error": str(e), "report_entry": entry}

        status = "migrated" if result.get("success") else "failed"
        entry = self._make_report_entry(
            source_node_token, title, obj_type, status,
            error=result.get("error"),
            target_node_token=result.get("target_node_token", ""),
            target_obj_token=result.get("target_obj_token", ""),
            detail=result.get("report"),
        )
        report.append(entry)

        result["source_node_token"] = source_node_token
        result["source_title"] = title
        result["source_obj_type"] = obj_type
        result["report_entry"] = entry
        return result

    async def copy_tree(
        self,
        source_node_token: str,
        target_space_id: str,
        target_parent_token: str,
    ) -> dict:
        """递归迁移节点及其所有子节点，生成完整报告。"""
        report: list[dict] = []

        # 获取源节点信息
        node_resp = await self._wiki.get_node(source_node_token)
        node_data = node_resp.get("data", {}).get("node", {})
        space_id = node_data.get("space_id", target_space_id)

        # 分页获取全部子节点
        children = await self._list_all_children(space_id, source_node_token)

        # 先迁移根节点
        root_result = await self.copy_node(
            source_node_token, target_space_id, target_parent_token,
            report=report,
        )

        if not root_result.get("success"):
            return {
                "success": False,
                "error": f"根节点迁移失败: {root_result.get('error', '')}",
                "root": root_result,
                "children_results": [],
                "report": report,
            }

        # 递归迁移子节点
        children_results = []
        for child in children:
            child_token = child.get("node_token", "")
            if not child_token:
                continue

            child_result = await self.copy_tree(
                child_token, target_space_id,
                root_result["target_node_token"],
            )
            children_results.append({
                "title": child.get("title", ""),
                "obj_type": child.get("obj_type", ""),
                **child_result,
            })
            # 合并子树报告
            report.extend(child_result.get("report", []))
            await asyncio.sleep(1.0)

        return {
            "success": True,
            "root": root_result,
            "children_count": len(children),
            "children_results": children_results,
            "report": report,
        }

    # ── 异步任务管理 ──────────────────────────────────────────────────

    def _save_report(self, task_id: str, report: list[dict]) -> str:
        """将迁移报告保存为 JSON 文件。"""
        os.makedirs("migration_reports", exist_ok=True)
        path = f"migration_reports/{task_id}_{time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        return path

    async def start_copy_task(
        self,
        source_node_token: str,
        target_space_id: str,
        target_parent_token: str,
        recursive: bool = False,
    ) -> str:
        """启动异步迁移任务，返回 task_id。"""
        task_id = str(uuid.uuid4())[:8]
        self._tasks[task_id] = {
            "status": "running",
            "source_node_token": source_node_token,
            "target_space_id": target_space_id,
            "target_parent_token": target_parent_token,
            "recursive": recursive,
            "result": None,
            "error": None,
            "report_file": None,
        }

        async def _run():
            try:
                if recursive:
                    result = await self.copy_tree(
                        source_node_token, target_space_id, target_parent_token,
                    )
                else:
                    report: list[dict] = []
                    node_result = await self.copy_node(
                        source_node_token, target_space_id, target_parent_token,
                        report=report,
                    )
                    result = {**node_result, "report": report}

                self._tasks[task_id]["status"] = "completed"
                self._tasks[task_id]["result"] = result

                # 保存报告
                report_data = result.get("report", [])
                if report_data:
                    path = self._save_report(task_id, report_data)
                    self._tasks[task_id]["report_file"] = path

            except Exception as e:
                logger.exception("Migration task %s failed", task_id)
                self._tasks[task_id]["status"] = "failed"
                self._tasks[task_id]["error"] = str(e)

        asyncio.create_task(_run())
        return task_id

    def get_task(self, task_id: str) -> dict | None:
        return self._tasks.get(task_id)

    def list_tasks(self) -> list[dict]:
        return [
            {"task_id": tid, **task}
            for tid, task in self._tasks.items()
        ]
