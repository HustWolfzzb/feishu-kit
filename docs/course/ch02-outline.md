# Ch2: 创建知识空间与文档骨架

## 2.1 创建知识空间

在飞书客户端中：

1. 打开「知识库」→ 点击「+」→ 创建知识空间
2. 命名为「具身智能导论」
3. 记录下知识空间的 **space_id**（URL 中 `/wiki/space/` 后面的那串数字）

> 或通过 API：调用 `GET /wiki/v2/spaces` 获取 space_id。

```bash
export WIKU_SPACE_ID="7594752784659073978"
```

## 2.2 用脚本批量创建文档骨架

创建 `scripts/create_outline.py`：

```python
"""创建课程文档骨架 — 在知识空间中批量创建章节和小节。"""
import asyncio
import os

from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

SPACE_ID = os.environ.get("WIKU_SPACE_ID", "your_space_id")

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
            # 创建章节点
            print(f"创建章节: {chapter_title}")
            result = await wiki.create_node(
                SPACE_ID, obj_type="docx", title=chapter_title
            )
            parent_token = result["data"]["node"]["node_token"]
            print(f"  node_token: {parent_token}")

            # 创建子节点
            for section_title in sections:
                print(f"  创建小节: {section_title}")
                await wiki.create_node(
                    SPACE_ID,
                    obj_type="docx",
                    title=section_title,
                    parent_node_token=parent_token,
                )
            print()

        print("文档骨架创建完成!")


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
文档骨架创建完成!
```

> 现在打开飞书知识库，你应该能看到完整的文档树结构。

---

上一章：[Ch1: 环境准备](ch01-setup.md) | 下一章：[Ch3: AI 辅助填充内容](ch03-fill-content.md)
