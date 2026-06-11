"""Butler Engine — main orchestration pipeline for processing user messages."""

import json
import logging
import time

from feishu_kit.core.client import FeishuClient
from feishu_kit.modules.butler.approval import ApprovalManager
from feishu_kit.modules.butler.clarifier import check_missing_fields, clarify_with_llm
from feishu_kit.modules.butler.dispatcher import ActionDispatcher
from feishu_kit.modules.butler.intent import (
    classify_intent, extract_goal, parse_relative_time,
    CONFIRM, DENY, CANCEL, GENERAL_CHAT, QUERY_INFO, UPDATE_TASK,
)
from feishu_kit.modules.butler.llm import call_llm
from feishu_kit.modules.butler.planner import generate_plan, review_plan_safety
from feishu_kit.modules.butler.scheduler import ReminderScheduler
from feishu_kit.modules.butler.store import Store

logger = logging.getLogger(__name__)


class ButlerEngine:
    """Orchestrates the full message processing pipeline."""

    def __init__(self, client: FeishuClient, store: Store):
        self._client = client
        self._store = store
        self._dispatcher = ActionDispatcher(client, store)
        self._approval = ApprovalManager(store)
        self._scheduler = ReminderScheduler(store, client)

    @property
    def scheduler(self) -> ReminderScheduler:
        return self._scheduler

    @property
    def store(self) -> Store:
        return self._store

    async def process_message(
        self, chat_id: str, open_id: str, message_id: str, user_text: str
    ) -> str:
        """Process a user message through the full pipeline.

        Returns the reply text to send back to the user.
        """
        logger.info(
            "Butler processing: chat=%s user=%s text=%s",
            chat_id, open_id, user_text[:80],
        )

        # Save user message
        self._store.append_conversation(chat_id, open_id, "user", user_text)

        try:
            reply = await self._pipeline(chat_id, open_id, message_id, user_text)
        except Exception as e:
            logger.error("Pipeline error: %s", e, exc_info=True)
            reply = f"抱歉，处理消息时遇到了问题: {e}"
            self._store.audit("pipeline_error", "", str(e), "", chat_id, open_id)

        # Save assistant reply
        self._store.append_conversation(chat_id, open_id, "assistant", reply)
        return reply

    def _get_context(self, chat_id: str) -> tuple[list[dict], list[dict]]:
        """Get conversation history and recent action results for context."""
        history = self._store.get_conversation_history(chat_id, limit=20)

        # Get recent completed goals and their results
        recent_results = []
        rows = self._store.conn.execute(
            "SELECT g.id, g.intent, g.fields_json, g.status, "
            "ps.result_json FROM goals g "
            "LEFT JOIN plan_steps ps ON ps.plan_id = "
            "(SELECT id FROM plans WHERE goal_id = g.id ORDER BY id DESC LIMIT 1) "
            "AND ps.status = 'done' "
            "WHERE g.chat_id = ? AND g.status = 'completed' "
            "ORDER BY g.id DESC LIMIT 3",
            (chat_id,),
        ).fetchall()
        for r in rows:
            entry = {"intent": r[1], "summary": ""}
            try:
                fields = json.loads(r[2]) if r[2] else {}
                entry["summary"] = fields.get("title") or fields.get("summary") or fields.get("message") or ""
            except Exception:
                pass
            try:
                if r[4]:
                    result_data = json.loads(r[4])
                    # Extract task_id from create_task results
                    task_info = result_data.get("data", {}).get("task", {})
                    if task_info:
                        entry["task_id"] = task_info.get("guid", "")
                        entry["task_summary"] = task_info.get("summary", "")
            except Exception:
                pass
            recent_results.append(entry)

        return history, recent_results

    async def _pipeline(
        self, chat_id: str, open_id: str, message_id: str, user_text: str
    ) -> str:
        """The core processing pipeline."""

        # ── Step 1: Check for pending approval response ────────────
        approval_result = self._approval.check_response(chat_id, user_text)
        if approval_result is not None:
            return await self._handle_approval_response(
                chat_id, open_id, message_id, approval_result
            )

        # ── Build context for this conversation ─────────────────────
        history, recent_results = self._get_context(chat_id)

        # ── Step 2: Classify intent WITH context ────────────────────
        classification = await classify_intent(user_text, history, recent_results)
        intent = classification.get("intent", GENERAL_CHAT)
        confidence = classification.get("confidence", 0.0)
        logger.info("Intent: %s (confidence=%.2f)", intent, confidence)

        # ── Step 3: Handle simple intents immediately ──────────────
        if intent == CANCEL:
            return await self._handle_cancel(chat_id, open_id)

        if intent == GENERAL_CHAT:
            return await self._handle_general_chat(chat_id, open_id, user_text)

        if intent == QUERY_INFO:
            return await self._handle_query(chat_id, open_id, user_text, history, recent_results)

        if intent == UPDATE_TASK:
            return await self._handle_update(chat_id, open_id, user_text, history, recent_results)

        # ── Step 4: Extract goal WITH context ───────────────────────
        goal_fields = await extract_goal(intent, user_text, history, recent_results)
        logger.info("Goal fields: %s", {k: v for k, v in goal_fields.items() if not k.startswith("_")})

        # ── Step 5: Check for missing fields ───────────────────────
        missing = check_missing_fields(intent, goal_fields)
        if missing:
            question = await clarify_with_llm(intent, user_text, missing)
            self._store.append_conversation(
                chat_id, open_id, "assistant", question, intent
            )
            return question

        # ── Step 6: Process time fields ────────────────────────────
        goal_fields = self._process_time_fields(goal_fields)

        # ── Step 7: Generate plan WITH context ──────────────────────
        context_hint = self._build_context_hint(recent_results)
        steps = await generate_plan(intent, goal_fields, context_hint)
        if not steps:
            return "抱歉，我无法理解这个请求的执行计划。能否换个方式描述一下？"

        # ── Step 8: Review plan safety ─────────────────────────────
        steps = review_plan_safety(steps, open_id)

        # ── Step 9: Create goal and plan in store ──────────────────
        goal_id = self._store.create_goal(chat_id, open_id, intent, goal_fields)
        plan_id = self._store.create_plan(goal_id)

        step_summaries = []
        for step in steps:
            step_id = self._store.add_plan_step(
                plan_id, step["seq"], step["action"],
                step.get("params", {}), step.get("safety", "AUTO_EXECUTE"),
            )
            step_summaries.append({
                "step_id": step_id,
                "action": step["action"],
                "safety": step.get("safety", "AUTO_EXECUTE"),
                "description": step.get("description", ""),
            })

        # ── Step 10: Execute plan ──────────────────────────────────
        return await self._execute_plan(
            chat_id, open_id, message_id, goal_id, plan_id, step_summaries
        )

    def _build_context_hint(self, recent_results: list[dict]) -> str:
        """Build a short text hint about recent actions for plan generation."""
        if not recent_results:
            return ""
        parts = []
        for r in recent_results:
            intent = r.get("intent", "")
            summary = r.get("summary", "")
            task_id = r.get("task_id", "")
            if intent == "create_task" and task_id:
                parts.append(f"刚创建的任务: \"{summary}\" (guid={task_id})")
            elif intent == "create_reminder":
                parts.append(f"刚创建的提醒: \"{summary}\"")
        return "最近操作上下文: " + "; ".join(parts) if parts else ""

    async def _handle_update(
        self, chat_id: str, open_id: str, user_text: str,
        history: list[dict], recent_results: list[dict],
    ) -> str:
        """Handle update/modify requests referencing previous actions."""
        goal_fields = await extract_goal("update_task", user_text, history, recent_results)

        # Find the most recent task to update
        task_guid = goal_fields.get("task_id", "")
        updates = goal_fields.get("updates", {})
        reason = goal_fields.get("reason", "")

        if not task_guid:
            # Try to find from recent results
            for r in recent_results:
                if r.get("task_id"):
                    task_guid = r["task_id"]
                    break

        if not task_guid:
            return "没有找到可以修改的任务。请先创建一个任务。"

        if not updates:
            return "请问你想怎么修改这个任务？"

        # Execute the update
        ctx = {"chat_id": chat_id, "open_id": open_id}
        result = await self._dispatcher.dispatch(
            "update_task", {"task_id": task_guid, **updates}, ctx
        )

        if result["success"]:
            self._store.audit("update_task", task_guid, "success", "AUTO_EXECUTE", chat_id, open_id)
            summary = goal_fields.get("task_summary", task_guid)
            return f"已更新任务「{summary}」{('：' + reason) if reason else ''}"
        else:
            return f"更新任务失败: {result.get('error', '未知错误')}"

    async def _execute_plan(
        self, chat_id: str, open_id: str, message_id: str,
        goal_id: int, plan_id: int, step_summaries: list[dict],
    ) -> str:
        """Execute a plan step by step, pausing for approvals."""
        self._store.update_plan_status(plan_id, "executing")
        results = []

        for summary in step_summaries:
            step_id = summary["step_id"]
            action = summary["action"]
            safety = summary["safety"]

            # Check safety
            if safety == "DENY":
                self._store.update_step(step_id, status="failed", error="Action denied by policy")
                results.append(f"- {summary.get('description', action)}: 已拒绝（安全策略）")
                continue

            if safety == "ADMIN_ONLY":
                self._store.update_step(step_id, status="failed", error="Requires admin")
                results.append(f"- {summary.get('description', action)}: 需要管理员权限")
                continue

            if safety == "CONFIRM_REQUIRED":
                # Pause execution and request approval
                step = self._store.get_next_executable_step(plan_id)
                if step:
                    params = step.get("params", {})
                    self._approval.request_approval(
                        goal_id, step_id, chat_id, open_id, action, params
                    )
                    self._store.update_plan_status(plan_id, "executing")
                    approval_msg = self._approval.format_approval_message(action, params)
                    return f"执行计划暂停，需要确认：\n\n{approval_msg}"

            # Execute the step
            step = self._store.get_next_executable_step(plan_id)
            if not step:
                break

            self._store.update_step(step_id, status="running")
            ctx = {"chat_id": chat_id, "open_id": open_id, "message_id": message_id}
            result = await self._dispatcher.dispatch(action, step.get("params", {}), ctx)

            if result["success"]:
                self._store.update_step(step_id, status="done", result=result.get("data"))
                results.append(f"- {summary.get('description', action)}: 完成")
                # Schedule reminders if this was a create_reminder action
                if action == "create_reminder" and result.get("data", {}).get("reminder_id"):
                    reminder_id = result["data"]["reminder_id"]
                    fire_at = step.get("params", {}).get("fire_at", 0)
                    if fire_at:
                        self._scheduler.schedule(reminder_id, float(fire_at))
            else:
                self._store.update_step(step_id, status="failed", error=result.get("error", ""))
                results.append(f"- {summary.get('description', action)}: 失败 - {result.get('error', '未知错误')}")

        # All steps done
        self._store.update_plan_status(plan_id, "completed")
        self._store.update_goal(goal_id, status="completed")
        self._store.audit("plan_completed", str(plan_id), "done", "", chat_id, open_id)

        reply = "计划执行完成：\n" + "\n".join(results)
        return reply

    async def _handle_approval_response(
        self, chat_id: str, open_id: str, message_id: str, result: dict
    ) -> str:
        """Handle user confirm/deny for a pending approval."""
        if not result["approved"]:
            goal = self._store.get_active_goal(chat_id)
            if goal:
                plan = self._store.get_plan_for_goal(goal["id"])
                if plan:
                    self._store.update_plan_status(plan["id"], "cancelled")
                self._store.update_goal(goal["id"], status="cancelled")
            return "好的，已取消操作。"

        goal = self._store.get_active_goal(chat_id)
        if not goal:
            return "没有找到待执行的计划。"

        plan = self._store.get_plan_for_goal(goal["id"])
        if not plan:
            return "没有找到待执行的计划。"

        results = []
        remaining_steps = [s for s in plan["steps"] if s["status"] == "pending"]

        for step in remaining_steps:
            self._store.update_step(step["id"], status="running")
            ctx = {"chat_id": chat_id, "open_id": open_id, "message_id": message_id}
            dispatch_result = await self._dispatcher.dispatch(
                step["action"], step.get("params", {}), ctx
            )
            if dispatch_result["success"]:
                self._store.update_step(step["id"], status="done", result=dispatch_result.get("data"))
                results.append(f"- {step['action']}: 完成")
            else:
                self._store.update_step(step["id"], status="failed", error=dispatch_result.get("error", ""))
                results.append(f"- {step['action']}: 失败 - {dispatch_result.get('error', '')}")

        self._store.update_plan_status(plan["id"], "completed")
        self._store.update_goal(goal["id"], status="completed")
        return "已确认，继续执行：\n" + "\n".join(results)

    async def _handle_cancel(self, chat_id: str, open_id: str) -> str:
        """Cancel the current active goal."""
        goal = self._store.get_active_goal(chat_id)
        if not goal:
            return "没有正在进行的任务需要取消。"

        plan = self._store.get_plan_for_goal(goal["id"])
        if plan:
            self._store.update_plan_status(plan["id"], "cancelled")
        self._store.update_goal(goal["id"], status="cancelled")
        return "好的，已取消当前任务。"

    async def _handle_general_chat(self, chat_id: str, open_id: str, user_text: str) -> str:
        """Handle general chat using LLM with conversation history."""
        from feishu_kit.core.settings import Settings as settings

        history = self._store.get_conversation_history(chat_id, limit=20)
        messages = [{"role": "system", "content": settings.chat_system_prompt}]
        for msg in history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        messages.append({"role": "user", "content": user_text})

        reply = await call_llm(messages)
        return reply

    async def _handle_query(
        self, chat_id: str, open_id: str, user_text: str,
        history: list[dict] | None = None, recent_results: list[dict] | None = None,
    ) -> str:
        """Handle information queries."""
        goal_fields = await extract_goal("query_info", user_text, history, recent_results)
        query_type = goal_fields.get("query_type", "general")

        if query_type == "calendar":
            try:
                result = await self._dispatcher.dispatch("list_events", {
                    "start_time": goal_fields.get("start_time", ""),
                    "end_time": goal_fields.get("end_time", ""),
                }, {"chat_id": chat_id, "open_id": open_id})
                if result["success"]:
                    events = result.get("data", {}).get("data", {}).get("items", [])
                    if not events:
                        return "没有找到日程。"
                    lines = [f"- {e.get('summary', '无标题')} ({e.get('start_time', {}).get('timestamp', '')})" for e in events[:5]]
                    return "近期日程：\n" + "\n".join(lines)
            except Exception as e:
                return f"查询日程失败: {e}"

        if query_type == "tasks":
            try:
                result = await self._dispatcher.dispatch("list_tasks", {}, {"chat_id": chat_id, "open_id": open_id})
                if result["success"]:
                    tasks = result.get("data", {}).get("data", {}).get("items", [])
                    if not tasks:
                        return "没有找到任务。"
                    lines = [f"- {t.get('summary', '无标题')} ({t.get('status', '')})" for t in tasks[:5]]
                    return "当前任务：\n" + "\n".join(lines)
            except Exception as e:
                return f"查询任务失败: {e}"

        return await self._handle_general_chat(chat_id, open_id, user_text)

    def _process_time_fields(self, fields: dict) -> dict:
        """Convert relative time strings to Unix timestamps in goal fields."""
        from feishu_kit.core.settings import Settings as settings

        for key in ("fire_at", "due_at"):
            val = fields.get(key, "")
            if val and isinstance(val, str) and not val.isdigit():
                ts = parse_relative_time(val, settings.butler_timezone)
                if ts:
                    fields[key] = ts

        return fields
