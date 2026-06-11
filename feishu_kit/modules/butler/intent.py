"""Intent Router + Goal Extractor — classify user messages and extract structured goals."""

import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from feishu_kit.modules.butler.llm import call_llm_json

logger = logging.getLogger(__name__)

# ── Intent types ──────────────────────────────────────────────────

CREATE_TASK = "create_task"
CREATE_REMINDER = "create_reminder"
CREATE_EVENT = "create_event"
CREATE_NOTE = "create_note"
QUERY_INFO = "query_info"
GENERAL_CHAT = "general_chat"
CANCEL = "cancel"
CONFIRM = "confirm"
DENY = "deny"
UPDATE_TASK = "update_task"

ALL_INTENTS = [
    CREATE_TASK, CREATE_REMINDER, CREATE_EVENT, CREATE_NOTE,
    QUERY_INFO, GENERAL_CHAT, CANCEL, CONFIRM, DENY, UPDATE_TASK,
]


def _build_context_block(history: list[dict], recent_results: list[dict] | None = None) -> str:
    """Build a context block from conversation history and recent action results."""
    parts = []

    # Recent conversation (last 6 messages)
    if history:
        recent = history[-6:]
        lines = []
        for msg in recent:
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")[:150]
            lines.append(f"{role}: {content}")
        parts.append("最近对话:\n" + "\n".join(lines))

    # Recent action results (completed goals/plans)
    if recent_results:
        lines = []
        for r in recent_results:
            intent = r.get("intent", "")
            summary = r.get("summary", "")[:100]
            task_id = r.get("task_id", "")
            result_data = r.get("result", "")
            if intent == "create_task" and task_id:
                lines.append(f"刚刚创建了任务: 标题=\"{summary}\" task_id={task_id}")
            elif intent == "create_reminder":
                lines.append(f"刚刚创建了提醒: {summary}")
            elif intent:
                lines.append(f"最近操作: {intent} {summary}")
        if lines:
            parts.append("最近完成的操作:\n" + "\n".join(lines))

    if not parts:
        return ""
    return "\n\n".join(parts)


# ── Intent classification prompt ──────────────────────────────────

_CLASSIFY_SYSTEM = """你是一个意图分类器。根据用户消息和对话上下文，返回一个 JSON 对象。

可能的意图：
- create_task: 用户想创建任务/待办
- create_reminder: 用户想设置提醒/闹钟/备忘
- create_event: 用户想创建日历日程/会议
- create_note: 用户想写笔记/记录/文档到飞书 Wiki
- update_task: 用户想修改/更新之前的任务（改标题/描述/时间/分组等）
- query_info: 用户在询问信息（查天气、查日历、查任务等）
- general_chat: 普通闲聊/问答
- cancel: 用户想取消某个操作
- confirm: 用户确认/同意/好的/可以
- deny: 用户否认/取消/不要

注意：如果用户提到"改"、"修改"、"换成"、"更新"等词，并且上下文中有刚创建的任务/提醒/日程，应该归类为 update_task 或对应类型的更新操作。

仅返回 JSON，不要多余文字：
{"intent": "<intent>", "confidence": <0.0-1.0>}"""


async def classify_intent(
    user_text: str,
    history: list[dict] | None = None,
    recent_results: list[dict] | None = None,
) -> dict:
    """Classify user message intent with conversation context."""
    try:
        messages = [{"role": "system", "content": _CLASSIFY_SYSTEM}]

        context = _build_context_block(history or [], recent_results)
        prompt = user_text
        if context:
            prompt = f"上下文:\n{context}\n\n当前消息: {user_text}"

        messages.append({"role": "user", "content": prompt})
        result = await call_llm_json(messages, temperature=0.0)
        intent = result.get("intent", GENERAL_CHAT)
        if intent not in ALL_INTENTS:
            intent = GENERAL_CHAT
        return result
    except Exception as e:
        logger.warning("Intent classification failed: %s", e)
        return {"intent": GENERAL_CHAT, "confidence": 0.0}


# ── Goal extraction prompt ────────────────────────────────────────

_EXTRACT_SYSTEM = """你是一个信息提取器。根据用户消息和对话上下文，提取结构化字段。

根据意图返回对应字段。仅返回 JSON，不要多余文字。

对于 create_task:
{"title": "任务标题", "description": "描述", "due_time": "ISO时间或空", "assignee": "人或空", "priority": "high/medium/low或空"}

对于 update_task:
{"task_id": "任务ID（从上下文获取）", "updates": {"summary": "新标题或空", "description": "新描述或空"}, "reason": "修改原因"}

对于 create_reminder:
{"message": "提醒内容", "fire_at": "ISO时间或相对时间如'3小时后'", "recurring": "daily/weekly/空"}

对于 create_event:
{"summary": "日程标题", "start_time": "ISO时间", "end_time": "ISO时间或空", "location": "地点或空", "description": "描述或空"}

对于 create_note:
{"title": "笔记标题", "content": "笔记内容概要", "space_id": "或空", "parent_node": "或空"}

对于 query_info:
{"query_type": "calendar/tasks/contacts/wiki/general", "query": "查询内容"}

重要规则：
1. 如果用户说"修改"、"改下"、"换"等，从上下文中找到最近创建的对象的ID和标题
2. 用户消息中省略的字段（用代词如"它"、"那个"指代）从上下文推断
3. 如果某个字段无法从消息和上下文中确定，设为空字符串
4. 如果消息不足以提取任何有意义的信息，返回 {"_insufficient": true, "missing": ["字段1", "字段2"]}
"""


async def extract_goal(
    intent: str, user_text: str,
    history: list[dict] | None = None,
    recent_results: list[dict] | None = None,
) -> dict:
    """Extract structured fields from user message with context."""
    try:
        context = _build_context_block(history or [], recent_results)
        prompt = f"意图: {intent}\n用户消息: {user_text}"
        if context:
            prompt = f"上下文:\n{context}\n\n{prompt}"

        result = await call_llm_json([
            {"role": "system", "content": _EXTRACT_SYSTEM},
            {"role": "user", "content": prompt},
        ], temperature=0.0)
        result["_intent"] = intent
        return result
    except Exception as e:
        logger.warning("Goal extraction failed: %s", e)
        return {"_intent": intent, "_insufficient": True, "missing": ["all"], "error": str(e)}


def parse_relative_time(time_str: str, tz_name: str = "Asia/Shanghai") -> float | None:
    """Parse relative time strings to Unix timestamp.

    Supports: '3小时后', '明天下午3点', '后天', etc.
    Returns None if cannot parse.
    """
    if not time_str:
        return None
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)

    # Absolute ISO format
    try:
        dt = datetime.fromisoformat(time_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=tz)
        return dt.timestamp()
    except (ValueError, TypeError):
        pass

    # Common relative patterns
    import re
    s = time_str.strip()

    # "X分钟后"
    m = re.match(r"(\d+)\s*分钟[之以]?后", s)
    if m:
        return (now + timedelta(minutes=int(m.group(1)))).timestamp()

    # "X小时后"
    m = re.match(r"(\d+)\s*小时[之以]?后", s)
    if m:
        return (now + timedelta(hours=int(m.group(1)))).timestamp()

    # "X天后"
    m = re.match(r"(\d+)\s*天[之以]?后", s)
    if m:
        return (now + timedelta(days=int(m.group(1)))).timestamp()

    # "明天"
    if "明天" in s:
        target = now + timedelta(days=1)
        m = re.search(r"(\d+)[:点](\d+)", s)
        if m:
            target = target.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0)
        elif "上午" in s:
            target = target.replace(hour=9, minute=0, second=0)
        elif "下午" in s:
            target = target.replace(hour=14, minute=0, second=0)
        elif "晚上" in s or "晚上" in s:
            target = target.replace(hour=20, minute=0, second=0)
        else:
            target = target.replace(hour=9, minute=0, second=0)
        return target.timestamp()

    # "后天"
    if "后天" in s:
        target = now + timedelta(days=2)
        m = re.search(r"(\d+)[:点](\d+)", s)
        if m:
            target = target.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0)
        else:
            target = target.replace(hour=9, minute=0, second=0)
        return target.timestamp()

    # "今天下午X点" etc
    if "今天" in s:
        target = now
        m = re.search(r"(\d+)[:点](\d+)", s)
        if m:
            h = int(m.group(1))
            if "下午" in s and h < 12:
                h += 12
            target = target.replace(hour=h, minute=int(m.group(2)), second=0)
        return target.timestamp()

    # "下午X点" / "晚上X点" today
    if re.search(r"下午|晚上|傍晚", s):
        m = re.search(r"(\d+)[:点](\d+)?", s)
        if m:
            h = int(m.group(1))
            if h < 12:
                h += 12
            mins = int(m.group(2)) if m.group(2) else 0
            target = now.replace(hour=h, minute=mins, second=0)
            return target.timestamp()

    # Fallback: try "HH:MM" or "N点MM分" today
    m = re.search(r"(\d{1,2})[:点](\d{1,2})", s)
    if m:
        h, mins = int(m.group(1)), int(m.group(2))
        target = now.replace(hour=h, minute=mins, second=0)
        return target.timestamp()

    # Pure "N点" without minutes (e.g. "10点")
    m = re.search(r"(\d{1,2})\s*点", s)
    if m:
        h = int(m.group(1))
        target = now.replace(hour=h, minute=0, second=0)
        # If the time has already passed today, assume tomorrow
        if target <= now:
            target += timedelta(days=1)
        return target.timestamp()

    return None
