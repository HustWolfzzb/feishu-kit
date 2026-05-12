"""MD-to-Feishu document orchestration service.

Parses Markdown into Feishu blocks, creates a wiki document, writes the
blocks, and optionally attaches the raw Markdown as a child document.
"""

from __future__ import annotations

import logging
from typing import Any

from feishu_kit.modules.md2feishu.parser import parse_md_to_blocks, _text_element, _code_lang
from feishu_kit.modules.wiki.service import WikiService

logger = logging.getLogger(__name__)

BATCH_SIZE = 50


class Md2FeishuService:
    """Orchestrates the conversion of Markdown into a Feishu wiki document.

    Instead of creating its own ``WikiService``, this class receives one
    via the constructor so that callers control the lifecycle and
    configuration of the wiki dependency.

    Args:
        wiki_service: A ``WikiService`` instance used for all wiki API calls.
    """

    def __init__(self, wiki_service: WikiService) -> None:
        self._wiki = wiki_service

    async def preview(self, markdown: str) -> list[dict[str, Any]]:
        """Parse Markdown into Feishu blocks without pushing.

        Args:
            markdown: Raw Markdown text.

        Returns:
            A list of Feishu block dicts (preview only).
        """
        return parse_md_to_blocks(markdown)

    async def push_markdown(
        self,
        markdown: str,
        title: str,
        space_id: str,
        parent_node_token: str | None = None,
    ) -> dict[str, Any]:
        """Full pipeline: parse Markdown, create document, write blocks, attach raw source.

        Args:
            markdown: Raw Markdown text.
            title: Document title.
            space_id: Target knowledge space ID.
            parent_node_token: Optional parent node for nested documents.

        Returns:
            A result dict with keys ``code`` and ``data`` containing
            ``node_token``, ``obj_token``, ``title``, ``blocks_written``,
            ``blocks_total``, ``errors``, ``child_node_token``,
            ``child_obj_token``, and ``url``.
        """
        # 1. Parse MD -> Feishu blocks
        blocks = parse_md_to_blocks(markdown)
        logger.info("Parsed %d blocks from markdown", len(blocks))

        # 2. Create the main document
        node_resp = await self._wiki.create_node(
            space_id=space_id,
            obj_type="docx",
            title=title,
            parent_node_token=parent_node_token,
        )
        if node_resp.get("code", 0) != 0:
            return {"code": -1, "msg": "Failed to create node", "raw": node_resp}

        node_data = node_resp.get("data", {}).get("node", {})
        node_token = node_data.get("node_token", "")
        obj_token = node_data.get("obj_token", "")

        if not obj_token:
            return {"code": -1, "msg": "Failed to create document node", "raw": node_resp}

        # 3. Get the document page block ID
        page_block_id = await self._get_page_block_id(obj_token)

        # 4. Write blocks (with per-block response checking)
        written, errors = await self._write_blocks(obj_token, page_block_id, blocks)
        logger.info(
            "Wrote %d/%d blocks to document %s (%d errors)",
            written, len(blocks), obj_token, errors,
        )

        # 5. Create a child document -- attach raw Markdown source
        child_node_token = ""
        child_obj_token = ""
        try:
            child_resp = await self._wiki.create_node(
                space_id=space_id,
                obj_type="docx",
                title=f"{title} — 原文.md",
                parent_node_token=node_token,
            )
            child_node_data = child_resp.get("data", {}).get("node", {})
            child_node_token = child_node_data.get("node_token", "")
            child_obj_token = child_node_data.get("obj_token", "")

            if child_obj_token:
                child_page_id = await self._get_page_block_id(child_obj_token)
                code_block: dict[str, Any] = {
                    "block_type": 14,
                    "code": {
                        "language": _code_lang("markdown"),
                        "elements": [_text_element(markdown)],
                    },
                }
                await self._wiki.create_doc_block(
                    child_obj_token, child_page_id, [code_block]
                )
                logger.info("Attached raw markdown to child doc %s", child_obj_token)
        except Exception as e:
            logger.warning("Failed to create raw markdown child doc: %s", e)

        return {
            "code": 0,
            "data": {
                "node_token": node_token,
                "obj_token": obj_token,
                "title": title,
                "blocks_written": written,
                "blocks_total": len(blocks),
                "errors": errors,
                "child_node_token": child_node_token,
                "child_obj_token": child_obj_token,
                "url": f"https://bytedance.larkoffice.com/wiki/{node_token}",
            },
        }

    async def _get_page_block_id(self, obj_token: str) -> str:
        """Retrieve the page block ID for a document.

        Args:
            obj_token: The document object token.

        Returns:
            The page block ID, falling back to ``obj_token`` itself.
        """
        resp = await self._wiki.get_doc_blocks(obj_token, page_size=1)
        items = resp.get("data", {}).get("items", [])
        if items:
            return items[0].get("block_id", obj_token)
        return obj_token

    async def _write_blocks(
        self,
        obj_token: str,
        page_block_id: str,
        blocks: list[dict[str, Any]],
    ) -> tuple[int, int]:
        """Write blocks to a document, handling tables specially.

        Normal blocks are written in batches; table blocks require
        separate creation and cell-population steps.

        Args:
            obj_token: The document object token.
            page_block_id: The parent page block ID.
            blocks: List of block dicts to write.

        Returns:
            A ``(written_count, error_count)`` tuple.
        """
        written = 0
        errors = 0

        # Separate table blocks from normal blocks
        normal_blocks: list[dict[str, Any]] = []
        table_blocks: list[dict[str, Any]] = []

        for block in blocks:
            if block.get("block_type") == 31:
                table_blocks.append(block)
            else:
                normal_blocks.append(block)

        # 1. Batch-write normal blocks
        for i in range(0, len(normal_blocks), BATCH_SIZE):
            batch = normal_blocks[i: i + BATCH_SIZE]
            resp = await self._wiki.create_doc_block(
                obj_token, page_block_id, batch
            )
            if resp.get("code", 0) == 0:
                written += len(batch)
            else:
                logger.warning(
                    "Batch write failed (code=%s): %s, retrying one-by-one",
                    resp.get("code"), resp.get("msg"),
                )
                for block in batch:
                    r = await self._wiki.create_doc_block(
                        obj_token, page_block_id, [block]
                    )
                    if r.get("code", 0) == 0:
                        written += 1
                    else:
                        errors += 1
                        logger.error(
                            "Block type=%s failed: %s",
                            block.get("block_type"), r.get("msg"),
                        )

        # 2. Write table blocks (special handling)
        for table_block in table_blocks:
            cell_contents = table_block.pop("children", [])
            # Step 1: create the table block (Feishu auto-creates empty cell blocks)
            resp = await self._wiki.create_doc_block(
                obj_token, page_block_id, [table_block]
            )
            if resp.get("code", 0) != 0:
                errors += 1
                logger.error("Table block failed: %s", resp.get("msg"))
                table_block["children"] = cell_contents
                continue

            written += 1

            # Step 2: get the auto-created cell block IDs
            created = resp.get("data", {}).get("children", [])
            if not created:
                table_block["children"] = cell_contents
                continue

            table_info = created[0]
            cell_ids: list[str] = table_info.get("table", {}).get("cells", [])
            if not cell_ids:
                cell_ids = table_info.get("children", [])

            # Step 3: write content into each cell
            for idx, cell_id in enumerate(cell_ids):
                if idx >= len(cell_contents):
                    break
                cell = cell_contents[idx]
                cell_children = cell.get("children", [])
                if cell_children:
                    cell_resp = await self._wiki.create_doc_block(
                        obj_token, cell_id, cell_children
                    )
                    if cell_resp.get("code", 0) == 0:
                        written += 1
                    else:
                        errors += 1
                        logger.error(
                            "Cell %d write failed: %s", idx, cell_resp.get("msg"),
                        )

            table_block["children"] = cell_contents

        return written, errors
