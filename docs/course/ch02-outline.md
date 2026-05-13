# Ch2: 创建知识空间与文档骨架

本章用 `WikiService` 在飞书知识库中创建课程大纲的完整树形结构。

## 2.1 创建知识空间

在飞书客户端中：

1. 打开「知识库」→ 点击右上角「+」→ 选择「创建知识空间」
2. 命名为「具身智能导论」，选择「文档」类型
3. 记录 **space_id** — 打开知识空间，URL 中 `/wiki/space/` 后面的数字

```
https://your-domain.feishu.cn/wiki/space/7594752784659073978
                                       ^^^^^^^^^^^^^^^^^^^^
                                       这就是 space_id
```

### 用 CLI 快速确认

```bash
feishu-kit spaces
```

找到你的知识空间并记录 space_id：

```bash
export WIKU_SPACE_ID="7594752784659073978"
```

## 2.2 理解 WikiService

`WikiService` 是 feishu-kit 提供的飞书知识库封装，核心方法：

| 方法 | API | 用途 |
|------|-----|------|
| `list_spaces()` | `GET /wiki/v2/spaces` | 列出知识空间 |
| `create_node()` | `POST /wiki/v2/spaces/{id}/nodes` | 创建文档节点 |
| `list_all_nodes()` | 分页遍历 | 获取空间下所有节点 |
| `get_node()` | `GET /wiki/v2/nodes/{token}` | 获取节点详情 |
| `rename_node()` | `POST /wiki/v2/spaces/{id}/nodes/{token}/rename` | 重命名 |
| `create_doc_block()` | `POST /wiki/v2/blocks/{id}/children` | 写入内容块 |
| `search_nodes()` | `POST /wiki/v2/spaces/{id}/nodes/search` | 搜索节点 |

使用模式：所有 Service 都通过构造函数注入 `FeishuClient`：

```python
from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

async with FeishuClient(app_id="...", app_secret="...") as client:
    wiki = WikiService(client)  # 注入 client
    spaces = await wiki.list_spaces()
```

!!! info "依赖注入设计"
    feishu-kit 的所有 Service 都通过构造函数接收 `FeishuClient`，而不是自己创建连接。这意味着你可以轻松替换为 mock 进行测试，或者用 `ClientPool` 同时管理多个 bot。

## 2.3 用脚本批量创建文档骨架

创建 `scripts/create_outline.py`：

```python
"""创建课程文档骨架 — 使用 WikiService 批量创建章节和小节。"""
import asyncio
import os

from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

SPACE_ID = os.environ["WIKU_SPACE_ID"]

# 课程大纲 — 标题 + 子节列表
OUTLINE = {
    "绪论": [
        "1.1 具身智能的概念与内涵",
        "1.2 发展背景与研究意义",
        "1.3 与机器人、人工智能的关系",
        "1.4 具身智能操作系统",
        "1.5 学习目标与学习方法",
        "1.6 教材整体结构说明",
    ],
    "第二章 感知基础": [
        "2.1 视觉感知",
        "2.2 深度相机原理",
        "2.3 激光雷达与SLAM",
    ],
    "第三章 运动与控制": [
        "3.1 运动学基础",
        "3.2 路径规划",
        "3.3 力控制",
    ],
}


async def main():
    async with FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    ) as client:
        wiki = WikiService(client)

        for chapter_title, sections in OUTLINE.items():
            # 创建章节点（顶层）
            print(f"创建章节: {chapter_title}")
            result = await wiki.create_node(
                SPACE_ID, obj_type="docx", title=chapter_title
            )
            parent_token = result["data"]["node"]["node_token"]
            print(f"  node_token: {parent_token}")

            # 在章节下创建子节点
            for section_title in sections:
                print(f"  创建小节: {section_title}")
                await wiki.create_node(
                    SPACE_ID,
                    obj_type="docx",
                    title=section_title,
                    parent_node_token=parent_token,
                )
            print()

        print("✓ 文档骨架创建完成!")


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
python scripts/create_outline.py
```

预期输出：

```
创建章节: 绪论
  node_token: FjrFwzqwbiRixckwuzncfL8TnBg
  创建小节: 1.1 具身智能的概念与内涵
  创建小节: 1.2 发展背景与研究意义
  ...
创建章节: 第二章 感知基础
  ...
✓ 文档骨架创建完成!
```

## 2.4 验证骨架结构

用 CLI 查看节点树：

```bash
feishu-kit nodes $WIKU_SPACE_ID
```

你会看到类似这样的树形输出：

```
7594752784659073978
├── 绪论 (docx)
│   ├── 1.1 具身智能的概念与内涵 (docx)
│   ├── 1.2 发展背景与研究意义 (docx)
│   └── ...
├── 第二章 感知基础 (docx)
│   └── ...
```

> 现在打开飞书知识库，你应该能看到完整的文档树结构。每个节点目前是空文档，下一章我们开始填充内容。

### 记录节点 Token

后续填充内容时需要每个小节的 `obj_token`。可以通过 API 获取：

```python
nodes = await wiki.list_all_nodes(SPACE_ID)
for node in nodes:
    print(f"{node['title']}: obj={node['obj_token']}, node={node['node_token']}")
```

!!! tip "obj_token vs node_token"
    - **obj_token** — 文档对象本身的 ID，用于读写内容
    - **node_token** — 文档在知识库树中的位置 ID，用于移动/重命名
    - 两者不同，不要混淆！

---

上一章：[Ch1: 环境准备](ch01-setup.md) | 下一章：[Ch3: AI 辅助填充内容](ch03-fill-content.md)
