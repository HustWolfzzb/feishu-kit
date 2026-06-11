"""Plan Generator + Safety Policy — turn goals into executable step sequences."""

import logging

from feishu_kit.modules.butler.llm import call_llm_json

logger = logging.getLogger(__name__)

# ── Safety levels ─────────────────────────────────────────────────

AUTO_EXECUTE = "AUTO_EXECUTE"
CONFIRM_REQUIRED = "CONFIRM_REQUIRED"
ADMIN_ONLY = "ADMIN_ONLY"
DENY = "DENY"

# ── Safety policy rules ──────────────────────────────────────────

# Action -> default safety level
_SAFETY_RULES: dict[str, str] = {
    # Personal productivity — safe
    "create_task": AUTO_EXECUTE,
    "update_task": AUTO_EXECUTE,
    "complete_task": AUTO_EXECUTE,
    "list_tasks": AUTO_EXECUTE,
    "create_reminder": AUTO_EXECUTE,
    "cancel_reminder": AUTO_EXECUTE,
    "create_event": AUTO_EXECUTE,
    "list_events": AUTO_EXECUTE,
    "freebusy": AUTO_EXECUTE,
    "create_note": AUTO_EXECUTE,
    "list_wiki_spaces": AUTO_EXECUTE,
    "search_wiki": AUTO_EXECUTE,
    "get_user": AUTO_EXECUTE,
    "list_departments": AUTO_EXECUTE,
    # Messaging — needs confirmation
    "send_message_to_user": CONFIRM_REQUIRED,
    "send_message_to_chat": CONFIRM_REQUIRED,
    "reply_message": AUTO_EXECUTE,  # replying to the user who asked
    # Permissions — risky
    "add_permission": CONFIRM_REQUIRED,
    "transfer_owner": ADMIN_ONLY,
    "delete_file": ADMIN_ONLY,
    "delete_node": ADMIN_ONLY,
    "disband_chat": ADMIN_ONLY,
    # Generic
    "general_query": AUTO_EXECUTE,
}

# Overrides: send message to self is auto
_SEND_TO_SELF_OPEN_IDS: set[str] = set()


def classify_safety(action: str, params: dict, open_id: str = "") -> str:
    """Determine the safety level for an action.

    Args:
        action: The action name (e.g. "send_message_to_user").
        params: Action parameters.
        open_id: The user who initiated the action.

    Returns:
        One of AUTO_EXECUTE, CONFIRM_REQUIRED, ADMIN_ONLY, DENY.
    """
    level = _SAFETY_RULES.get(action, CONFIRM_REQUIRED)

    # Special: sending message to yourself is auto
    if action in ("send_message_to_user", "send_message_to_chat"):
        target = params.get("receive_id", "")
        if target == open_id or target in _SEND_TO_SELF_OPEN_IDS:
            return AUTO_EXECUTE

    return level


# ── Plan generation prompt ────────────────────────────────────────

_PLAN_SYSTEM = """你是一个任务规划器。根据用户意图和提取的字段，生成一个可执行的计划。

返回 JSON 数组，每个元素是一个步骤：
[
  {"seq": 1, "action": "<action_name>", "params": {...}, "description": "步骤描述"},
  ...
]

可用的 action：
- create_task: params={summary, description, due_at, assignee_open_id, members: [{id, role}]}
- update_task: params={task_id(guid), summary(新标题), description(新描述), due_at}
- complete_task: params={task_id}
- list_tasks: params={page_size}
- create_reminder: params={message, fire_at(unix timestamp), recurring}
- cancel_reminder: params={reminder_id}
- create_event: params={calendar_id, summary, start_time(ISO), end_time(ISO), location, description}
- list_events: params={calendar_id, start_time, end_time}
- create_note: params={title, content(markdown), space_id, parent_node_token}
- send_message_to_user: params={receive_id(open_id), text}
- send_message_to_chat: params={receive_id(chat_id), text}
- reply_message: params={message_id, text}
- search_wiki: params={space_id, keyword}
- get_user: params={user_id, user_id_type}
- list_departments: params={}
- general_query: params={query}

规则：
1. 步骤必须按依赖顺序排列
2. 如果需要发送消息通知用户，使用 reply_message
3. 仅返回 JSON 数组，不要多余文字
4. 如果信息不足，返回 {"_insufficient": true, "missing": ["字段1"]}
"""


async def generate_plan(intent: str, goal_fields: dict, context_hint: str = "") -> list[dict]:
    """Generate an executable plan from a goal.

    Returns a list of steps: [{"seq": N, "action": str, "params": dict, "description": str}]
    """
    prompt = f"意图: {intent}\n字段: {goal_fields}"
    if context_hint:
        prompt = f"{context_hint}\n\n{prompt}"
    try:
        result = await call_llm_json([
            {"role": "system", "content": _PLAN_SYSTEM},
            {"role": "user", "content": prompt},
        ], temperature=0.0)

        if isinstance(result, dict) and result.get("_insufficient"):
            return []

        if isinstance(result, list):
            return result

        return []
    except Exception as e:
        logger.warning("Plan generation failed: %s", e)
        return []


def review_plan_safety(steps: list[dict], open_id: str = "") -> list[dict]:
    """Add safety classification to each step.

    Returns steps with added "safety" field.
    """
    reviewed = []
    for step in steps:
        action = step.get("action", "")
        params = step.get("params", {})
        safety = classify_safety(action, params, open_id)
        reviewed.append({**step, "safety": safety})
    return reviewed
