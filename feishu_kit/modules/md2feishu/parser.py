"""Markdown → 飞书 DocX Block 转换器

使用 mistune 解析 MD AST，递归映射为飞书文档 block 格式。
"""

from __future__ import annotations

from typing import Callable, Awaitable

import mistune

# ── 飞书 BlockType 常量 ──────────────────────────────────────────
BLOCK_TEXT = 2
BLOCK_HEADING_BASE = 3  # heading1=3, heading2=4, ...
BLOCK_BULLET = 12
BLOCK_ORDERED = 13
BLOCK_CODE = 14
BLOCK_QUOTE = 15
BLOCK_TODO = 17
BLOCK_DIVIDER = 22
BLOCK_IMAGE = 27
BLOCK_TABLE = 31
BLOCK_TABLE_CELL = 32

# ── 代码语言映射 ─────────────────────────────────────────────────
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
    if not lang:
        return 0
    return LANG_MAP.get(lang.strip().lower(), 0)


def _text_element(text: str, *, bold: bool = False, italic: bool = False,
                  strikethrough: bool = False, inline_code: bool = False,
                  link: str | None = None) -> dict:
    """构建飞书 TextElement (text_run)。"""
    style: dict = {}
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

    elem: dict = {"text_run": {"content": text}}
    if style:
        elem["text_run"]["text_element_style"] = style
    return elem


def _inline_elements(children: list[dict]) -> list[dict]:
    """递归将 mistune inline tokens 转为飞书 TextElement 列表。"""
    elements: list[dict] = []
    for child in children:
        ctype = child["type"]
        if ctype == "text":
            elements.append(_text_element(child["raw"]))
        elif ctype == "softbreak":
            elements.append(_text_element("\n"))
        elif ctype == "strong":
            for el in _inline_elements(child.get("children", [])):
                # 标记 bold
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
            # fallback: 取 raw 文本
            raw = child.get("raw", "")
            if raw:
                elements.append(_text_element(raw))
    return elements


def _make_block(block_type: int, elements: list[dict] | None = None, **extra) -> dict:
    """构建飞书 block dict。"""
    block: dict = {"block_type": block_type}
    if elements is not None:
        # block_type 对应的字段名
        type_names = {
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


def _try_convert_standalone_image(
    token: dict, image_tokens: dict[str, str] | None
) -> dict | None:
    """检查段落是否只包含一个图片，如果是且有 file_token 则返回图片 block。"""
    if not image_tokens:
        return None
    children = token.get("children", [])
    if len(children) != 1 or children[0].get("type") != "image":
        return None

    img = children[0]
    url = img.get("attrs", {}).get("url", "")

    # 查找匹配的 file_token
    file_token = image_tokens.get(url)
    if not file_token:
        # 也尝试用文件名匹配
        import os
        basename = os.path.basename(url)
        for path, token_val in image_tokens.items():
            if os.path.basename(path) == basename:
                file_token = token_val
                break
    if not file_token:
        return None

    return {"block_type": BLOCK_IMAGE, "image": {"token": file_token}}


def _convert_paragraph(token: dict) -> dict:
    elements = _inline_elements(token.get("children", []))
    return _make_block(BLOCK_TEXT, elements)


def _convert_heading(token: dict) -> dict:
    level = token.get("attrs", {}).get("level", 1)
    level = min(level, 6)  # 飞书最多 heading6
    elements = _inline_elements(token.get("children", []))
    return _make_block(BLOCK_HEADING_BASE + level - 1, elements)


def _convert_block_code(token: dict) -> dict:
    lang = token.get("attrs", {}).get("info", "")
    code = token.get("raw", "")
    # 飞书 code block 结构
    return {
        "block_type": BLOCK_CODE,
        "code": {
            "style": {"language": _code_lang(lang)},
            "elements": [_text_element(code)],
        },
    }


def _convert_list(token: dict) -> list[dict]:
    ordered = token.get("attrs", {}).get("ordered", False)
    block_type = BLOCK_ORDERED if ordered else BLOCK_BULLET
    blocks: list[dict] = []
    for item in token.get("children", []):
        item_type = item.get("type", "list_item")
        # task_list_item 由 task_lists 插件产生
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
            # 普通 list_item → block_text children
            sub_children = item.get("children", [])
            elements: list[dict] = []
            for sc in sub_children:
                if sc["type"] == "block_text":
                    elements.extend(_inline_elements(sc.get("children", [])))
                elif sc["type"] == "paragraph":
                    elements.extend(_inline_elements(sc.get("children", [])))
            blocks.append(_make_block(block_type, elements))
    return blocks


def _convert_block_quote(token: dict) -> dict:
    # 引用块内的子元素递归转换，取第一个段落的内容
    elements: list[dict] = []
    for child in token.get("children", []):
        if child["type"] == "paragraph":
            elements.extend(_inline_elements(child.get("children", [])))
        elif child["type"] == "block_text":
            elements.extend(_inline_elements(child.get("children", [])))
    return _make_block(BLOCK_QUOTE, elements)


def _convert_table(token: dict) -> list[dict]:
    """将 mistune table token 转为飞书 table block + cell blocks。

    飞书 table block 结构：
    - block_type: 31
    - table.property: { row_size, column_size }
    - 子 block: table_cell (32)，每个 cell 含 text block 子节点

    返回 [table_block]（children 字段含 cell blocks）
    """
    # 收集所有行数据
    row_data: list[list[dict]] = []  # 每行 = list of elements
    col_count = 0

    for section in token.get("children", []):
        if section["type"] == "table_head":
            row_elems: list[dict] = []
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

    # 构建 table block
    table_block = {
        "block_type": BLOCK_TABLE,
        "table": {
            "property": {
                "row_size": len(row_data),
                "column_size": col_count,
            },
        },
    }

    # 构建 cell blocks — 每个 cell 含一个 text block 作为子节点
    cells: list[dict] = []
    for row_elems in row_data:
        for cell_elements in row_elems:
            cell: dict = {
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


def parse_md_to_blocks(
    md_text: str,
    *,
    image_tokens: dict[str, str] | None = None,
) -> list[dict]:
    """将 Markdown 文本解析为飞书 DocX block 列表。

    Args:
        md_text: Markdown 文本
        image_tokens: 可选的本地路径→file_token 映射。
            当图片路径在此映射中时，创建飞书图片 block (block_type=27)。
    """
    md = mistune.create_markdown(
        renderer=None,
        plugins=["table", "task_lists", "strikethrough"],
    )
    tokens, _ = md.parse(md_text)

    blocks: list[dict] = []
    for token in tokens:
        ttype = token["type"]

        if ttype == "heading":
            blocks.append(_convert_heading(token))
        elif ttype == "paragraph":
            # 检查段落是否只包含一个 image（独占一行的图片）
            img_block = _try_convert_standalone_image(token, image_tokens)
            if img_block is not None:
                blocks.append(img_block)
            else:
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
        # 忽略 block_html 等不支持的类型

    return blocks
