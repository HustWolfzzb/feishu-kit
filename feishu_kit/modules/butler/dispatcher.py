"""Action Dispatcher — execute plan steps through existing Feishu module services."""

import json
import logging

from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.butler.store import Store

logger = logging.getLogger(__name__)


class ActionDispatcher:
    """Maps plan step actions to existing Feishu module service methods."""

    def __init__(self, client: FeishuClient, store: Store):
        self._client = client
        self._store = store

    def _task_service(self):
        from feishu_kit.modules.task.service import TaskService
        return TaskService(self._client)

    def _calendar_service(self):
        from feishu_kit.modules.calendar.service import CalendarService
        return CalendarService(self._client)

    def _messaging_service(self):
        from feishu_kit.modules.messaging.service import MessagingService
        return MessagingService(self._client)

    def _wiki_service(self):
        from feishu_kit.modules.wiki.service import WikiService
        return WikiService(self._client)

    def _contacts_service(self):
        from feishu_kit.modules.contacts.service import ContactsService
        return ContactsService(self._client)

    def _md2feishu_service(self):
        from feishu_kit.modules.md2feishu.service import Md2FeishuService
        return Md2FeishuService(self._client)

    async def dispatch(self, action: str, params: dict, context: dict) -> dict:
        """Execute a single action and return the result.

        Args:
            action: Action name from plan step.
            params: Action parameters.
            context: Execution context (chat_id, open_id, message_id, etc.)

        Returns:
            {"success": bool, "data": ..., "error": ...}
        """
        handler = getattr(self, f"_do_{action}", None)
        if handler is None:
            return {"success": False, "error": f"Unknown action: {action}"}

        try:
            result = await handler(params, context)
            return {"success": True, "data": result}
        except Exception as e:
            logger.error("Action %s failed: %s", action, e, exc_info=True)
            return {"success": False, "error": str(e)}

    # ── Task actions ──────────────────────────────────────────────

    async def _do_create_task(self, params: dict, ctx: dict) -> dict:
        svc = self._task_service()
        body: dict = {"summary": params.get("summary", "Untitled task")}
        if params.get("description"):
            body["description"] = params["description"]
        if params.get("due_at"):
            body["due_at"] = params["due_at"]
        # Add members from params
        if params.get("members"):
            body["members"] = params["members"]
        # Default: add the requesting user as assignee so task shows in their task center
        open_id = ctx.get("open_id", "")
        if open_id:
            members = body.get("members", [])
            existing_ids = {m.get("id") for m in members}
            if open_id not in existing_ids:
                members.append({"id": open_id, "type": "user", "role": "assignee"})
            body["members"] = members
        if params.get("assignee_open_id"):
            body.setdefault("members", []).append({
                "id": params["assignee_open_id"],
                "type": "user",
                "role": "assignee",
            })
        result = await svc.create_task(body)
        self._store.audit("create_task", str(result.get("data", {}).get("task", {}).get("guid", "")),
                          "success", "AUTO_EXECUTE", ctx.get("chat_id", ""), ctx.get("open_id", ""))
        return result

    async def _do_complete_task(self, params: dict, ctx: dict) -> dict:
        svc = self._task_service()
        result = await svc.complete_task(params["task_id"])
        self._store.audit("complete_task", params["task_id"], "success", "AUTO_EXECUTE",
                          ctx.get("chat_id", ""), ctx.get("open_id", ""))
        return result

    async def _do_list_tasks(self, params: dict, ctx: dict) -> dict:
        svc = self._task_service()
        return await svc.list_tasks(page_size=params.get("page_size", 20))

    async def _do_update_task(self, params: dict, ctx: dict) -> dict:
        svc = self._task_service()
        task_id = params.get("task_id", "")
        updates = {}
        if params.get("summary"):
            updates["summary"] = params["summary"]
        if params.get("description"):
            updates["description"] = params["description"]
        if params.get("due_at"):
            updates["due_at"] = params["due_at"]
        # Merge any extra update fields
        for key in params:
            if key not in ("task_id",) and params[key]:
                updates.setdefault(key, params[key])
        result = await svc.update_task(task_id, updates)
        self._store.audit("update_task", task_id, "success", "AUTO_EXECUTE",
                          ctx.get("chat_id", ""), ctx.get("open_id", ""))
        return result

    # ── Reminder actions ──────────────────────────────────────────

    async def _do_create_reminder(self, params: dict, ctx: dict) -> dict:
        fire_at = params.get("fire_at", 0)
        # Try to parse string time if not already a number
        if isinstance(fire_at, str):
            from feishu_kit.modules.butler.intent import parse_relative_time
            from feishu_kit.core.settings import Settings as settings
            parsed = parse_relative_time(fire_at, settings.butler_timezone)
            fire_at = parsed if parsed else 0
        reminder_id = self._store.create_reminder(
            chat_id=ctx.get("chat_id", ""),
            open_id=ctx.get("open_id", ""),
            message=params.get("message", "提醒"),
            fire_at=float(fire_at) if fire_at else 0,
            recurring=params.get("recurring"),
        )
        self._store.audit("create_reminder", str(reminder_id), "success", "AUTO_EXECUTE",
                          ctx.get("chat_id", ""), ctx.get("open_id", ""))
        return {"reminder_id": reminder_id}

    async def _do_cancel_reminder(self, params: dict, ctx: dict) -> dict:
        self._store.cancel_reminder(params["reminder_id"])
        self._store.audit("cancel_reminder", str(params["reminder_id"]), "success", "AUTO_EXECUTE",
                          ctx.get("chat_id", ""), ctx.get("open_id", ""))
        return {"cancelled": True}

    # ── Calendar actions ──────────────────────────────────────────

    async def _do_create_event(self, params: dict, ctx: dict) -> dict:
        svc = self._calendar_service()
        calendar_id = params.get("calendar_id", "")
        if not calendar_id:
            cal = await svc.get_primary()
            calendar_id = cal.get("data", {}).get("calendar", {}).get("calendar_id", "")
        event: dict = {"summary": params.get("summary", "")}
        if params.get("start_time"):
            event["start_time"] = params["start_time"]
        if params.get("end_time"):
            event["end_time"] = params["end_time"]
        if params.get("location"):
            event["location"] = {"name": params["location"]}
        if params.get("description"):
            event["description"] = params["description"]
        result = await svc.create_event(calendar_id, event)
        self._store.audit("create_event", calendar_id, "success", "AUTO_EXECUTE",
                          ctx.get("chat_id", ""), ctx.get("open_id", ""))
        return result

    async def _do_list_events(self, params: dict, ctx: dict) -> dict:
        svc = self._calendar_service()
        calendar_id = params.get("calendar_id", "")
        if not calendar_id:
            cal = await svc.get_primary()
            calendar_id = cal.get("data", {}).get("calendar", {}).get("calendar_id", "")
        return await svc.list_events(
            calendar_id,
            start_time=params.get("start_time", ""),
            end_time=params.get("end_time", ""),
        )

    # ── Note / Wiki actions ───────────────────────────────────────

    async def _do_create_note(self, params: dict, ctx: dict) -> dict:
        from feishu_kit.core.settings import Settings as settings
        svc = self._md2feishu_service()
        space_id = params.get("space_id") or settings.butler_default_space_id
        result = await svc.push_markdown(
            markdown=params.get("content", ""),
            title=params.get("title", "笔记"),
            space_id=space_id,
            parent_node_token=params.get("parent_node_token"),
        )
        self._store.audit("create_note", params.get("title", ""), "success", "AUTO_EXECUTE",
                          ctx.get("chat_id", ""), ctx.get("open_id", ""))
        return result

    async def _do_search_wiki(self, params: dict, ctx: dict) -> dict:
        svc = self._wiki_service()
        space_id = params.get("space_id", "")
        return await svc.search_nodes(space_id, params.get("keyword", ""))

    # ── Messaging actions ─────────────────────────────────────────

    async def _do_send_message_to_user(self, params: dict, ctx: dict) -> dict:
        svc = self._messaging_service()
        content = json.dumps({"text": params.get("text", "")})
        result = await svc.send_message(
            params["receive_id"], "text", content, "open_id"
        )
        self._store.audit("send_message_to_user", params["receive_id"], "success", "CONFIRM_REQUIRED",
                          ctx.get("chat_id", ""), ctx.get("open_id", ""))
        return result

    async def _do_send_message_to_chat(self, params: dict, ctx: dict) -> dict:
        svc = self._messaging_service()
        content = json.dumps({"text": params.get("text", "")})
        result = await svc.send_message(
            params["receive_id"], "text", content, "chat_id"
        )
        self._store.audit("send_message_to_chat", params["receive_id"], "success", "CONFIRM_REQUIRED",
                          ctx.get("chat_id", ""), ctx.get("open_id", ""))
        return result

    async def _do_reply_message(self, params: dict, ctx: dict) -> dict:
        svc = self._messaging_service()
        content = json.dumps({"text": params.get("text", "")})
        message_id = params.get("message_id") or ctx.get("message_id", "")
        result = await svc.reply_message(message_id, "text", content)
        self._store.audit("reply_message", message_id, "success", "AUTO_EXECUTE",
                          ctx.get("chat_id", ""), ctx.get("open_id", ""))
        return result

    # ── Contacts actions ──────────────────────────────────────────

    async def _do_get_user(self, params: dict, ctx: dict) -> dict:
        svc = self._contacts_service()
        return await svc.get_user(
            params.get("user_id", ""),
            user_id_type=params.get("user_id_type", "open_id"),
        )

    async def _do_list_departments(self, params: dict, ctx: dict) -> dict:
        svc = self._contacts_service()
        parent_id = params.get("parent_department_id", "0")
        return await svc.list_departments(parent_department_id=parent_id)

    # ── General ──────────────────────────────────────────────────

    async def _do_general_query(self, params: dict, ctx: dict) -> dict:
        # Handled by LLM directly, not dispatched
        return {"query": params.get("query", "")}
