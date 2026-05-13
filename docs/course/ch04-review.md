# Ch4: 内容审查与修正

内容写入后，需要检查和优化。这一步决定了课程的专业度。

## 4.1 查看当前内容

```python
async def review_content(wiki, obj_token):
    """读取文档全文并显示。"""
    raw = await wiki.get_doc_raw_content(obj_token)
    content = raw.get("data", {}).get("content", "")
    print(content)
    print(f"\n--- {len(content)} chars ---")
```

或使用 CLI：

```bash
feishu-kit inspect B16Bdn0vqopi8XxQaERcZPdenHd
```

## 4.2 用 Claude 进行内容审查

```
请检查我刚才填充到 1.1 小节的内容，要求：
1. 去除AI味道（避免大量重复废话、过度热情的语气）
2. 检查每小节前后逻辑，避免前后不一致
3. 确保内容连贯性
4. 引用的论文和年份要准确

文档 obj_token: B16Bdn0vqopi8XxQaERcZPdenHd
```

## 4.3 常见审查要点

| 问题 | 检查方法 |
|------|----------|
| AI 生成痕迹 | 搜索「值得注意的是」「总而言之」「毫无疑问」等套话 |
| 逻辑矛盾 | 检查前后段落是否有相互矛盾的论断 |
| 引用准确性 | 核对论文标题、年份、期刊名 |
| 格式一致性 | 确保标题层级、列表样式、引用格式统一 |
| 空块问题 | 检查是否有 `elements: []` 的空块 |

## 4.4 增量更新内容

```python
# 追加内容到文档末尾
await wiki.create_doc_block(obj_token, obj_token, new_blocks, index=-1)
```

> 飞书 API 目前不支持删除或修改已有块，只能追加。如需大幅修改，建议重建文档。

---

上一章：[Ch3: 填充内容](ch03-fill-content.md) | 下一章：[Ch5: 制作 PPT 课件](ch05-ppt.md)
