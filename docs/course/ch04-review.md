# Ch4: 内容审查与修正

内容写入飞书后，需要检查质量。这一步决定了课程的专业度，也是最容易忽略的环节。

## 4.1 查看当前内容

### 用 CLI 查看（推荐）

```bash
feishu-kit inspect B16Bdn0vqopi8XxQaERcZPdenHd
```

输出是格式化的 JSON，包含文档所有块的完整结构。

### 用 Python 查看

```python
from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

async with FeishuClient(app_id="...", app_secret="...") as client:
    wiki = WikiService(client)
    raw = await wiki.get_doc_raw_content("B16Bdn0vqopi8XxQaERcZPdenHd")
    content = raw.get("data", {}).get("content", "")
    print(content)
    print(f"\n--- {len(content)} chars ---")
```

### 查看块结构

```python
# 获取文档的块树结构
blocks = await wiki.get_doc_blocks("B16Bdn0vqopi8XxQaERcZPdenHd")
for block in blocks.get("data", {}).get("items", []):
    btype = block.get("block_type")
    print(f"  block_type={btype}")
```

## 4.2 用 Claude 进行内容审查

给 Claude 的审查提示词：

```
请检查我刚才填充到 1.1 小节的内容，要求：
1. 去除AI味道（避免大量重复废话、过度热情的语气）
2. 检查每小节前后逻辑，避免前后不一致
3. 确保内容连贯性
4. 引用的论文和年份要准确

文档 obj_token: B16Bdn0vqopi8XxQaERcZPdenHd
```

## 4.3 常见审查要点

| 问题 | 检查方法 | 修复方式 |
|------|----------|----------|
| AI 生成痕迹 | 搜索「值得注意的是」「总而言之」「毫无疑问」等套话 | 替换为更自然的表述 |
| 逻辑矛盾 | 检查前后段落是否有相互矛盾的论断 | 重写矛盾段落 |
| 引用不准确 | 核对论文标题、年份、期刊名 | 用正确的引用替换 |
| 格式不一致 | 确保标题层级、列表样式、引用格式统一 | 追加修正块 |
| 空块问题 | 检查 `elements: []` 的空块 | 追加含内容的块覆盖 |
| 堆砌感 | 段落间缺少过渡，像拼凑的 | 增加过渡段 |

## 4.4 增量更新内容

飞书 DocX API 的限制：**不能删除或修改已有块，只能追加**。

```python
# 追加新内容到文档末尾
new_blocks = [
    heading2("补充说明"),
    text("经过审查，补充以下内容..."),
]
await wiki.create_doc_block(obj_token, obj_token, new_blocks, index=-1)
```

!!! warning "如需大幅修改"
    如果一个文档的问题太多，建议删除重建：
    1. 创建新文档：`await wiki.create_node(space_id, title="1.1 xxx")`
    2. 写入修正后的内容
    3. 删除旧文档（需在飞书客户端手动操作，API 不支持删除）

## 4.5 异常处理

feishu-kit 提供了自定义异常体系，帮你优雅地处理 API 错误：

```python
from feishu_kit.core.exceptions import APIError, AuthenticationError, RateLimitError

try:
    await wiki.create_doc_block(obj_token, obj_token, blocks)
except AuthenticationError:
    print("凭证无效，请检查 App ID/Secret")
except RateLimitError as e:
    print(f"触发限流，{e.retry_after}秒后重试")
except APIError as e:
    print(f"API 错误 code={e.code}: {e.msg}")
```

feishu-client 内置了自动重试机制（429 限流和 5xx 服务端错误），大多数情况下你不需要手动处理重试。

---

上一章：[Ch3: 填充内容](ch03-fill-content.md) | 下一章：[Ch5: 制作 PPT 课件](ch05-ppt.md)
