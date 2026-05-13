# Ch3: AI 辅助填充课程内容

上一章：[Ch2: 创建骨架](ch02-outline.md) | 下一章：[Ch4: 内容审查](ch04-review.md)

---

## 本章目标

完成本章后，你将学会：

- 理解飞书文档的「块」模型（用积木来类比）
- 使用工具函数构建标题、段落、列表等内容块
- 用 Python 脚本将内容写入飞书文档
- 用 Claude AI 辅助生成课程内容
- 使用 Markdown 一键推送（更简单的方式）

> 换句话说：完成本章后，你的课程文档将不再空白，而是有完整的教科书内容。

---

## 3.1 理解飞书文档的「块」模型

### 用积木来理解

想象你在用乐高积木搭房子：

- **每一块积木** = 飞书文档中的一个「块」（Block）
- **不同形状的积木** = 不同类型的块（标题、段落、列表...）
- **搭出来的房子** = 一篇完整的文档

飞书文档就是这样——不是一大坨纯文本，而是由一个个「块」拼接起来的。

### 有哪些类型的块？

| 积木形状 | 块类型 | block_type 数字 | 你看到的效果 |
|---------|--------|:-----------:|-------------|
| 大标题 | heading2 | 4 | **像这样的大标题** |
| 小标题 | heading3 | 5 | *像这样的小标题* |
| 普通段落 | text | 2 | 一行普通的文字 |
| 圆点列表 | bullet | 12 | • 前面有个圆点 |
| 数字列表 | ordered | 13 | 1. 前面有数字 |
| 代码块 | code | 14 | 黑底白字的代码区域 |
| 表格 | table | 23 | 有行有列的表格 |

### 一个块长什么样？

以最简单的「普通段落」为例，它在 Python 中用一个字典（dict）表示：

```python
# 这就是一个最简单的文本块
{
    "block_type": 2,                          # 2 表示「普通段落」
    "text": {                                  # text 是这个块的类型名
        "elements": [                          # elements 里面放文字内容
            {
                "text_run": {                  # text_run 表示「一段文字」
                    "content": "Hello World",  # content 是实际显示的文字
                    "text_element_style": {}   # style 可以设置加粗、斜体等
                }
            }
        ],
        "style": {}
    }
}
```

看着很复杂对吧？别担心，我们接下来会用**工具函数**把它简化。

!!! tip "不用死记这些格式"
    你不需要记住块的 JSON 格式。下一节我们会写几个工具函数，把复杂的字典构造封装成简单的函数调用。比如 `heading2("标题")` 就能创建一个标题块。

---

## 3.2 块构建工具函数

### 工具函数是什么？

「工具函数」就是把我们经常要重复写的代码，打包成一个简短的函数。比如：

- 不用工具函数：每次都要写 `{"block_type": 4, "heading2": {"elements": [...]}}`
- 用工具函数：只需要写 `heading2("我的标题")`

### 工具函数清单

把下面的代码复制到你的项目里（后面所有脚本都会用到这些函数）：

```python
# ============================================================
# 飞书文档块构建工具函数
# 复制这段代码到你的脚本开头，或者单独存为一个 blocks.py 文件
# ============================================================

def t(content, bold=False, italic=False):
    """创建一个文字片段。

    参数说明：
        content  -- 要显示的文字内容
        bold     -- 是否加粗（默认不加粗）
        italic   -- 是否斜体（默认不斜体）

    使用示例：
        t("普通文字")                → 普通文字
        t("加粗文字", bold=True)     → **加粗文字**
        t("斜体文字", italic=True)   → *斜体文字*
    """
    style = {}                        # 先创建一个空的样式字典
    if bold:                          # 如果需要加粗
        style["bold"] = True          # 就把 bold 设为 True
    if italic:                        # 如果需要斜体
        style["italic"] = True        # 就把 italic 设为 True
    return {                          # 返回一个 text_run 字典
        "text_run": {
            "content": content,       # 实际显示的文字
            "text_element_style": style  # 文字样式
        }
    }


def heading2(content):
    """创建一个二级标题块。

    在飞书文档中显示为较大的标题文字。

    参数说明：
        content -- 标题文字内容

    使用示例：
        heading2("什么是具身智能")
    """
    return {
        "block_type": 4,              # 4 = 二级标题
        "heading2": {                 # 类型名
            "elements": [t(content)], # 标题文字（只能是纯文字，不能加粗/斜体）
            "style": {}
        }
    }


def heading3(content):
    """创建一个三级标题块（比二级标题小一点）。"""
    return {
        "block_type": 5,              # 5 = 三级标题
        "heading3": {
            "elements": [t(content)],
            "style": {}
        }
    }


def text(*parts):
    """创建一个普通段落块。

    可以传入多个文字片段，它们会拼在一起显示为一行。
    这样你就可以在一行里混合使用加粗、斜体等样式。

    使用示例：
        text(t("具身智能", bold=True), t("是指..."))
        → **具身智能**是指...
    """
    return {
        "block_type": 2,              # 2 = 普通段落
        "text": {
            "elements": list(parts),  # 把所有文字片段放进列表
            "style": {}
        }
    }


def bullet(*parts):
    """创建一个无序列表项（前面带圆点的）。

    使用示例：
        bullet(t("要点", bold=True), t("：详细说明"))
        → • **要点**：详细说明
    """
    return {
        "block_type": 12,             # 12 = 无序列表
        "bullet": {
            "elements": list(parts),
            "style": {}
        }
    }


def ordered(*parts):
    """创建一个有序列表项（前面带数字的）。"""
    return {
        "block_type": 13,             # 13 = 有序列表
        "ordered": {
            "elements": list(parts),
            "style": {}
        }
    }
```

!!! tip "这些函数和 feishu-kit 的关系"
    这些工具函数不是 feishu-kit 自带的，而是我们为了方便使用而写的辅助代码。feishu-kit 提供的是 `WikiService.create_doc_block()` 这个 API 调用方法，而工具函数帮你构造出符合格式要求的内容块。

    feishu-kit 的 `examples/07-course-builder/course_builder.py` 中也有完全相同的函数定义，你可以直接参考。

---

## 3.3 内容填充脚本（手把手教学）

现在我们用上面学的工具函数，写一个完整的脚本来填充一个小节的内容。

> **我们要做什么**：向飞书文档中写入一段关于「具身智能」的课程内容，包括标题、正文段落、要点列表和参考文献。

### 第 1 步：创建脚本文件

创建文件 `fill_section_1_1.py`，把以下代码完整复制进去：

```python
"""
为一个小节填充课程内容。

这个脚本会：
1. 连接飞书 API
2. 构建一组内容块（标题 + 正文 + 列表 + 参考文献）
3. 把这些内容块写入指定的飞书文档
"""
# ============================================================
# 第 1 部分：导入需要的模块
# ============================================================
import asyncio   # Python 异步编程模块（飞书 API 调用需要）
import os        # 读取环境变量的模块

# feishu-kit 的核心客户端 —— 负责和飞书服务器通信
from feishu_kit import FeishuClient
# feishu-kit 的知识库服务 —— 提供操作知识库的各种方法
from feishu_kit.modules.wiki import WikiService

# ============================================================
# 第 2 部分：把工具函数复制过来（或者 import 你的 blocks.py）
# ============================================================
# （这里省略工具函数的定义，请把 3.2 节的工具函数粘贴到这里）

# ============================================================
# 第 3 部分：设置目标文档
# ============================================================
# obj_token 是你要写入的文档的 ID
# 从 Ch2 的 list_all_nodes 输出中获取，或者从飞书文档 URL 中复制
OBJ_TOKEN = "B16Bdn0vqopi8XxQaERcZPdenHd"  # ← 替换成你自己的！

# ============================================================
# 第 4 部分：构建内容块
# ============================================================
# blocks 是一个列表，里面每个元素就是一个「块」
# 飞书会按照列表的顺序，依次把这些块添加到文档中
blocks = [
    # --- 标题 ---
    heading2("什么是具身智能"),       # 一个二级标题

    # --- 正文段落（混合加粗和普通文字） ---
    text(
        t("具身智能（Embodied AI）", bold=True),  # 加粗显示
        t("是指智能体通过与物理环境的交互来获取感知、执行行动的智能范式。"),
    ),
    # 这是一个纯文字段落（没有加粗）
    text("与传统「离身」AI 不同，具身智能要求智能体拥有身体，能感知环境并做出反应。"),

    # --- 小标题 + 列表 ---
    heading3("核心特征"),             # 一个三级标题
    bullet(t("感知—行动闭环", bold=True), t("：通过行动改变环境，再感知变化，形成闭环")),
    bullet(t("环境交互性", bold=True), t("：智能行为在真实或仿真物理环境中实现")),
    bullet(t("多模态感知", bold=True), t("：融合视觉、听觉、触觉等多种传感器信息")),
    bullet(t("实时性与鲁棒性", bold=True), t("：在不确定条件下保持稳定运行")),
    bullet(t("学习与适应", bold=True), t("：通过持续交互学习新技能、适应新场景")),

    # --- 类比段落 ---
    heading3("生活中的类比"),
    text(
        t("会开车 vs 懂交规：", bold=True),
        t("熟读驾驶手册但从未上路的人，和有实际驾驶经验的人，差距在哪？"),
    ),

    # --- 参考文献（注意期刊名用斜体） ---
    heading2("参考文献"),
    bullet(
        t("Brooks, R. (1991). Intelligence Without Representation. "),
        t("Artificial Intelligence", italic=True),  # 期刊名用斜体
        t(", 47, 139-160."),
    ),
]

# ============================================================
# 第 5 部分：连接飞书并写入内容
# ============================================================
async def main():
    # 从环境变量读取凭证
    app_id = os.environ["FEISHU_APP_ID"]
    app_secret = os.environ["FEISHU_APP_SECRET"]

    # async with 会自动管理连接的创建和关闭
    async with FeishuClient(app_id=app_id, app_secret=app_secret) as client:
        # 创建 WikiService —— 它是操作知识库的工具箱
        wiki = WikiService(client)

        # 写入内容块
        # create_doc_block 的 4 个参数：
        #   OBJ_TOKEN  -- 文档 ID（告诉飞书写入哪个文档）
        #   OBJ_TOKEN  -- 父块 ID（通常是文档自身，所以和文档 ID 相同）
        #   blocks     -- 内容块列表
        #   index=-1   -- 写入位置（-1 表示追加到文档末尾）
        print(f"正在写入 {len(blocks)} 个内容块...")  # 先打印要写几个块
        result = await wiki.create_doc_block(OBJ_TOKEN, OBJ_TOKEN, blocks, index=-1)

        # 打印结果
        # code=0 表示成功
        if result.get("code") == 0:
            print("写入成功！去飞书看看吧。")
        else:
            print(f"写入失败: {result}")

# ============================================================
# 第 6 部分：运行脚本
# ============================================================
# asyncio.run() 是启动异步函数的标准方式
if __name__ == "__main__":
    asyncio.run(main())
```

### 第 2 步：运行脚本

```bash
python fill_section_1_1.py
```

预期输出：

```
正在写入 12 个内容块...
写入成功！去飞书看看吧。
```

### 第 3 步：去飞书查看结果

打开你的飞书知识库，点击 1.1 小节，你应该能看到完整的课程内容了！

### 如果你遇到了问题

| 现象 | 可能原因 | 解决方法 |
|------|---------|---------|
| `KeyError: 'FEISHU_APP_ID'` | 环境变量没有设置 | 运行 `source .env`（Ch1 讲过） |
| `AuthenticationError` | App ID 或 App Secret 填错了 | 检查环境变量是否正确 |
| `code: 99991672` | 文档 obj_token 不存在 | 检查 OBJ_TOKEN 是否正确，或确认文档没有被删除 |
| `invalid param` | 有空的 text_run | 检查是否有 `t("")` 空字符串，改用 `t(" ")` |

---

## 3.4 用 Claude AI 辅助生成内容

手动写内容块很累，特别是当你有几十个小节要填充的时候。这时候可以让 Claude AI 来帮你。

### 什么是 Claude Code？

Claude Code 是 Anthropic 公司出品的 AI 编程助手。你可以在终端里和它对话，它会帮你写代码、调试错误、生成内容。

### 怎么用？

**第 1 步**：安装 Claude Code（参考 [官方文档](https://docs.anthropic.com/en/docs/claude-code)）

**第 2 步**：在项目目录打开终端，输入 `claude` 启动对话

**第 3 步**：把下面的提示词复制粘贴给 Claude：

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

**第 4 步**：Claude 会生成完整的 Python 脚本，保存并运行它即可。

!!! tip "给 Claude 越具体的要求，生成的质量越高"
    不要只说"帮我写内容"，而是告诉它：目标读者是谁、内容深度、要包含哪些部分、格式要求。就像给人类作者提需求一样。

---

## 3.5 用 Markdown 推送（更简单的方式）

如果你觉得手动构造块太复杂，还有一个更简单的方式：**先写 Markdown，再一键推送到飞书**。

### 什么是 Markdown？

Markdown 是一种简单的文本格式，用几个特殊符号就能表示标题、加粗、列表等。比如：

```markdown
# 大标题
## 二级标题
**加粗文字** 和 *斜体文字*
- 圆点列表项
1. 数字列表项
```

### 用 CLI 一行推送

如果你已经有一个 `.md` 文件，直接用命令行推送：

```bash
# 把 section_1_1.md 文件推送到飞书知识库
feishu-kit push section_1_1.md 7594752784659073978 --title "1.1 具身智能的概念与内涵"
```

参数说明：
- `section_1_1.md` — 你的 Markdown 文件路径
- `7594752784659073978` — 知识空间 ID
- `--title` — 文档标题

成功后会显示：

```
✓ Pushed 1.1 具身智能的概念与内涵
  Blocks written: 15
  URL: https://your-domain.feishu.cn/wiki/B16Bdn0vqopi8XxQaERcZPdenHd
```

### 用 Python 代码推送

```python
import asyncio
import os

from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService
from feishu_kit.modules.md2feishu import Md2FeishuService


async def main():
    async with FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    ) as client:
        # 第 1 步：创建 WikiService（操作知识库）
        wiki = WikiService(client)

        # 第 2 步：创建 Md2FeishuService（Markdown 转飞书）
        # 注意：它接收的是 WikiService，不是 FeishuClient
        # 这叫「依赖注入」——让 Md2FeishuService 复用 WikiService 的能力
        md = Md2FeishuService(wiki)

        # 第 3 步（可选）：先预览转换结果，不调用 API
        # 这样你可以看看 Markdown 会被转成多少个块
        markdown_content = """
# 什么是具身智能

**具身智能**是指智能体通过与物理环境的交互来获取感知的智能范式。

## 核心特征

- 感知—行动闭环
- 环境交互性
- 多模态感知
- 实时性与鲁棒性
"""
        blocks = await md.preview(markdown_content)
        print(f"预览：将生成 {len(blocks)} 个内容块")

        # 第 4 步：推送到飞书知识库
        result = await md.push_markdown(
            markdown_content,          # Markdown 文本
            title="1.1 具身智能的概念",  # 文档标题
            space_id="your_space_id",   # 知识空间 ID
        )
        print(f"推送成功！URL: {result['url']}")


asyncio.run(main())
```

### Markdown 和飞书块的对应关系

| 你写的 Markdown | 飞书文档中的效果 |
|----------------|----------------|
| `# 一级标题` | 大标题 |
| `## 二级标题` | 中标题 |
| `### 三级标题` | 小标题 |
| 普通文字 | 正文段落 |
| `**加粗**` | **加粗** |
| `*斜体*` | *斜体* |
| `- 列表项` | • 圆点列表 |
| `1. 列表项` | 1. 数字列表 |
| `` ```代码``` `` | 代码块 |
| `> 引用` | 引用块 |

---

## 3.6 批量填充所有小节

当你需要填充很多小节时，可以这样组织工作流：

```
对每个小节重复以下步骤：
  1. 告诉 Claude 这个小节的标题和要点
  2. Claude 生成内容块（或你用 Markdown 写）
  3. 运行脚本写入飞书
  4. 去飞书检查效果
```

下面这个脚本会遍历所有小节，打印出每个小节的信息，方便你逐个处理：

```python
"""批量处理多个小节 — 打印每个小节的信息。"""
import asyncio
import os

from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

# 每个小节对应：
#   key   = obj_token（文档 ID，从 Ch2 获取）
#   value = 小节描述（方便你辨认这是哪个小节）
SECTIONS = {
    "GcJ6dJN2EoomGUx5U0IcVywznXg": "1.2 发展背景与研究意义",
    "IxvbdGYYWoiniwxIPi0cv0mpnEg": "1.3 与机器人、人工智能的关系",
    "I3JkdOfphoIakvxzXtOcf4xhnje": "1.4 具身智能操作系统",
    "POtHd6pY9oFbPBxZHuCcT10Jnje": "1.5 学习目标与学习方法",
    "QtCIdafeYoXvQWx3zOacmS8enjm": "1.6 教材整体结构说明",
}


async def main():
    async with FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    ) as client:
        wiki = WikiService(client)

        # 遍历每个小节
        for obj_token, description in SECTIONS.items():
            print(f"--- {description} ---")
            print(f"  obj_token: {obj_token}")
            print(f"  写入命令: wiki.create_doc_block('{obj_token}', '{obj_token}', blocks)")
            print()  # 空行分隔


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 关键概念回顾

本章你学到了 5 个关键概念：

1. **块模型**：飞书文档 = 一个个块（标题、段落、列表...）拼接而成
2. **工具函数**：`t()`、`heading2()`、`text()`、`bullet()` 简化块的构造
3. **create_doc_block**：`wiki.create_doc_block(obj_token, obj_token, blocks, index=-1)` 写入内容
4. **AI 辅助**：给 Claude 具体的提示词，让它帮你生成内容块脚本
5. **Markdown 推送**：用 `Md2FeishuService` 或 `feishu-kit push` 一键推送 Markdown 到飞书

---

上一章：[Ch2: 创建骨架](ch02-outline.md) | 下一章：[Ch4: 内容审查](ch04-review.md)
