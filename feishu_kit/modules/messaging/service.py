"""消息与群聊服务 — 封装飞书 IM 全部 API"""


class MessagingService:
    def __init__(self, client):
        self._client = client

    # ── 消息发送 ────────────────────────────────────────────────────
    async def send_message(
        self,
        receive_id: str,
        msg_type: str,
        content: str,
        receive_id_type: str = "open_id",
    ) -> dict:
        return await self._client.request(
            "POST",
            "/im/v1/messages",
            params={"receive_id_type": receive_id_type},
            json={
                "receive_id": receive_id,
                "msg_type": msg_type,
                "content": content,
            },
        )

    async def reply_message(self, message_id: str, msg_type: str, content: str) -> dict:
        """回复指定消息。"""
        return await self._client.request(
            "POST",
            f"/im/v1/messages/{message_id}/reply",
            json={"msg_type": msg_type, "content": content},
        )

    async def get_message(self, message_id: str) -> dict:
        """获取指定消息详情。"""
        return await self._client.request("GET", f"/im/v1/messages/{message_id}")

    async def delete_message(self, message_id: str) -> dict:
        """撤回消息。"""
        return await self._client.request("DELETE", f"/im/v1/messages/{message_id}")

    async def update_message(self, message_id: str, content: str) -> dict:
        """更新消息内容（仅支持卡片消息）。"""
        return await self._client.request(
            "PATCH",
            f"/im/v1/messages/{message_id}",
            json={"content": content},
        )

    async def list_messages(
        self,
        container_id: str,
        container_id_type: str = "chat",
        page_size: int = 20,
        page_token: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
    ) -> dict:
        """获取会话内消息列表。"""
        params: dict = {
            "container_id_type": container_id_type,
            "container_id": container_id,
            "page_size": str(page_size),
        }
        if page_token:
            params["page_token"] = page_token
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        return await self._client.request("GET", "/im/v1/messages", params=params)

    # ── 消息反应 ────────────────────────────────────────────────────
    async def add_reaction(self, message_id: str, reaction_type: str, emoji: str = "") -> dict:
        """给消息添加表情回应。"""
        body: dict = {"reaction_type": reaction_type}
        if emoji:
            body["emoji"] = emoji
        return await self._client.request(
            "POST",
            f"/im/v1/messages/{message_id}/reactions",
            json=body,
        )

    async def list_reactions(self, message_id: str, page_size: int = 20) -> dict:
        """获取消息回应列表。"""
        return await self._client.request(
            "GET",
            f"/im/v1/messages/{message_id}/reactions",
            params={"page_size": str(page_size)},
        )

    async def delete_reaction(self, message_id: str, reaction_id: str) -> dict:
        """删除消息回应。"""
        return await self._client.request(
            "DELETE",
            f"/im/v1/messages/{message_id}/reactions/{reaction_id}",
        )

    # ── 群聊管理 ────────────────────────────────────────────────────
    async def list_chats(self, page_size: int = 20, page_token: str | None = None) -> dict:
        params: dict = {"page_size": str(page_size)}
        if page_token:
            params["page_token"] = page_token
        return await self._client.request("GET", "/im/v1/chats", params=params)

    async def get_chat_info(self, chat_id: str) -> dict:
        return await self._client.request("GET", f"/im/v1/chats/{chat_id}")

    async def create_chat(
        self,
        name: str = "",
        description: str = "",
        chat_mode: str = "group",
        chat_type: str = "public",
        user_id_list: list[str] | None = None,
        bot_id_list: list[str] | None = None,
    ) -> dict:
        """创建群聊。"""
        body: dict = {
            "chat_mode": chat_mode,
            "chat_type": chat_type,
        }
        if name:
            body["name"] = name
        if description:
            body["description"] = description
        if user_id_list:
            body["user_id_list"] = user_id_list
        if bot_id_list:
            body["bot_id_list"] = bot_id_list
        return await self._client.request("POST", "/im/v1/chats", json=body)

    async def update_chat(
        self,
        chat_id: str,
        *,
        name: str | None = None,
        description: str | None = None,
    ) -> dict:
        """更新群聊信息。"""
        body: dict = {}
        if name is not None:
            body["name"] = name
        if description is not None:
            body["description"] = description
        return await self._client.request(
            "PUT",
            f"/im/v1/chats/{chat_id}",
            json=body,
        )

    async def disband_chat(self, chat_id: str) -> dict:
        """解散群聊。"""
        return await self._client.request("DELETE", f"/im/v1/chats/{chat_id}")

    # ── 群成员管理 ──────────────────────────────────────────────────
    async def list_chat_members(
        self,
        chat_id: str,
        member_id_type: str = "open_id",
        page_size: int = 50,
    ) -> dict:
        """获取群成员列表。"""
        return await self._client.request(
            "GET",
            f"/im/v1/chats/{chat_id}/members",
            params={"member_id_type": member_id_type, "page_size": str(page_size)},
        )

    async def add_chat_members(
        self,
        chat_id: str,
        id_list: list[str],
        id_type: str = "open_id",
    ) -> dict:
        """添加群成员。"""
        return await self._client.request(
            "POST",
            f"/im/v1/chats/{chat_id}/members",
            json={"id_list": id_list},
            params={"member_id_type": id_type},
        )

    async def remove_chat_members(
        self,
        chat_id: str,
        id_list: list[str],
        id_type: str = "open_id",
    ) -> dict:
        """移除群成员。"""
        return await self._client.request(
            "DELETE",
            f"/im/v1/chats/{chat_id}/members",
            params={"member_id_type": id_type},
            json={"id_list": id_list},
        )

    # ── 群管理员 ────────────────────────────────────────────────────
    async def set_chat_admin(self, chat_id: str, user_id_list: list[str]) -> dict:
        """设置群管理员。"""
        return await self._client.request(
            "POST",
            f"/im/v1/chats/{chat_id}/managers",
            json={"manager_list": [{"member_id": uid} for uid in user_id_list]},
        )

    async def remove_chat_admin(self, chat_id: str, user_id_list: list[str]) -> dict:
        """移除群管理员。"""
        return await self._client.request(
            "DELETE",
            f"/im/v1/chats/{chat_id}/managers",
            json={"manager_list": [{"member_id": uid} for uid in user_id_list]},
        )

    # ── 群公告 & 置顶 ──────────────────────────────────────────────
    async def pin_message(self, chat_id: str, message_id: str) -> dict:
        """置顶消息。"""
        return await self._client.request(
            "POST",
            f"/im/v1/chats/{chat_id}/pins",
            json={"message_id": message_id},
        )

    async def unpin_message(self, chat_id: str, message_id: str) -> dict:
        """取消置顶。"""
        return await self._client.request(
            "DELETE",
            f"/im/v1/chats/{chat_id}/pins",
            json={"message_id": message_id},
        )

    async def list_pins(self, chat_id: str) -> dict:
        """获取置顶消息列表。"""
        return await self._client.request("GET", f"/im/v1/chats/{chat_id}/pins")

    # ── 群标签 ──────────────────────────────────────────────────────
    async def set_chat_top_notice(self, chat_id: str, content: str) -> dict:
        """设置群公告。"""
        return await self._client.request(
            "POST",
            f"/im/v1/chats/{chat_id}/top_notice",
            json={"chat_top_notice": {"content": {"text": content}}},
        )

    async def delete_chat_top_notice(self, chat_id: str) -> dict:
        """删除群公告。"""
        return await self._client.request(
            "DELETE",
            f"/im/v1/chats/{chat_id}/top_notice",
        )
