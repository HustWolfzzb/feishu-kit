# Ch3: AI 辅助填充课程内容

这是本项目最关键的部分 — 用 AI Agent 为每个小节生成课程内容并写入飞书。

## 3.1 理解飞书文档的块模型

飞书文档不是纯文本，而是由「块」（Block）组成的树结构：

```python
# 常用块类型
BLOCK_TEXT = 2        # 普通文本
BLOCK_HEADING2 = 4   # 二级标题
BLOCK_HEADING3 = 5   # 三级标题
BLOCK_BULLET = 12    # 无序列表
BLOCK_ORDERED = 13   # 有序列表
BLOCK_CODE = 14      # 代码块

# 文本元素（每个块包含一个 elements 列表）
def text_run(content, bold=False, italic=False):
    style = {}
    if bold: style["bold"] = True
    if italic: style["italic"] = True
    return {"text_run": {"content": content, "text_element_style": style}}
```

## 3.2 块构建工具函数

这些工具函数会频繁用到，建议放在一个公共模块中：

```python
def t(content, bold=False, italic=False):
    style = {}
    if bold: style["bold"] = True
    if italic: style["italic"] = True
    return {"text_run": {"content": content, "text_element_style": style}}

def heading2(content):
    return {"block_type": 4, "heading2": {"elements": [t(content)], "style": {}}}

def heading3(content):
    return {"block_type": 5, "heading3": {"elements": [t(content)], "style": {}}}

def text(*parts):
    return {"block_type": 2, "text": {"elements": list(parts), "style": {}}}

def bullet(*parts):
    return {"block_type": 12, "bullet": {"elements": list(parts), "style": {}}}

def ordered(*parts):
    return {"block_type": 13, "ordered": {"elements": list(parts), "style": {}}}
```

## 3.3 内容填充脚本模板

```python
"""为一个小节填充课程内容。"""
import asyncio
import os

from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

async def main():
    async with FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    ) as client:
        wiki = WikiService(client)

        # 目标文档的 obj_token（从飞书 URL 或 API 获取）
        OBJ_TOKEN = "B16Bdn0vqopi8XxQaERcZPdenHd"

        # 构建内容块
        blocks = [
            heading2("什么是具身智能"),
            text(
                t("具身智能（Embodied AI）", bold=True),
                t("是指智能体通过与物理环境的交互来获取感知、执行行动的智能范式。"),
            ),
            text("与传统「离身」AI 不同，具身智能要求智能体拥有身体，能感知环境并做出反应。"),

            heading3("核心特征"),
            bullet(t("感知—行动闭环", bold=True), t("：通过行动改变环境，再感知变化")),
            bullet(t("环境交互性", bold=True), t("：在真实或仿真环境中实现智能行为")),
            bullet(t("多模态感知", bold=True), t("：融合视觉、听觉、触觉等多种传感器")),
            bullet(t("实时性与鲁棒性", bold=True), t("：在不确定条件下保持稳定")),
            bullet(t("学习与适应", bold=True), t("：通过持续交互学习新技能")),

            heading2("参考文献"),
            bullet(t("Brooks, R. (1991). Intelligence Without Representation. "),
                   t("Artificial Intelligence", italic=True), t(", 47, 139-160.")),
        ]

        # 写入文档
        print(f"写入 {len(blocks)} 个内容块...")
        result = await wiki.create_doc_block(OBJ_TOKEN, OBJ_TOKEN, blocks, index=-1)
        print(f"结果: code={result.get('code')}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 3.4 用 Claude 辅助生成内容

在终端中启动 Claude Code：

```bash
cd my-course-project
claude
```

给 Claude 的提示词：

```
我正在用飞书知识库构建一门「具身智能导论」课程。

知识空间 ID: 7594752784659073978
目标文档 obj_token: B16Bdn0vqopi8XxQaERcZPdenHd（1.1 具身智能的概念与内涵）

请帮我编写一个 Python 脚本，通过飞书 API 向这个文档填充教科书风格的内容。

要求：
1. 使用 feishu_kit 库的 WikiService
2. 内容面向应用型课程，浅显易懂，配有实际案例
3. 使用 heading2/heading3/text/bullet 等块类型
4. 混合使用 bold/italic 格式
5. 包含参考文献（带作者、年份、期刊）
6. 在需要配图的地方插入 [待配图] 占位说明和 AI 制图 prompt

请直接写出可运行的脚本，不要只写框架。
```

Claude 会生成完整的填充脚本。运行即可：

```bash
python fill_section_1_1.py
```

## 3.5 批量填充所有小节

对于大量小节，可以构建一个自动化脚本：

```python
"""批量填充所有小节 — 结合 AI 生成内容。"""
import asyncio
import os

from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

# 每个小节对应一个 obj_token 和内容描述
SECTIONS = {
    "GcJ6dJN2EoomGUx5U0IcVywznXg": "1.2 发展背景与研究意义 — 从控制论到大模型时代的演进",
    "IxvbdGYYWoiniwxIPi0cv0mpnEg": "1.3 与机器人、人工智能的关系 — 韦恩图、四代机器人",
    "I3JkdOfphoIakvxzXtOcf4xhnje": "1.4 具身智能操作系统 — Robonix 四层架构",
    "POtHd6pY9oFbPBxZHuCcT10Jnje": "1.5 学习目标与学习方法 — 12 周路线图",
    "QtCIdafeYoXvQWx3zOacmS8enjm": "1.6 教材整体结构说明 — 章节依赖关系",
}


async def main():
    async with FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    ) as client:
        wiki = WikiService(client)

        for obj_token, description in SECTIONS.items():
            print(f"--- {description} ---")
            print(f"obj_token: {obj_token}")
            print("请让 Claude 生成内容块，然后调用:")
            print(f"  await wiki.create_doc_block('{obj_token}', '{obj_token}', blocks)")
            print()

if __name__ == "__main__":
    asyncio.run(main())
```

> **工作流**: 对每个小节，你向 Claude 提供小节标题和要点 → Claude 生成 blocks 列表 → 你运行脚本写入。

---

上一章：[Ch2: 创建骨架](ch02-outline.md) | 下一章：[Ch4: 内容审查与修正](ch04-review.md)
