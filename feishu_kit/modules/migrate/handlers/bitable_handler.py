"""bitable 多维表格迁移处理器 — 读取 tables/fields/records → 创建副本 → 重建"""

from __future__ import annotations

import asyncio

from feishu_kit.modules.migrate.handlers import BaseHandler
from feishu_kit.modules.migrate.handlers.docx_handler import retry, DELAY_CREATE


class BitableHandler(BaseHandler):
    """bitable 多维表格迁移：读取表结构/字段/记录 → 创建副本 → 重建。"""

    def can_handle(self, obj_type: str) -> bool:
        return obj_type == "bitable"

    async def copy(
        self,
        src_node: dict,
        target_space_id: str,
        target_parent_token: str,
    ) -> dict:
        obj_token = src_node["obj_token"]
        title = src_node.get("title", "未命名多维表格")

        # 1. 读取源 tables
        tables_resp = await self._client.request(
            "GET", f"/bitable/v1/apps/{obj_token}/tables",
            params={"page_size": 100},
        )
        if tables_resp.get("code") != 0:
            return {"success": False, "error": f"读取 tables 失败: {tables_resp.get('msg', '')}",
                    "target_node_token": "", "target_obj_token": "", "report": {}}

        source_tables = tables_resp.get("data", {}).get("items", [])

        # 2. 读取每个 table 的 fields + records
        table_data = []
        for tbl in source_tables:
            table_id = tbl.get("table_id", "")
            table_name = tbl.get("name", "")

            # fields
            fields_resp = await self._client.request(
                "GET", f"/bitable/v1/apps/{obj_token}/tables/{table_id}/fields",
                params={"page_size": 200},
            )
            fields = fields_resp.get("data", {}).get("items", [])

            # records
            records = []
            pt = None
            while True:
                rec_resp = await self._client.request(
                    "GET", f"/bitable/v1/apps/{obj_token}/tables/{table_id}/records",
                    params={"page_size": 500, "page_token": pt},
                )
                items = rec_resp.get("data", {}).get("items", [])
                records.extend(items)
                pt = rec_resp.get("data", {}).get("page_token")
                if not pt or not items:
                    break
                await asyncio.sleep(0.3)

            table_data.append({
                "table_id": table_id,
                "name": table_name,
                "fields": fields,
                "records": records,
            })
            await asyncio.sleep(0.3)

        # 3. 创建目标 bitable
        create_resp = await retry(
            lambda: self._wiki.create_node(
                space_id=target_space_id, obj_type="bitable",
                title=f"{title}（副本）",
                parent_node_token=target_parent_token,
                node_type="origin",
            ),
            label="create_bitable",
        )
        new_node = create_resp.get("data", {}).get("node", {})
        new_obj_token = new_node.get("obj_token", "")
        new_node_token = new_node.get("node_token", "")

        if not new_obj_token:
            return {"success": False, "error": f"创建多维表格失败: {create_resp.get('msg', '')}",
                    "target_node_token": "", "target_obj_token": "", "report": {}}

        await asyncio.sleep(DELAY_CREATE)

        # 4. 获取默认 table（bitable 创建时自动带一个默认表）
        target_tables_resp = await self._client.request(
            "GET", f"/bitable/v1/apps/{new_obj_token}/tables",
            params={"page_size": 100},
        )
        target_tables = target_tables_resp.get("data", {}).get("items", [])
        default_table_id = target_tables[0].get("table_id", "") if target_tables else ""

        # 5. 重建表结构和数据
        tables_migrated = 0
        for i, td in enumerate(table_data):
            if i == 0 and default_table_id:
                target_table_id = default_table_id
            else:
                # 创建新表
                ct_resp = await self._client.request(
                    "POST", f"/bitable/v1/apps/{new_obj_token}/tables",
                    json={"table": {"name": td["name"]}},
                )
                if ct_resp.get("code") != 0:
                    continue
                target_table_id = ct_resp.get("data", {}).get("table_id", "")

            # 创建 fields
            field_id_map = {}
            for field in td["fields"]:
                cf_resp = await self._client.request(
                    "POST",
                    f"/bitable/v1/apps/{new_obj_token}/tables/{target_table_id}/fields",
                    json={"field": {
                        "field_name": field.get("field_name", ""),
                        "type": field.get("type", 1),
                    }},
                )
                if cf_resp.get("code") == 0:
                    old_fid = field.get("field_id", "")
                    new_fid = cf_resp.get("data", {}).get("field", {}).get("field_id", "")
                    field_id_map[old_fid] = new_fid
                await asyncio.sleep(0.2)

            # 创建 records（批量）
            if td["records"]:
                # 映射字段 ID
                mapped_records = []
                for rec in td["records"]:
                    old_fields = rec.get("fields", {})
                    new_fields = {}
                    for old_fid, val in old_fields.items():
                        new_fid = field_id_map.get(old_fid, old_fid)
                        new_fields[new_fid] = val
                    mapped_records.append({"fields": new_fields})

                # 分批写入
                batch_size = 500
                for batch_start in range(0, len(mapped_records), batch_size):
                    batch = mapped_records[batch_start:batch_start + batch_size]
                    await self._client.request(
                        "POST",
                        f"/bitable/v1/apps/{new_obj_token}/tables/{target_table_id}/records/batch_create",
                        json={"records": batch},
                    )
                    await asyncio.sleep(0.3)

            tables_migrated += 1

        return {
            "success": True,
            "target_node_token": new_node_token,
            "target_obj_token": new_obj_token,
            "report": {
                "source_tables": len(source_tables),
                "tables_migrated": tables_migrated,
                "total_fields": sum(len(td["fields"]) for td in table_data),
                "total_records": sum(len(td["records"]) for td in table_data),
            },
            "error": None,
        }
