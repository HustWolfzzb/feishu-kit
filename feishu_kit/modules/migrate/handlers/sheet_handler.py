"""sheet 电子表格迁移处理器 — 读取所有 sheet 数据 → 创建副本 → 逐 sheet 写入"""

from __future__ import annotations

import asyncio

from feishu_kit.modules.migrate.handlers import BaseHandler
from feishu_kit.modules.migrate.handlers.docx_handler import retry, DELAY_CREATE


class SheetHandler(BaseHandler):
    """sheet 电子表格迁移：读取 sheet 列表 → 逐 sheet 读取数据 → 创建副本 → 写入。"""

    def can_handle(self, obj_type: str) -> bool:
        return obj_type == "sheet"

    async def copy(
        self,
        src_node: dict,
        target_space_id: str,
        target_parent_token: str,
    ) -> dict:
        obj_token = src_node["obj_token"]
        title = src_node.get("title", "未命名表格")

        # 1. 读取源表格的 sheet 列表
        sheets_resp = await self._client.request(
            "GET",
            f"/sheets/v3/spreadsheets/{obj_token}/sheets/query",
            params={"spreadsheet_token": obj_token},
        )
        if sheets_resp.get("code") != 0:
            return {"success": False, "error": f"读取 sheet 列表失败: {sheets_resp.get('msg', '')}",
                    "target_node_token": "", "target_obj_token": "", "report": {}}

        source_sheets = sheets_resp.get("data", {}).get("sheets", [])
        if not source_sheets:
            return {"success": False, "error": "源表格无 sheet",
                    "target_node_token": "", "target_obj_token": "", "report": {}}

        # 2. 读取每个源 sheet 的数据，建立 source_sheet_id → data 映射
        sheet_data_map: dict[str, list[list]] = {}
        sheet_title_map: dict[str, str] = {}
        for sheet_info in source_sheets:
            sheet_id = sheet_info.get("sheet_id", "")
            sheet_title = sheet_info.get("title", "")
            row_count = sheet_info.get("grid_properties", {}).get("row_count", 0)
            col_count = sheet_info.get("grid_properties", {}).get("column_count", 0)
            if not sheet_id:
                continue

            sheet_title_map[sheet_id] = sheet_title

            if row_count == 0 or col_count == 0:
                sheet_data_map[sheet_id] = []
                continue

            col_letter = _col_to_letter(col_count)
            range_str = f"{sheet_id}!A1:{col_letter}{row_count}"

            values_resp = await self._client.request(
                "GET",
                f"/sheets/v2/spreadsheets/{obj_token}/values/{range_str}",
            )
            if values_resp.get("code") == 0:
                sheet_data_map[sheet_id] = values_resp.get("data", {}).get("valueRange", {}).get("values", [])
            else:
                sheet_data_map[sheet_id] = []
            await asyncio.sleep(0.5)

        # 3. 创建目标表格
        create_resp = await retry(
            lambda: self._wiki.create_node(
                space_id=target_space_id, obj_type="sheet",
                title=f"{title}（副本）",
                parent_node_token=target_parent_token,
                node_type="origin",
            ),
            label="create_sheet",
        )
        new_node = create_resp.get("data", {}).get("node", {})
        new_obj_token = new_node.get("obj_token", "")
        new_node_token = new_node.get("node_token", "")

        if not new_obj_token:
            return {"success": False, "error": f"创建表格失败: {create_resp.get('msg', '')}",
                    "target_node_token": "", "target_obj_token": "", "report": {}}

        await asyncio.sleep(DELAY_CREATE)

        # 4. 获取目标表格的 sheet 列表
        target_sheets_resp = await self._client.request(
            "GET",
            f"/sheets/v3/spreadsheets/{new_obj_token}/sheets/query",
            params={"spreadsheet_token": new_obj_token},
        )
        target_sheets = target_sheets_resp.get("data", {}).get("sheets", [])

        # 5. 建立 source_sheet_id → target_sheet_id 映射
        # 新建的 sheet 默认有一个 sheet，后续通过 API 创建更多
        sheet_mapping: dict[str, str] = {}
        source_sheet_ids = list(sheet_data_map.keys())

        # 第一个源 sheet 映射到目标默认 sheet
        if source_sheet_ids and target_sheets:
            sheet_mapping[source_sheet_ids[0]] = target_sheets[0].get("sheet_id", "")

        # 为剩余的源 sheet 创建目标 sheet
        for src_sid in source_sheet_ids[1:]:
            src_title = sheet_title_map.get(src_sid, "Sheet")
            create_sheet_resp = await self._client.request(
                "POST",
                f"/sheets/v3/spreadsheets/{new_obj_token}/sheets",
                json={"title": src_title},
            )
            if create_sheet_resp.get("code") == 0:
                new_sheet_id = create_sheet_resp.get("data", {}).get("sheet_id", "")
                if new_sheet_id:
                    sheet_mapping[src_sid] = new_sheet_id
            await asyncio.sleep(0.5)

        # 6. 逐 sheet 写入数据（按 source_sheet_id → target_sheet_id 映射）
        written_sheets = 0
        sheet_reports = []
        for src_sid in source_sheet_ids:
            target_sid = sheet_mapping.get(src_sid, "")
            values = sheet_data_map.get(src_sid, [])
            src_title = sheet_title_map.get(src_sid, "")

            if not target_sid:
                sheet_reports.append({
                    "source_sheet_id": src_sid, "source_title": src_title,
                    "status": "skipped", "error": "no target sheet mapping",
                })
                continue

            if not values:
                sheet_reports.append({
                    "source_sheet_id": src_sid, "source_title": src_title,
                    "target_sheet_id": target_sid,
                    "status": "migrated", "rows": 0, "cols": 0,
                })
                written_sheets += 1
                continue

            max_col = max(len(row) for row in values) if values else 1
            col_letter = _col_to_letter(max_col)
            range_str = f"{target_sid}!A1:{col_letter}{len(values)}"

            write_resp = await self._client.request(
                "PUT",
                f"/sheets/v2/spreadsheets/{new_obj_token}/values",
                json={"valueRange": {"range": range_str, "values": values}},
            )
            ok = write_resp.get("code") == 0
            if ok:
                written_sheets += 1

            sheet_reports.append({
                "source_sheet_id": src_sid, "source_title": src_title,
                "target_sheet_id": target_sid,
                "status": "migrated" if ok else "failed",
                "rows": len(values), "cols": max_col,
                "error": write_resp.get("msg", "") if not ok else None,
            })
            await asyncio.sleep(0.5)

        # 7. 重命名第一个目标 sheet 为源第一个 sheet 的标题
        if source_sheet_ids and target_sheets:
            first_title = sheet_title_map.get(source_sheet_ids[0], "")
            first_target_sid = sheet_mapping.get(source_sheet_ids[0], "")
            if first_title and first_target_sid:
                await self._client.request(
                    "PUT",
                    f"/sheets/v3/spreadsheets/{new_obj_token}/sheets/{first_target_sid}",
                    json={"properties": {"title": first_title}},
                )

        return {
            "success": True,
            "target_node_token": new_node_token,
            "target_obj_token": new_obj_token,
            "report": {
                "source_sheets": len(source_sheets),
                "data_sheets": len(sheet_data_map),
                "written_sheets": written_sheets,
                "sheet_mapping": {k: v for k, v in sheet_mapping.items()},
                "sheet_details": sheet_reports,
            },
            "error": None,
        }


def _col_to_letter(col_count: int) -> str:
    """将列数转为 Excel 风格列字母（如 3 → 'C'，28 → 'AB'）。"""
    result = ""
    n = col_count
    while n > 0:
        n -= 1
        result = chr(65 + n % 26) + result
        n //= 26
    return result
