"""Clarifier — detect missing fields and generate minimal clarification questions."""

import logging

from feishu_kit.modules.butler.llm import call_llm_json

logger = logging.getLogger(__name__)

# Required fields per intent
_REQUIRED_FIELDS: dict[str, list[str]] = {
    "create_task": ["title"],
    "create_reminder": ["message", "fire_at"],
    "create_event": ["summary", "start_time"],
    "create_note": ["title"],
    "query_info": ["query"],
}

# Field -> human-readable name + question template
_FIELD_INFO: dict[str, dict] = {
    "title": {"name": "标题", "question": "请问任务标题是什么？"},
    "summary": {"name": "日程标题", "question": "请问日程标题是什么？"},
    "message": {"name": "提醒内容", "question": "请问要提醒什么内容？"},
    "fire_at": {"name": "提醒时间", "question": "请问什么时候提醒你？（例如：明天下午3点、3小时后）"},
    "start_time": {"name": "开始时间", "question": "请问什么时候开始？（例如：明天下午3点、2026-04-22 10:00）"},
    "end_time": {"name": "结束时间", "question": "请问什么时候结束？"},
    "description": {"name": "描述", "question": "请问有什么补充描述吗？"},
    "location": {"name": "地点", "question": "请问在哪里？"},
    "assignee": {"name": "负责人", "question": "请问谁来负责这个任务？"},
    "content": {"name": "内容", "question": "请问笔记的内容是什么？"},
    "query": {"name": "查询内容", "question": "请问你想查询什么？"},
    "space_id": {"name": "知识库", "question": "请问要保存到哪个知识库？"},
}


def check_missing_fields(intent: str, fields: dict) -> list[str]:
    """Check which required fields are missing or empty.

    Returns list of missing field names.
    """
    required = _REQUIRED_FIELDS.get(intent, [])
    missing = []
    for field in required:
        val = fields.get(field, "")
        if not val:
            missing.append(field)
    return missing


def generate_clarification_question(missing_fields: list[str]) -> str:
    """Generate a minimal clarification question for missing fields."""
    if not missing_fields:
        return ""

    if len(missing_fields) == 1:
        field = missing_fields[0]
        info = _FIELD_INFO.get(field, {})
        return info.get("question", f"请提供 {field} 的信息。")

    # Multiple missing fields — ask about the most important one first
    questions = []
    for field in missing_fields[:2]:  # Ask max 2 at a time
        info = _FIELD_INFO.get(field, {})
        questions.append(info.get("question", f"请提供 {field} 的信息。"))

    return "还需要一些信息：\n" + "\n".join(f"· {q}" for q in questions)


async def clarify_with_llm(intent: str, user_text: str, missing_fields: list[str]) -> str:
    """Use LLM to generate a natural clarification question.

    Falls back to template-based question if LLM fails.
    """
    if not missing_fields:
        return ""

    # Try template first for single field
    if len(missing_fields) == 1:
        return generate_clarification_question(missing_fields)

    try:
        field_names = ", ".join(
            _FIELD_INFO.get(f, {}).get("name", f) for f in missing_fields
        )
        result = await call_llm_json([{
            "role": "user",
            "content": (
                f"用户说: {user_text}\n"
                f"意图: {intent}\n"
                f"缺少字段: {field_names}\n"
                f"请生成一句简短的追问，用自然语言询问缺少的信息。"
                f"仅返回 JSON: {{\"question\": \"...\"}}"
            ),
        }], temperature=0.3)
        return result.get("question", generate_clarification_question(missing_fields))
    except Exception as e:
        logger.warning("LLM clarification failed: %s", e)
        return generate_clarification_question(missing_fields)
