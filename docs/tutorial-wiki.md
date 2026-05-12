# Wiki Tutorial — Knowledge Base Operations

This tutorial covers the `WikiService` module for managing Feishu knowledge bases (spaces, nodes, and documents).

## Setup

```python
import asyncio
from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

client = FeishuClient(app_id="...", app_secret="...")
wiki = WikiService(client)
```

## 1. List Knowledge Spaces

```python
result = await wiki.list_spaces(page_size=20)
for space in result.get("data", {}).get("items", []):
    print(f"{space['name']} — id={space['space_id']}")
```

## 2. List Nodes in a Space

```python
# Single page
result = await wiki.list_nodes("space_id", page_size=50)

# All nodes (auto-pagination)
all_nodes = await wiki.list_all_nodes("space_id")
print(f"Total nodes: {len(all_nodes)}")
```

## 3. Get Node Tree (Hierarchical)

```python
tree = await wiki.get_node_tree("space_id", max_depth=3)

def print_tree(nodes, indent=0):
    for node in nodes:
        print("  " * indent + f"📁 {node.get('title')}")
        children = node.get("children", [])
        if children:
            print_tree(children, indent + 1)

print_tree(tree)
```

## 4. Create a Document

```python
result = await wiki.create_node(
    space_id="space_id",
    obj_type="docx",
    title="My New Document",
    parent_node_token="parent_node_token",  # optional
)
node_token = result["data"]["node"]["node_token"]
obj_token = result["data"]["node"]["obj_token"]
```

## 5. Write Content to a Document

Feishu documents use a block-based model. Each block has a `block_type`:

| Type | Block | Description |
|------|-------|-------------|
| 1 | page | Document root |
| 2 | text | Paragraph |
| 3 | heading1 | Level 1 heading |
| 4 | heading2 | Level 2 heading |
| 5 | heading3 | Level 3 heading |
| 12 | bullet | Unordered list item |
| 13 | ordered | Ordered list item |
| 14 | code | Code block |

```python
def text_run(content, bold=False):
    style = {"bold": True} if bold else {}
    return {"text_run": {"content": content, "text_element_style": style}}

blocks = [
    {"block_type": 4, "heading2": {"elements": [text_run("Title", bold=True)], "style": {}}},
    {"block_type": 2, "text": {"elements": [text_run("Paragraph content here.")], "style": {}}},
    {"block_type": 12, "bullet": {"elements": [text_run("Bullet point")], "style": {}}},
]

await wiki.create_doc_block(obj_token, obj_token, blocks, index=-1)
```

## 6. Read Document Content

```python
# Plain text content
raw = await wiki.get_doc_raw_content(obj_token)
print(raw["data"]["content"])

# Structured blocks
blocks = await wiki.get_doc_blocks(obj_token, page_size=50)
for block in blocks.get("data", {}).get("items", []):
    print(f"Block type: {block.get('block_type')}")
```

## 7. Search Nodes

```python
matches = await wiki.search_nodes("space_id", keyword="机器人")
for m in matches:
    print(f"Found: {m['title']}")
```

## 8. Move and Rename Nodes

```python
# Rename
await wiki.rename_node("space_id", "node_token", "New Title")

# Move to a different parent
await wiki.move_node("space_id", "node_token", "new_parent_token")
```

## 9. Move Files from Drive to Wiki

```python
await wiki.move_docs_to_wiki(
    space_id="space_id",
    parent_wiki_token="parent_node_token",
    obj_token="drive_file_token",
    obj_type="file",
)
```

## 10. RAG Support

```python
# Get full text content of all documents in a space
docs = await wiki.get_space_full_content("space_id", max_nodes=50)
for doc in docs:
    print(f"{doc['title']}: {len(doc['content'])} chars")

# Get single node with full content
detail = await wiki.get_node_with_content("node_token")
print(detail["content"])
```

## Cleanup

Always close the client when done:

```python
await client.close()
```

## Next: [Drive Tutorial](tutorial-drive.md)
