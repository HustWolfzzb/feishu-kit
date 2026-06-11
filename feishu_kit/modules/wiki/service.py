"""Wiki service -- wraps all Feishu Wiki (知识库) API endpoints.

Provides methods for managing knowledge spaces, nodes, document content,
members, and RAG-oriented retrieval.
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from feishu_kit.core.client import FeishuClient

logger = logging.getLogger(__name__)


class WikiService:
    """Service class for Feishu Wiki operations.

    Args:
        client: A ``FeishuClient`` instance used to make API requests.
    """

    def __init__(self, client: FeishuClient) -> None:
        self._client = client

    # -- Knowledge Spaces -----------------------------------------------

    async def list_spaces(
        self,
        page_size: int = 20,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List knowledge spaces.

        Args:
            page_size: Number of spaces per page.
            page_token: Pagination token from a previous response.

        Returns:
            Raw API response dict.
        """
        params: dict[str, str] = {"page_size": str(page_size)}
        if page_token:
            params["page_token"] = page_token
        return await self._client.request("GET", "/wiki/v2/spaces", params=params)

    async def get_space(self, space_id: str) -> dict[str, Any]:
        """Get details of a knowledge space.

        Args:
            space_id: The space identifier.

        Returns:
            Raw API response dict.
        """
        return await self._client.request("GET", f"/wiki/v2/spaces/{space_id}")

    # -- Nodes -----------------------------------------------------------

    async def list_nodes(
        self,
        space_id: str,
        page_size: int = 50,
        page_token: str | None = None,
        parent_node_token: str | None = None,
    ) -> dict[str, Any]:
        """List nodes in a knowledge space.

        Args:
            space_id: The space identifier.
            page_size: Number of nodes per page.
            page_token: Pagination token.
            parent_node_token: Filter by parent node.

        Returns:
            Raw API response dict.
        """
        params: dict[str, str] = {"page_size": str(page_size)}
        if page_token:
            params["page_token"] = page_token
        if parent_node_token:
            params["parent_node_token"] = parent_node_token
        return await self._client.request("GET", f"/wiki/v2/spaces/{space_id}/nodes", params=params)

    async def get_node(self, token: str) -> dict[str, Any]:
        """Get node information by token.

        Args:
            token: The node token.

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "GET", "/wiki/v2/spaces/get_node", params={"token": token}
        )

    async def list_all_nodes(self, space_id: str) -> list[dict[str, Any]]:
        """Recursively fetch all nodes in a space.

        Args:
            space_id: The space identifier.

        Returns:
            A flat list of node dicts.
        """
        all_nodes: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            result = await self.list_nodes(space_id, page_size=50, page_token=page_token)
            all_nodes.extend(result.get("data", {}).get("items", []))
            if not result.get("data", {}).get("has_more"):
                break
            page_token = result.get("data", {}).get("page_token")
        return all_nodes

    async def get_node_tree(
        self,
        space_id: str,
        max_depth: int = 2,
    ) -> list[dict[str, Any]]:
        """Get a hierarchical node tree for a space.

        Args:
            space_id: The space identifier.
            max_depth: Maximum tree depth to build.

        Returns:
            A nested list of node dicts with ``children`` keys.
        """
        all_nodes = await self.list_all_nodes(space_id)

        by_parent: dict[str, list[dict[str, Any]]] = {}
        roots: list[dict[str, Any]] = []
        for n in all_nodes:
            parent = n.get("parent_node_token", "")
            if not parent:
                roots.append(n)
            else:
                by_parent.setdefault(parent, []).append(n)

        def _build(nodes: list[dict[str, Any]], depth: int) -> list[dict[str, Any]]:
            if depth >= max_depth:
                return nodes
            result: list[dict[str, Any]] = []
            for node in nodes:
                item = dict(node)
                children = by_parent.get(node["node_token"], [])
                if children:
                    item["children"] = _build(children, depth + 1)
                result.append(item)
            return result

        return _build(roots, 0)

    # -- Members ---------------------------------------------------------

    async def list_members(
        self,
        space_id: str,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List members of a knowledge space.

        Args:
            space_id: The space identifier.
            page_size: Number of members per page.

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "GET",
            f"/wiki/v2/spaces/{space_id}/members",
            params={"page_size": str(page_size)},
        )

    # -- Document Content ------------------------------------------------

    async def get_doc_raw_content(self, obj_token: str) -> dict[str, Any]:
        """Get the raw text content of a document.

        Args:
            obj_token: The document object token.

        Returns:
            Raw API response dict.
        """
        return await self._client.request("GET", f"/docx/v1/documents/{obj_token}/raw_content")

    async def get_doc_blocks(
        self,
        obj_token: str,
        page_size: int = 50,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List blocks in a document.

        Args:
            obj_token: The document object token.
            page_size: Number of blocks per page.
            page_token: Pagination token.

        Returns:
            Raw API response dict.
        """
        params: dict[str, str] = {"page_size": str(page_size)}
        if page_token:
            params["page_token"] = page_token
        return await self._client.request(
            "GET", f"/docx/v1/documents/{obj_token}/blocks", params=params
        )

    async def get_block(
        self,
        obj_token: str,
        block_id: str,
    ) -> dict[str, Any]:
        """Get a single block in a document.

        Args:
            obj_token: The document object token.
            block_id: The block identifier.

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "GET", f"/docx/v1/documents/{obj_token}/blocks/{block_id}"
        )

    # -- Document Permissions --------------------------------------------

    async def get_doc_members(
        self,
        obj_token: str,
        obj_type: str = "docx",
    ) -> dict[str, Any]:
        """Get document collaborators.

        Args:
            obj_token: The document object token.
            obj_type: The object type (e.g. ``"docx"``).

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "POST",
            "/drive/permission/member/list",
            json={"token": obj_token, "type": obj_type},
        )

    async def add_doc_member(
        self,
        obj_token: str,
        member_type: str,
        member_id: str,
        perm: str,
        obj_type: str = "docx",
    ) -> dict[str, Any]:
        """Add a collaborator to a document.

        Args:
            obj_token: The document object token.
            member_type: The member type (e.g. ``"openid"``).
            member_id: The member identifier.
            perm: Permission string (e.g. ``"full_access"``).
            obj_type: The object type.

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "POST",
            f"/drive/v1/permissions/{obj_token}/members",
            json={
                "member_type": member_type,
                "member_id": member_id,
                "perm": perm,
            },
            params={
                "type": obj_type,
                "need_notification": "false",
                "user_id_type": "open_id",
            },
        )

    # -- Node Write Operations -------------------------------------------

    async def create_node(
        self,
        space_id: str,
        obj_type: str = "docx",
        title: str = "未命名文档",
        parent_node_token: str | None = None,
        node_type: str = "origin",
    ) -> dict[str, Any]:
        """Create a node (document) in a knowledge space.

        Args:
            space_id: The space identifier.
            obj_type: Object type (default ``"docx"``).
            title: Document title.
            parent_node_token: Parent node token (for nested documents).
            node_type: Node type (default ``"origin"``).

        Returns:
            Raw API response dict.
        """
        body: dict[str, Any] = {
            "obj_type": obj_type,
            "title": title,
            "node_type": node_type,
        }
        if parent_node_token:
            body["parent_node_token"] = parent_node_token
        return await self._client.request("POST", f"/wiki/v2/spaces/{space_id}/nodes", json=body)

    async def move_node(
        self,
        space_id: str,
        node_token: str,
        target_parent_token: str,
    ) -> dict[str, Any]:
        """Move a node to a new parent.

        Args:
            space_id: The space identifier.
            node_token: The node to move.
            target_parent_token: The new parent node token.

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "POST",
            f"/wiki/v2/spaces/{space_id}/nodes/{node_token}/move",
            json={"target_parent_token": target_parent_token},
        )

    async def rename_node(
        self,
        space_id: str,
        node_token: str,
        title: str,
    ) -> dict[str, Any]:
        """Rename a node.

        Args:
            space_id: The space identifier.
            node_token: The node token.
            title: The new title.

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "POST",
            f"/wiki/v2/spaces/{space_id}/nodes/{node_token}/update_title",
            json={"title": title},
        )

    async def move_docs_to_wiki(
        self,
        space_id: str,
        parent_wiki_token: str,
        obj_token: str,
        obj_type: str = "doc",
    ) -> dict[str, Any]:
        """Move a cloud document into a knowledge space.

        Args:
            space_id: Target space identifier.
            parent_wiki_token: Parent wiki node token.
            obj_token: The cloud document object token.
            obj_type: The object type (default ``"doc"``).

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "POST",
            f"/wiki/v2/spaces/{space_id}/nodes/move_docs_to_wiki",
            json={
                "parent_wiki_token": parent_wiki_token,
                "obj_type": obj_type,
                "obj_token": obj_token,
            },
        )

    async def delete_node(
        self,
        space_id: str,
        node_token: str,
    ) -> dict[str, Any]:
        """Delete a node by looking up its underlying document and deleting that.

        Args:
            space_id: The space identifier.
            node_token: The node token to delete.

        Returns:
            Raw API response dict, or an error dict if ``obj_token`` cannot be resolved.
        """
        node_info = await self.get_node(node_token)
        obj_token = node_info.get("data", {}).get("node", {}).get("obj_token", "")
        obj_type = node_info.get("data", {}).get("node", {}).get("obj_type", "docx")
        if not obj_token:
            return {"code": -1, "msg": f"无法获取节点 {node_token} 的 obj_token"}
        return await self._client.request(
            "DELETE",
            f"/drive/v1/files/{obj_token}",
            params={"type": obj_type},
        )

    # -- Document Content Write Operations --------------------------------

    async def create_doc(
        self,
        title: str = "未命名文档",
        folder_token: str = "",
    ) -> dict[str, Any]:
        """Create a new cloud document.

        Args:
            title: Document title.
            folder_token: Target folder token (empty for root).

        Returns:
            Raw API response dict.
        """
        body: dict[str, Any] = {"title": title}
        if folder_token:
            body["folder_token"] = folder_token
        return await self._client.request("POST", "/docx/v1/documents", json=body)

    async def update_doc_content(
        self,
        obj_token: str,
        operations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Batch-update document content blocks.

        Args:
            obj_token: The document object token.
            operations: List of update operation dicts.

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "POST",
            f"/docx/v1/documents/{obj_token}/blocks/batch_update",
            json={"requests": operations},
        )

    async def create_doc_block(
        self,
        obj_token: str,
        block_id: str,
        children: list[dict[str, Any]],
        index: int = -1,
    ) -> dict[str, Any]:
        """Create child blocks under a parent block.

        Args:
            obj_token: The document object token.
            block_id: The parent block identifier.
            children: List of child block dicts to create.
            index: Insertion index (``-1`` means append).

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "POST",
            f"/docx/v1/documents/{obj_token}/blocks/{block_id}/children",
            json={"children": children, "index": index},
        )

    # -- Space Member Write Operations ------------------------------------

    async def add_space_member(
        self,
        space_id: str,
        member_type: str,
        member_id: str,
        member_role: str = "member",
    ) -> dict[str, Any]:
        """Add a member to a knowledge space.

        Args:
            space_id: The space identifier.
            member_type: The member type.
            member_id: The member identifier.
            member_role: The role to assign (default ``"member"``).

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "POST",
            f"/wiki/v2/spaces/{space_id}/members",
            json={
                "member_type": member_type,
                "member_id": member_id,
                "member_role": member_role,
            },
        )

    async def update_space_member(
        self,
        space_id: str,
        member_type: str,
        member_id: str,
        member_role: str,
    ) -> dict[str, Any]:
        """Update a space member's role (delete then re-add).

        Args:
            space_id: The space identifier.
            member_type: The member type.
            member_id: The member identifier.
            member_role: The new role.

        Returns:
            Raw API response dict from the add operation.
        """
        with contextlib.suppress(Exception):
            await self.delete_space_member(space_id, member_type, member_id)
        return await self.add_space_member(space_id, member_type, member_id, member_role)

    async def delete_space_member(
        self,
        space_id: str,
        member_type: str,
        member_id: str,
        member_role: str = "member",
    ) -> dict[str, Any]:
        """Remove a member from a knowledge space.

        Args:
            space_id: The space identifier.
            member_type: The member type.
            member_id: The member identifier.
            member_role: The member role.

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "DELETE",
            f"/wiki/v2/spaces/{space_id}/members/{member_id}",
            json={"member_type": member_type, "member_role": member_role},
        )

    # -- RAG Support -----------------------------------------------------

    async def get_space_full_content(
        self,
        space_id: str,
        max_nodes: int = 100,
    ) -> list[dict[str, Any]]:
        """Retrieve full text content for all documents in a space (for RAG indexing).

        Args:
            space_id: The space identifier.
            max_nodes: Maximum number of nodes to process.

        Returns:
            A list of dicts with keys ``node_token``, ``title``, ``obj_token``,
            ``content``, and ``blocks_summary``.
        """
        all_nodes = await self.list_all_nodes(space_id)
        results: list[dict[str, Any]] = []

        for node in all_nodes[:max_nodes]:
            obj_token = node.get("obj_token", "")
            title = node.get("title", "")
            node_token = node.get("node_token", "")

            content = ""
            blocks_count = 0
            if obj_token:
                try:
                    raw = await self.get_doc_raw_content(obj_token)
                    content = raw.get("data", {}).get("content", "")
                    blocks_resp = await self.get_doc_blocks(obj_token, page_size=1)
                    blocks_count = len(blocks_resp.get("data", {}).get("items", []))
                except Exception as e:
                    logger.warning("Failed to get content for %s: %s", obj_token, e)

            results.append(
                {
                    "node_token": node_token,
                    "title": title,
                    "obj_token": obj_token,
                    "content": content,
                    "blocks_summary": blocks_count,
                }
            )

        return results

    async def get_node_with_content(self, node_token: str) -> dict[str, Any]:
        """Get node details together with the full document content.

        Useful for single-document RAG retrieval.

        Args:
            node_token: The node token.

        Returns:
            A dict with keys ``node``, ``obj_token``, ``content``, and ``blocks``.
        """
        node_info = await self.get_node(node_token)
        node = node_info.get("data", {}).get("node", {})
        obj_token = node.get("obj_token", "")

        content = ""
        blocks: list[dict[str, Any]] = []
        if obj_token:
            try:
                raw = await self.get_doc_raw_content(obj_token)
                content = raw.get("data", {}).get("content", "")
            except Exception:
                pass
            try:
                blocks_resp = await self.get_doc_blocks(obj_token, page_size=50)
                blocks = blocks_resp.get("data", {}).get("items", [])
            except Exception:
                pass

        return {
            "node": node,
            "obj_token": obj_token,
            "content": content,
            "blocks": blocks,
        }

    async def search_nodes(
        self,
        space_id: str,
        keyword: str,
        max_depth: int = 3,
    ) -> list[dict[str, Any]]:
        """Search nodes in a space by keyword (case-insensitive title match).

        Args:
            space_id: The space identifier.
            keyword: The search keyword.
            max_depth: Unused; kept for backward compatibility.

        Returns:
            A list of matching node dicts.
        """
        all_nodes = await self.list_all_nodes(space_id)
        keyword_lower = keyword.lower()
        matches = [n for n in all_nodes if keyword_lower in n.get("title", "").lower()]
        return matches

    async def delete_block(
        self,
        obj_token: str,
        block_id: str,
        start_index: int = 0,
        end_index: int = 0,
    ) -> dict[str, Any]:
        """Delete a block from a document.

        Args:
            obj_token: The document object token.
            block_id: The block to delete.
            start_index: Start index for partial deletion.
            end_index: End index for partial deletion.

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "DELETE",
            f"/docx/v1/documents/{obj_token}/blocks/{block_id}",
            json={"start_index": start_index, "end_index": end_index},
        )

    async def update_block(
        self,
        obj_token: str,
        block_id: str,
        update_body: dict[str, Any],
    ) -> dict[str, Any]:
        """Update a document block's content.

        Args:
            obj_token: The document object token.
            block_id: The block identifier.
            update_body: The update payload.

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "PATCH",
            f"/docx/v1/documents/{obj_token}/blocks/{block_id}",
            json=update_body,
        )

    # -- Media operations -----------------------------------------------

    async def download_media(self, file_token: str) -> bytes:
        """Download media/file binary data by file_token."""
        return await self._client.download(
            f"/drive/v1/medias/{file_token}/download"
        )

    async def download_image(self, file_token: str) -> bytes:
        """Download image binary data (backward compat)."""
        return await self.download_media(file_token)

    async def upload_docx_image(
        self, obj_token: str, file_name: str, file_data: bytes
    ) -> str:
        """Upload an image to a Feishu docx document, return file_token."""
        return await self._upload_docx_media(
            obj_token, file_name, file_data, parent_type="docx_image"
        )

    async def upload_docx_file(
        self, obj_token: str, file_name: str, file_data: bytes
    ) -> str:
        """Upload a file (PDF etc.) to a Feishu docx document, return file_token."""
        return await self._upload_docx_media(
            obj_token, file_name, file_data, parent_type="docx_file"
        )

    async def _upload_docx_media(
        self, obj_token: str, file_name: str, file_data: bytes,
        parent_type: str = "docx_image",
    ) -> str:
        """Upload media to a Feishu docx document (internal)."""
        resp = await self._client.upload(
            "/drive/v1/medias/upload_all",
            file_name=file_name,
            file_data=file_data,
            fields={
                "file_name": file_name,
                "parent_type": parent_type,
                "parent_node": obj_token,
                "size": str(len(file_data)),
            },
        )
        return resp["data"]["file_token"]
