# Ch3: AI 辅助填充课程内容

这是整个工作流的核心 — 用 AI 为每个小节生成教科书内容，通过飞书 DocX Block API 写入文档。

## 3.1 理解飞书文档的块模型

飞书文档不是纯文本，而是由「块」（Block）组成的树结构。每个块有一个 `block_type` 和对应的类型字段：

| block_type | 类型 | 说明 |
|:----------:|------|------|
| 2 | `text` | 普通段落 |
| 4 | `heading2` | 二级标题 |
| 5 | `heading3` | 三级标题 |
| 12 | `bullet` | 无序列表 |
| 13 | `ordered` | 有序列表 |
| 14 | `code` | 代码块 |
| 23 | `table` | 表格 |

每个文本块内部包含一个 `elements` 列表，每个元素是一个 `text_run`：

```python
# 最简单的文本块
{
    "block_type": 2,
    "text": {
        "elements": [
            {"text_run": {"content": "Hello World", "text_element_style": {}}}
        ],
        "style": {}
    }
}
```

## 3.2 块构建工具函数

这些工具函数在整个项目中反复使用。feishu-kit 的 `examples/07-course-builder` 中也有同样的定义：

```python
# --- 块构建工具（复制到你的项目中） ---

def t(content, bold=False, italic=False):
    """创建 text_run 元素。"""
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

!!! tip "富文本组合"
    `text()` 和 `bullet()` 接受多个 `text_run` 参数，可以组合不同样式：
    ```python
    # 一段话中混合粗体和普通文本
    text(t("具身智能（Embodied AI）", bold=True), t("是指..."))
    # 参考文献中混合普通+斜体
    bullet(t("Brooks (1991). "), t("AI Journal", italic=True), t(", 47."))
    ```

## 3.3 内容填充脚本模板

这是一个完整的填充脚本，写入一个小节的内容：

```python
"""为一个小节填充课程内容。"""
import asyncio
import os

from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

# 目标文档的 obj_token（从 Ch2 的 list_all_nodes 结果中获取）
OBJ_TOKEN = "B16Bdn0vqopi8XxQaERcZPdenHd"


async def main():
    async with FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    ) as client:
        wiki = WikiService(client)

        # 构建内容块
        blocks = [
            heading2("什么是具身智能"),
            text(
                t("具身智能（Embodied AI）", bold=True),
                t("是指智能体通过与物理环境的交互来获取感知、执行行动的智能范式。"),
            ),
            text("与传统「离身」AI 不同，具身智能要求智能体拥有身体，能感知环境并做出反应。"),

            heading3("核心特征"),
            bullet(t("感知—行动闭环", bold=True), t("：通过行动改变环境，再感知变化，形成闭环")),
            bullet(t("环境交互性", bold=True), t("：智能行为在真实或仿真物理环境中实现")),
            bullet(t("多模态感知", bold=True), t("：融合视觉、听觉、触觉等多种传感器信息")),
            bullet(t("实时性与鲁棒性", bold=True), t("：在不确定条件下保持稳定运行")),
            bullet(t("学习与适应", bold=True), t("：通过持续交互学习新技能、适应新场景")),

            heading3("生活中的类比"),
            text(
                t("会开车 vs 懂交规：", bold=True),
                t("熟读驾驶手册但从未上路的人，和有实际驾驶经验的人，差距在哪？后者在与环境的交互中积累了「身体智慧」—— 这正是具身智能的核心。"),
            ),

            heading2("参考文献"),
            bullet(t("Brooks, R. (1991). Intelligence Without Representation. "),
                   t("Artificial Intelligence", italic=True), t(", 47, 139-160.")),
        ]

        # 写入文档（index=-1 表示追加到末尾）
        print(f"写入 {len(blocks)} 个内容块...")
        result = await wiki.create_doc_block(OBJ_TOKEN, OBJ_TOKEN, blocks, index=-1)
        print(f"结果: code={result.get('code')}")


if __name__ == "__main__":
    asyncio.run(main())
```

### 关键 API 说明

```python
wiki.create_doc_block(
    obj_token,       # 文档 ID
    block_id,        # 父块 ID（通常是文档自身）
    blocks,          # 内容块列表
    index=-1,        # -1 = 追加到末尾，0 = 插入到开头
)
```

!!! warning "空元素列表会报错"
    飞书 API 不接受 `elements: []`。如果某个 text_run 可能为空，用空格代替：`t(" ")`。

## 3.4 用 Claude 辅助生成内容

在终端中启动 Claude Code：

```bash
cd my-course-project
claude
```

**有效的提示词模板**：

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

Claude 会生成完整的填充脚本，直接运行：

```bash
python fill_section_1_1.py
```

## 3.5 用 Markdown 推送（更简单的方式）

如果你的内容是 Markdown 格式，可以使用 feishu-kit 的 `Md2FeishuService` 直接推送，无需手动构建块：

```python
from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService
from feishu_kit.modules.md2feishu import Md2FeishuService

async with FeishuClient(app_id="...", app_secret="...") as client:
    wiki = WikiService(client)
    md = Md2FeishuService(wiki)  # 注入 WikiService

    # 先预览（不调 API，只看转换结果）
    blocks = await md.preview("# Hello\n\n**Bold** text here")
    print(f"将生成 {len(blocks)} 个块")

    # 推送到知识库
    result = await md.push_markdown(
        "# Hello\n\n**Bold** text here",
        title="测试文档",
        space_id="7594752784659073978",
    )
    print(f"URL: {result['url']}")
```

或者使用 CLI 一行搞定：

```bash
feishu-kit push section_1_1.md $WIKU_SPACE_ID --title "1.1 具身智能的概念与内涵"
```

!!! info "Md2FeishuService 的设计"
    `Md2FeishuService` 通过构造函数接收 `WikiService` 实例（而不是自己创建）。这种依赖注入设计让你可以轻松替换为 mock 进行测试，或者用不同的 WikiService 实例操作不同的知识空间。

### 支持的 Markdown 元素

| Markdown | 飞书块类型 |
|----------|-----------|
| `# H1` / `## H2` / `### H3` | heading1/2/3 |
| 段落 | text |
| `- item` | bullet |
| `1. item` | ordered |
| `` ```code``` `` | code |
| `> quote` | quote |
| `**bold**` / `*italic*` | bold/italic text_run |
| 表格 | table |

## 3.6 批量填充所有小节

对于大量小节，构建自动化脚本：

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

> **推荐工作流**: 让 Claude 逐节生成内容块 → 你审核 → 运行脚本写入 → 进入 Ch4 审查。

---

上一章：[Ch2: 创建骨架](ch02-outline.md) | 下一章：[Ch4: 内容审查与修正](ch04-review.md)
