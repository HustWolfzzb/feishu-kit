"""Approval Manager — handle CONFIRM_REQUIRED actions with user confirmation."""

import logging

from feishu_kit.modules.butler.store import Store

logger = logging.getLogger(__name__)


class ApprovalManager:
    """Manages approval flow for risky actions."""

    def __init__(self, store: Store):
        self._store = store

    def request_approval(
        self, goal_id: int, step_id: int,
        chat_id: str, open_id: str,
        action: str, params: dict,
    ) -> int:
        """Create a pending approval request.

        Returns the approval ID.
        """
        approval_id = self._store.create_approval(
            goal_id, step_id, chat_id, open_id, action, params
        )
        self._store.audit(
            "approval_requested", f"step_{step_id}",
            f"approval_id={approval_id}", "CONFIRM_REQUIRED",
            chat_id, open_id,
        )
        logger.info("Approval requested: id=%d action=%s chat=%s", approval_id, action, chat_id)
        return approval_id

    def format_approval_message(self, action: str, params: dict) -> str:
        """Generate a human-readable confirmation message."""
        action_desc = {
            "send_message_to_user": f"发送消息给用户 {params.get('receive_id', '?')}",
            "send_message_to_chat": f"发送消息到群聊 {params.get('receive_id', '?')}",
            "add_permission": f"修改权限: {params}",
            "transfer_owner": f"转移所有者: {params}",
            "delete_file": f"删除文件: {params}",
            "delete_node": f"删除节点: {params}",
            "disband_chat": f"解散群聊: {params}",
        }
        desc = action_desc.get(action, f"执行操作: {action} ({params})")
        return f"需要确认：{desc}\n\n回复「确认」或「取消」来继续。"

    def check_response(self, chat_id: str, user_text: str) -> dict | None:
        """Check if user text is a confirm/deny response to a pending approval.

        Returns:
            None if no pending approval or text is not a response.
            {"approved": bool, "approval_id": int, "step_id": int} if resolved.
        """
        approval = self._store.get_pending_approval(chat_id)
        if not approval:
            return None

        text = user_text.strip().lower()
        confirm_words = {"确认", "好的", "可以", "同意", "confirm", "yes", "是", "ok", "确定", "没问题"}
        deny_words = {"取消", "拒绝", "不要", "cancel", "no", "否", "算了", "不用了"}

        if text in confirm_words:
            self._store.resolve_approval(approval["id"], approved=True)
            self._store.audit(
                "approval_granted", f"approval_{approval['id']}",
                "approved", "CONFIRM_REQUIRED",
                chat_id, "",
            )
            logger.info("Approval granted: id=%d", approval["id"])
            return {
                "approved": True,
                "approval_id": approval["id"],
                "step_id": approval["step_id"],
            }

        if text in deny_words:
            self._store.resolve_approval(approval["id"], approved=False)
            self._store.audit(
                "approval_denied", f"approval_{approval['id']}",
                "denied", "CONFIRM_REQUIRED",
                chat_id, "",
            )
            logger.info("Approval denied: id=%d", approval["id"])
            return {
                "approved": False,
                "approval_id": approval["id"],
                "step_id": approval["step_id"],
            }

        # Not a confirm/deny response
        return None

    def get_pending(self, chat_id: str) -> dict | None:
        """Get the current pending approval for a chat."""
        return self._store.get_pending_approval(chat_id)

    def is_approved(self, step_id: int, chat_id: str) -> bool:
        """Check if a specific step's approval has been granted."""
        approval = self._store.get_pending_approval(chat_id)
        if not approval:
            return False
        return approval["step_id"] == step_id and approval["status"] == "approved"
