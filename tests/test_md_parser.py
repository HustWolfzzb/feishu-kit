"""Tests for Markdown to Feishu block parser."""

from feishu_kit.modules.md2feishu.parser import parse_md_to_blocks


def test_heading():
    blocks = parse_md_to_blocks("# Hello World")
    # Should produce at least one heading block (type 3 = heading1)
    assert len(blocks) > 0
    heading = blocks[0]
    assert heading["block_type"] == 3  # heading1


def test_paragraph():
    blocks = parse_md_to_blocks("This is a paragraph.")
    assert len(blocks) > 0
    assert blocks[0]["block_type"] == 2  # text


def test_bullet_list():
    md = "- Item 1\n- Item 2\n- Item 3"
    blocks = parse_md_to_blocks(md)
    bullets = [b for b in blocks if b["block_type"] == 12]
    assert len(bullets) == 3


def test_ordered_list():
    md = "1. First\n2. Second\n3. Third"
    blocks = parse_md_to_blocks(md)
    ordered = [b for b in blocks if b["block_type"] == 13]
    assert len(ordered) == 3


def test_code_block():
    md = "```python\nprint('hello')\n```"
    blocks = parse_md_to_blocks(md)
    code_blocks = [b for b in blocks if b["block_type"] == 14]
    assert len(code_blocks) == 1


def test_bold_text():
    blocks = parse_md_to_blocks("This has **bold** text.")
    assert len(blocks) > 0


def test_empty_input():
    blocks = parse_md_to_blocks("")
    # Should handle gracefully (empty list or minimal output)
    assert isinstance(blocks, list)
