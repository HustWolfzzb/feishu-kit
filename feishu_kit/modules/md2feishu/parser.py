"""Markdown to Feishu DocX Block converter.

Uses mistune to parse Markdown into an AST, then recursively maps tokens
to the Feishu document block format.
"""

from __future__ import annotations

from typing import Any

import mistune

# -- Feishu BlockType constants ----------------------------------------
BLOCK_TEXT = 2
BLOCK_HEADING_BASE = 3  # heading1=3, heading2=4, ...
BLOCK_BULLET = 12
BLOCK_ORDERED = 13
BLOCK_CODE = 14
BLOCK_QUOTE = 15
BLOCK_TODO = 17
BLOCK_DIVIDER = 22
BLOCK_TABLE = 31
BLOCK_TABLE_CELL = 32

# -- Code language mapping ---------------------------------------------
LANG_MAP: dict[str, int] = {
    "python": 49, "py": 49,
    "javascript": 30, "js": 30,
    "typescript": 63, "ts": 63,
    "bash": 7, "shell": 7, "sh": 7, "zsh": 7,
    "c": 10,
    "cpp": 9, "c++": 9, "cc": 9,
    "java": 29,
    "go": 21,
    "rust": 51, "rs": 51,
    "ruby": 50, "rb": 50,
    "sql": 55,
    "html": 25,
    "css": 14,
    "json": 31,
    "yaml": 67, "yml": 67,
    "xml": 66,
    "markdown": 36, "md": 36,
    "latex": 44, "tex": 44,
    "r": 48,
    "matlab": 37,
    "perl": 45, "pl": 45,
    "php": 46,
    "swift": 58,
    "kotlin": 32, "kt": 32,
    "scala": 53,
    "lua": 34,
    "dart": 16,
    "dockerfile": 17,
    "makefile": 35,
    "diff": 18,
    "plaintext": 0, "text": 0, "": 0,
}


def _code_lang(lang: str | None) -> int:
    """Map a language name string to the Feishu code block language ID.

    Args:
        lang: Language identifier (e.g. ``"python"``).

    Returns:
        Integer language code, or ``0`` for plain text / unknown.
    """
    if not lang:
        return 0
    return LANG_MAP.get(lang.strip().lower(), 0)


def _text_element(
    text: str,
    *,
    bold: bool = False,
    italic: bool = False,
    strikethrough: bool = False,
    inline_code: bool = False,
    link: str | None = None,
) -> dict[str, Any]:
    """Build a Feishu TextElement (``text_run``).

    Args:
        text: The text content.
        bold: Whether to apply bold style.
        italic: Whether to apply italic style.
        strikethrough: Whether to apply strikethrough style.
        inline_code: Whether to render as inline code.
        link: Optional URL for a hyperlink.

    Returns:
        A dict representing a Feishu ``text_run`` element.
    """
    style: dict[str, Any] = {}
    if bold:
        style["bold"] = True
    if italic:
        style["italic"] = True
    if strikethrough:
        style["strikethrough"] = True
    if inline_code:
        style["inline_code"] = True
    if link:
        style["link"] = {"url": link}

    elem: dict[str, Any] = {"text_run": {"content": text}}
    if style:
        elem["text_run"]["text_element_style"] = style
    return elem


def _inline_elements(children: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Recursively convert mistune inline tokens into Feishu TextElement list.

    Args:
        children: List of mistune inline token dicts.

    Returns:
        A flat list of Feishu TextElement dicts.
    """
    elements: list[dict[str, Any]] = []
    for child in children:
        ctype = child["type"]
        if ctype == "text":
            elements.append(_text_element(child["raw"]))
        elif ctype == "softbreak":
            elements.append(_text_element("\n"))
        elif ctype == "strong":
            for el in _inline_elements(child.get("children", [])):
                if "text_run" in el:
                    el["text_run"].setdefault("text_element_style", {})["bold"] = True
                elements.append(el)
        elif ctype == "emphasis":
            for el in _inline_elements(child.get("children", [])):
                if "text_run" in el:
                    el["text_run"].setdefault("text_element_style", {})["italic"] = True
                elements.append(el)
        elif ctype == "codespan":
            elements.append(_text_element(child["raw"], inline_code=True))
        elif ctype == "link":
            url = child.get("attrs", {}).get("url", "")
            sub = child.get("children", [])
            if sub:
                for el in _inline_elements(sub):
                    if "text_run" in el:
                        el["text_run"].setdefault("text_element_style", {})["link"] = {"url": url}
                    elements.append(el)
            else:
                elements.append(_text_element(url, link=url))
        elif ctype == "strikethrough":
            for el in _inline_elements(child.get("children", [])):
                if "text_run" in el:
                    el["text_run"].setdefault("text_element_style", {})["strikethrough"] = True
                elements.append(el)
        elif ctype == "image":
            alt = ""
            for sc in child.get("children", []):
                if sc["type"] == "text":
                    alt += sc["raw"]
            url = child.get("attrs", {}).get("url", "")
            elements.append(_text_element(f"[图片: {alt or url}]", link=url if url else None))
        elif ctype == "auto_link":
            url = child.get("raw", "").strip("<>")
            elements.append(_text_element(url, link=url))
        elif ctype == "linebreak":
            elements.append(_text_element("\n"))
        else:
            raw = child.get("raw", "")
            if raw:
                elements.append(_text_element(raw))
    return elements


def _make_block(
    block_type: int,
    elements: list[dict[str, Any]] | None = None,
    **extra: Any,
) -> dict[str, Any]:
    """Build a Feishu block dict.

    Args:
        block_type: Integer block type constant.
        elements: Optional list of TextElement dicts.
        **extra: Additional keys merged into the block dict.

    Returns:
        A dict representing a Feishu block.
    """
    block: dict[str, Any] = {"block_type": block_type}
    if elements is not None:
        type_names: dict[int, str] = {
            BLOCK_TEXT: "text",
            BLOCK_HEADING_BASE + 0: "heading1",
            BLOCK_HEADING_BASE + 1: "heading2",
            BLOCK_HEADING_BASE + 2: "heading3",
            BLOCK_HEADING_BASE + 3: "heading4",
            BLOCK_HEADING_BASE + 4: "heading5",
            BLOCK_HEADING_BASE + 5: "heading6",
            BLOCK_BULLET: "bullet",
            BLOCK_ORDERED: "ordered",
            BLOCK_TODO: "todo",
            BLOCK_QUOTE: "quote",
        }
        key = type_names.get(block_type, "text")
        block[key] = {"elements": elements}
    block.update(extra)
    return block


def _convert_paragraph(token: dict[str, Any]) -> dict[str, Any]:
    """Convert a paragraph token to a Feishu text block."""
    elements = _inline_elements(token.get("children", []))
    return _make_block(BLOCK_TEXT, elements)


def _convert_heading(token: dict[str, Any]) -> dict[str, Any]:
    """Convert a heading token to a Feishu heading block."""
    level = token.get("attrs", {}).get("level", 1)
    level = min(level, 6)  # Feishu supports up to heading6
    elements = _inline_elements(token.get("children", []))
    return _make_block(BLOCK_HEADING_BASE + level - 1, elements)


def _convert_block_code(token: dict[str, Any]) -> dict[str, Any]:
    """Convert a block_code token to a Feishu code block."""
    lang = token.get("attrs", {}).get("info", "")
    code = token.get("raw", "")
    return {
        "block_type": BLOCK_CODE,
        "code": {
            "style": {"language": _code_lang(lang)},
            "elements": [_text_element(code)],
        },
    }


def _convert_list(token: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a list token to Feishu bullet / ordered / todo blocks."""
    ordered = token.get("attrs", {}).get("ordered", False)
    block_type = BLOCK_ORDERED if ordered else BLOCK_BULLET
    blocks: list[dict[str, Any]] = []
    for item in token.get("children", []):
        item_type = item.get("type", "list_item")
        if item_type == "task_list_item":
            checked = item.get("attrs", {}).get("checked", False)
            elements = _inline_elements(
                item.get("children", [{}])[0].get("children", [])
                if item.get("children") else []
            )
            todo_block = _make_block(BLOCK_TODO, elements)
            todo_block["todo"] = {"elements": elements}
            if checked:
                todo_block["todo"]["style"] = {"done": True}
            blocks.append(todo_block)
        else:
            sub_children = item.get("children", [])
            elements: list[dict[str, Any]] = []
            for sc in sub_children:
                if sc["type"] == "block_text":
                    elements.extend(_inline_elements(sc.get("children", [])))
                elif sc["type"] == "paragraph":
                    elements.extend(_inline_elements(sc.get("children", [])))
            blocks.append(_make_block(block_type, elements))
    return blocks


def _convert_block_quote(token: dict[str, Any]) -> dict[str, Any]:
    """Convert a block_quote token to a Feishu quote block."""
    elements: list[dict[str, Any]] = []
    for child in token.get("children", []):
        if child["type"] == "paragraph":
            elements.extend(_inline_elements(child.get("children", [])))
        elif child["type"] == "block_text":
            elements.extend(_inline_elements(child.get("children", [])))
    return _make_block(BLOCK_QUOTE, elements)


def _convert_table(token: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert a table token to a Feishu table block with cell children.

    The Feishu table block structure:
    - ``block_type``: 31
    - ``table.property``: ``{row_size, column_size}``
    - Child blocks: ``table_cell`` (type 32), each containing text block children

    Returns:
        A list containing a single table block dict (with ``children``).
    """
    row_data: list[list[list[dict[str, Any]]]] = []
    col_count = 0

    for section in token.get("children", []):
        if section["type"] == "table_head":
            row_elems: list[list[dict[str, Any]]] = []
            for cell in section.get("children", []):
                if cell["type"] == "table_cell":
                    row_elems.append(_inline_elements(cell.get("children", [])))
            if row_elems:
                row_data.append(row_elems)
                col_count = max(col_count, len(row_elems))
        elif section["type"] == "table_body":
            for row in section.get("children", []):
                row_elems = []
                for cell in row.get("children", []):
                    if cell["type"] == "table_cell":
                        row_elems.append(_inline_elements(cell.get("children", [])))
                if row_elems:
                    row_data.append(row_elems)
                    col_count = max(col_count, len(row_elems))

    if not row_data or col_count == 0:
        return []

    table_block: dict[str, Any] = {
        "block_type": BLOCK_TABLE,
        "table": {
            "property": {
                "row_size": len(row_data),
                "column_size": col_count,
            },
        },
    }

    cells: list[dict[str, Any]] = []
    for row_elems in row_data:
        for cell_elements in row_elems:
            cell: dict[str, Any] = {
                "block_type": BLOCK_TABLE_CELL,
                "table_cell": {},
            }
            if cell_elements:
                cell["children"] = [{
                    "block_type": BLOCK_TEXT,
                    "text": {"elements": cell_elements},
                }]
            cells.append(cell)

    table_block["children"] = cells
    return [table_block]


def parse_md_to_blocks(md_text: str) -> list[dict[str, Any]]:
    """Parse Markdown text into a list of Feishu DocX block dicts.

    Args:
        md_text: Raw Markdown string.

    Returns:
        A list of dicts, each representing a Feishu document block.
    """
    md = mistune.create_markdown(
        renderer=None,
        plugins=["table", "task_lists", "strikethrough"],
    )
    tokens, _ = md.parse(md_text)

    blocks: list[dict[str, Any]] = []
    for token in tokens:
        ttype = token["type"]

        if ttype == "heading":
            blocks.append(_convert_heading(token))
        elif ttype == "paragraph":
            blocks.append(_convert_paragraph(token))
        elif ttype == "block_code":
            blocks.append(_convert_block_code(token))
        elif ttype == "list":
            blocks.extend(_convert_list(token))
        elif ttype == "block_quote":
            blocks.append(_convert_block_quote(token))
        elif ttype == "thematic_break":
            blocks.append({"block_type": BLOCK_DIVIDER, "divider": {}})
        elif ttype == "table":
            blocks.extend(_convert_table(token))
        elif ttype in ("blank_line",):
            continue

    return blocks
