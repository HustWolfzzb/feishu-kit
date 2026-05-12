"""Drive service -- wraps all Feishu Drive (云盘) API endpoints.

Provides methods for file/folder browsing, permissions, and file upload/download.
"""

from __future__ import annotations

from typing import Any

from feishu_kit.core.client import FeishuClient


class DriveService:
    """Service class for Feishu Drive operations.

    Args:
        client: A ``FeishuClient`` instance used to make API requests.
    """

    def __init__(self, client: FeishuClient) -> None:
        self._client = client

    # -- File / Folder Browsing ------------------------------------------

    async def get_root_folder(self) -> dict[str, Any]:
        """Get the root folder metadata.

        Returns:
            Raw API response dict.
        """
        return await self._client.request("GET", "/drive/explorer/v2/root_folder/meta")

    async def list_files(
        self,
        folder_token: str = "",
        page_size: int = 20,
        order_by: str = "EditedTime",
    ) -> dict[str, Any]:
        """List files in a folder.

        Args:
            folder_token: Folder token (empty for root).
            page_size: Number of files per page.
            order_by: Sort field (default ``"EditedTime"``).

        Returns:
            Raw API response dict.
        """
        params: dict[str, str] = {"page_size": str(page_size), "order_by": order_by}
        if folder_token:
            params["folder_token"] = folder_token
        return await self._client.request("GET", "/drive/v1/files", params=params)

    async def get_file(
        self,
        file_token: str,
        file_type: str = "file",
    ) -> dict[str, Any]:
        """Get file details.

        Args:
            file_token: The file token.
            file_type: The file type (default ``"file"``).

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "GET",
            f"/drive/v1/files/{file_token}",
            params={"type": file_type},
        )

    async def create_folder(
        self,
        folder_token: str,
        name: str,
    ) -> dict[str, Any]:
        """Create a folder.

        Args:
            folder_token: Parent folder token.
            name: New folder name.

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "POST",
            "/drive/v1/files/create_folder",
            json={"folder_token": folder_token, "name": name},
        )

    async def delete_file(
        self,
        file_token: str,
        file_type: str = "file",
    ) -> dict[str, Any]:
        """Delete a file or folder.

        Args:
            file_token: The file token.
            file_type: The file type (default ``"file"``).

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "DELETE",
            f"/drive/v1/files/{file_token}",
            params={"type": file_type},
        )

    # -- File Permissions ------------------------------------------------

    async def list_file_members(
        self,
        token: str,
        obj_type: str = "docx",
    ) -> dict[str, Any]:
        """Get the collaborator list for a file.

        Args:
            token: The file token.
            obj_type: The object type (default ``"docx"``).

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "POST",
            "/drive/permission/member/list",
            json={"token": token, "type": obj_type},
        )

    async def add_file_member(
        self,
        token: str,
        obj_type: str,
        member_type: str,
        member_id: str,
        perm: str,
    ) -> dict[str, Any]:
        """Add a collaborator to a file.

        Args:
            token: The file token.
            obj_type: The object type.
            member_type: The member type.
            member_id: The member identifier.
            perm: Permission to grant.

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "POST",
            "/drive/permission/member/create",
            json={
                "token": token,
                "type": obj_type,
                "members": [{"member_type": member_type, "member_id": member_id}],
                "notify_lark": False,
            },
            params={"perm": perm},
        )

    async def transfer_owner(
        self,
        token: str,
        obj_type: str,
        owner_id: str,
    ) -> dict[str, Any]:
        """Transfer ownership of a file.

        Args:
            token: The file token.
            obj_type: The object type.
            owner_id: The new owner's identifier.

        Returns:
            Raw API response dict.
        """
        return await self._client.request(
            "POST",
            "/drive/permission/member/transfer",
            json={"token": token, "type": obj_type, "owner": owner_id},
        )

    # -- Upload / Download -----------------------------------------------

    async def upload_file(
        self,
        folder_token: str,
        file_name: str,
        file_data: bytes,
    ) -> dict[str, Any]:
        """Upload a local file to Feishu Drive (single-shot, max 20 MB).

        Args:
            folder_token: Target folder token.
            file_name: File name including extension.
            file_data: Raw file bytes.

        Returns:
            Raw API response dict.
        """
        return await self._client.upload(
            "/drive/v1/files/upload_all",
            file_name=file_name,
            file_data=file_data,
            fields={
                "file_name": file_name,
                "parent_type": "explorer",
                "parent_node": folder_token,
                "size": str(len(file_data)),
            },
        )

    async def download(
        self,
        file_token: str,
        file_type: str = "file",
    ) -> dict[str, Any]:
        """Get a file download link.

        Args:
            file_token: The file token.
            file_type: The file type (default ``"file"``).

        Returns:
            Raw API response dict containing the ``download_url``.
        """
        return await self._client.request(
            "GET",
            f"/drive/v1/files/{file_token}",
            params={"type": file_type, "extra": "download_url"},
        )
