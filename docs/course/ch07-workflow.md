# Ch7: 完整工作流与 FAQ

## 全流程回顾

```
1. 环境准备
   ├─ 注册飞书应用，获取凭证
   ├─ pip install feishu-kit
   └─ 配置环境变量

2. 创建骨架          ← scripts/create_outline.py
   ├─ 创建知识空间（手动）
   ├─ 创建章节节点
   └─ 创建小节节点

3. AI 填充内容        ← Claude 生成 + scripts/fill_*.py
   ├─ 为每节生成内容块
   ├─ 写入飞书文档
   └─ 检查并修正

4. 内容审查           ← Claude review + scripts/enrich_*.py
   ├─ 去除AI味道
   ├─ 补充学术引用
   └─ 添加产业数据

5. PPT 课件           ← scripts/make_ppts.py
   ├─ python-pptx 生成
   ├─ 上传到云盘
   └─ move_docs_to_wiki 移入知识库

6. 持续维护
   ├─ 搜索节点 → wiki.search_nodes()
   ├─ 读取内容 → wiki.get_doc_raw_content()
   └─ 增量更新 → wiki.create_doc_block()
```

## FAQ

### API 返回 "forbidden"

检查飞书应用的权限范围是否已开通并发布。部分 API 需要管理员审批。

### 上传 PPT 后在知识库看不到文件节点

确保使用 `move_docs_to_wiki` 而非 `create_node`。`create_node` 不支持 file 类型。

### 文档块写入返回 "invalid param"

检查是否有空的 text_run（`elements: []`），飞书 API 不接受空元素列表。用空格代替：`text_run(" ")`。

### 如何处理批量操作中的错误

每个小节单独 try/except，记录失败的 obj_token，最后统一重试：

```python
failed = []
for obj_token, blocks in all_content.items():
    try:
        await wiki.create_doc_block(obj_token, obj_token, blocks)
    except Exception as e:
        failed.append((obj_token, str(e)))

for obj_token, error in failed:
    print(f"RETRY: {obj_token} — {error}")
```

### 如何搜索已有节点

```python
results = await wiki.search_nodes(space_id, keyword="具身智能")
for item in results.get("data", {}).get("items", []):
    print(item["title"], item["node_token"])
```

## 下一步

- 将工作流封装成 CLI 工具（`feishu-kit push` 已支持 Markdown 推送）
- 添加自动化测试
- 探索飞书多维表格作为课程进度管理
- 集成 LLM API 实现全自动内容生成

---

上一章：[Ch6: 内容扩充](ch06-enrich.md) | [返回目录](index.md)
