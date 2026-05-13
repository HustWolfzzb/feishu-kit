# Ch7: 完整工作流与 FAQ

上一章：[Ch6: 学术引用](ch06-enrich.md) | [返回目录](index.md)

---

## 本章目标

完成本章后，你将：

- 对整个工作流有清晰的全局认知
- 知道每个步骤用了 feishu-kit 的哪个模块和方法
- 能够独立排查和解决常见问题
- 了解后续可以继续探索的方向

---

## 7.1 全流程回顾

下面是我们从 Ch1 到 Ch6 完成的所有工作，以及每一步对应的 feishu-kit 方法：

```
第 1 步：环境准备（Ch1）
  │  注册飞书应用 → 获取 App ID 和 App Secret
  │  安装 feishu-kit → pip install feishu-kit
  │  验证连接 → feishu-kit spaces
  │
第 2 步：创建文档骨架（Ch2）
  │  创建知识空间 → 在飞书客户端手动创建
  │  创建章节节点 → WikiService.create_node()
  │  创建小节节点 → WikiService.create_node(parent_node_token=...)
  │
第 3 步：填充内容（Ch3）
  │  构建内容块 → heading2() / text() / bullet() 等工具函数
  │  写入飞书文档 → WikiService.create_doc_block()
  │  或用 Markdown → Md2FeishuService.push_markdown()
  │  或用 CLI → feishu-kit push file.md space_id
  │
第 4 步：内容审查（Ch4）
  │  查看内容 → feishu-kit inspect token
  │  AI 审查 → Claude 辅助去 AI 味、核实引用
  │  追加修正 → WikiService.create_doc_block(index=-1)
  │
第 5 步：PPT 课件（Ch5）
  │  生成 PPT → python-pptx 库
  │  上传云盘 → DriveService.upload_file()
  │  移入知识库 → WikiService.move_docs_to_wiki(obj_type="file")
  │
第 6 步：学术引用（Ch6）
  │  补充引用 → 构建参考文献块并追加
  │  添加数据 → 构建表格块
  │  快速推送 → Md2FeishuService 或 feishu-kit push
```

---

## 7.2 你现在已经会了

通过这个教程，你已经掌握了以下技能：

| 技能 | 具体能力 |
|------|---------|
| 飞书 API 调用 | 使用 FeishuClient 连接飞书、自动管理令牌 |
| 知识库操作 | 创建空间、创建节点、遍历树形结构 |
| 文档写入 | 构建各种类型的块（标题、段落、列表、表格） |
| Markdown 转换 | 用 Md2FeishuService 一键推送 Markdown |
| 文件上传 | 用 DriveService 上传 PPT 等文件到云盘 |
| AI 辅助编程 | 用 Claude 生成内容块、审查质量 |
| CLI 工具 | 用 feishu-kit 命令行快速查看和操作 |
| 错误处理 | 使用 feishu-kit 的异常体系排查问题 |

---

## 7.3 FAQ

### Q: 运行脚本时报 `AuthenticationError`

**原因**：App ID 或 App Secret 不正确，或者环境变量没有设置。

**解决**：
```bash
# 检查环境变量是否已设置
echo $FEISHU_APP_ID
echo $FEISHU_APP_SECRET

# 如果为空，重新加载
source .env
```

### Q: API 返回 `code: 99991668` (forbidden)

**原因**：飞书应用的权限未开通或未发布。

**解决**：
1. 回到 Ch1 的 1.2 节，确认已开通 `wiki:wiki` 和 `drive:drive` 权限
2. 确认已创建版本并发布（可能需要等 1-2 分钟生效）

### Q: 上传 PPT 后在知识库中看不到

**原因**：使用了错误的 `obj_type` 或没有使用 `move_docs_to_wiki`。

**解决**：
```python
# ❌ 错误写法
await wiki.move_docs_to_wiki(..., obj_type="docx")

# ✅ 正确写法
await wiki.move_docs_to_wiki(..., obj_type="file")
```

### Q: `create_doc_block` 返回 "invalid param"

**原因**：有空的 text_run（`elements: []`）。

**解决**：
```python
# ❌ 错误：空内容
t("")

# ✅ 正确：用空格代替
t(" ")
```

### Q: 触发限流 (RateLimitError)

**原因**：短时间内发送了太多 API 请求。

**解决**：feishu-kit 内置了自动重试（最多 3 次，指数退避）。如果仍然失败，在循环中加一个 `await asyncio.sleep(1)` 每次请求间隔 1 秒。

### Q: 能否删除已创建的节点？

飞书 API 目前不支持删除知识库节点。需要在飞书客户端中手动右键删除。

### Q: 如何搜索已有节点？

```python
# 按关键词搜索
results = await wiki.search_nodes(space_id, keyword="具身智能")
for item in results.get("data", {}).get("items", []):
    print(item["title"], item["node_token"])
```

或用 CLI：
```bash
feishu-kit nodes $WIKU_SPACE_ID
```

---

## 7.4 进阶方向

### 方向一：多 Bot 协作

用 `ClientPool` 管理多个飞书应用，分别负责不同课程：

```python
from feishu_kit import ClientPool

pool = ClientPool()
pool.add("course-a", "cli_app1_id", "cli_app1_secret")
pool.add("course-b", "cli_app2_id", "cli_app2_secret")

# 用不同的 bot 操作不同的知识空间
wiki_a = WikiService(pool.get("course-a"))
wiki_b = WikiService(pool.get("course-b"))
```

### 方向二：搭建 FastAPI 管理后台

用 feishu-kit 的 `server` 层搭建一个 REST API，通过网页管理课程：

```bash
pip install "feishu-kit[server]"
```

参考 `examples/08-web-dashboard/` 中的完整示例。

### 方向三：全自动内容生成

集成 LLM API（如 Claude API），实现从大纲到完整内容的自动化：

```
课程大纲 → LLM 生成 Markdown → Md2FeishuService 推送 → 自动审查 → 自动生成 PPT
```

参考 `examples/07-course-builder/course_builder.py` 中的自动化流程。

---

## 下一步做什么

1. **找一个你感兴趣的课程主题**，把教程中的"具身智能导论"替换成你自己的主题，重新跑一遍整个流程
2. **阅读 feishu-kit 的其他教程**：[Wiki 教程](../tutorial-wiki.md)、[Drive 教程](../tutorial-drive.md)、[Markdown 转换教程](../tutorial-md2feishu.md)
3. **给 feishu-kit 贡献代码**：如果在用的过程中发现了 bug 或有改进建议，欢迎到 [GitHub](https://github.com/HustWolfzzb/feishu-kit) 提 Issue 或 PR

---

上一章：[Ch6: 学术引用](ch06-enrich.md) | [返回目录](index.md)
