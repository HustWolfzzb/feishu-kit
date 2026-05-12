# 实战项目：用 AI Agent + 飞书构建一门完整课程

> **保姆级教程** — 从注册飞书应用到课程上线，每一步都有代码和截图说明。
> 你将学到如何用 Claude Code + feishu-kit 在飞书知识库里构建一门完整的课程。

## 你将构建什么

一门名为「具身智能导论」的完整飞书知识库课程，包含：

```
具身智能导论（知识空间）
├── 绪论
│   ├── 1.1 具身智能的概念与内涵
│   ├── 1.2 发展背景与研究意义
│   ├── 1.3 与机器人、人工智能的关系
│   ├── 1.4 具身智能操作系统
│   ├── 1.5 学习目标与学习方法
│   └── 1.6 教材整体结构说明
├── 第二章 感知基础
│   └── ...
└── ...
```

每个章节不仅有文档内容，还有配套的 PPT 课件作为子文档。

## 前置准备

### 环境

```bash
# 1. Python 3.11+
python --version

# 2. 安装 feishu-kit
pip install feishu-kit

# 3. 安装 Claude Code（用于 AI 辅助）
#    参考 https://docs.anthropic.com/en/docs/claude-code

# 4. 安装 PPT 生成工具（可选，用于课件制作）
pip install python-pptx
```

### 飞书应用配置

1. 前往 [open.feishu.cn/app](https://open.feishu.cn/app) 创建自建应用
2. 记录 **App ID** 和 **App Secret**
3. 开通以下权限：
   - `wiki:wiki` — 读写知识库
   - `drive:drive` — 云盘读写
   - `drive:file:upload` — 文件上传
4. 发布应用版本

设置环境变量：

```bash
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
```

验证连接：

```bash
python -c "
import asyncio
from feishu_kit import FeishuClient

async def check():
    c = FeishuClient('$FEISHU_APP_ID', '$FEISHU_APP_SECRET')
    r = await c.request('GET', '/wiki/v2/spaces')
    print('OK!' if r.get('code') == 0 else f'Error: {r}')
    await c.close()
asyncio.run(check())
"
```

---

## 第一步：创建知识空间和文档骨架

### 1.1 创建知识空间

在飞书客户端中：
1. 打开「知识库」→ 点击「+」→ 创建知识空间
2. 命名为「具身智能导论」
3. 记录下知识空间的 **space_id**（URL 中 `/wiki/space/` 后面的那串数字）

> 或者通过 API：在飞书开放平台创建后，调用 `GET /wiki/v2/spaces` 获取 space_id。

### 1.2 用脚本创建文档骨架

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
    client = FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    )
    wiki = WikiService(client)

    try:
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

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
export WIKU_SPACE_ID="7594752784659073978"
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

## 第二步：AI 辅助填充课程内容

这是本项目最关键的部分 — 用 AI Agent 为每个小节生成课程内容并写入飞书。

### 2.1 理解飞书文档的块模型

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

### 2.2 内容填充脚本模板

创建 `scripts/fill_content.py`：

```python
"""为一个小节填充课程内容。"""
import asyncio
import os
from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

# --- 块构建工具 ---
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


async def main():
    client = FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    )
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

        heading3("类比：学骑自行车"),
        text(
            "没有人能仅通过阅读物理教材就学会骑自行车。你需要真正坐上去、感受平衡、摔倒、再调整——",
            t("这个过程中，你的身体和大脑在持续协作。", bold=True),
        ),

        heading2("参考文献"),
        bullet(t("Brooks, R. (1991). Intelligence Without Representation. "), t("Artificial Intelligence", italic=True), t(", 47, 139-160.")),
        bullet(t("Pfeifer, R. & Bongard, J. (2007). "), t("How the Body Shapes the Way We Think", italic=True), t(". MIT Press.")),
    ]

    # 写入文档
    print(f"写入 {len(blocks)} 个内容块...")
    result = await wiki.create_doc_block(OBJ_TOKEN, OBJ_TOKEN, blocks, index=-1)
    print(f"结果: code={result.get('code')}")

    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
```

### 2.3 用 Claude 辅助生成内容

在终端中启动 Claude Code：

```bash
# 在项目目录下启动
cd my-course-project
claude
```

给 Claude 的提示词（这是实际有效的 prompt）：

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

Claude 会生成完整的填充脚本。你只需要运行它：

```bash
python fill_section_1_1.py
```

### 2.4 批量填充所有小节

对于大量小节，可以写一个自动化脚本：

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
    client = FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    )
    wiki = WikiService(client)

    for obj_token, description in SECTIONS.items():
        print(f"--- {description} ---")
        print(f"obj_token: {obj_token}")
        print("请让 Claude 生成内容块，然后调用:")
        print(f"  await wiki.create_doc_block('{obj_token}', '{obj_token}', blocks)")
        print()

    await client.close()

asyncio.run(main())
```

> **工作流**: 对每个小节，你向 Claude 提供小节标题和要点 → Claude 生成 blocks 列表 → 你运行脚本写入。

---

## 第三步：内容审查与修正

内容写入后，你需要检查和优化。

### 3.1 查看当前内容

```python
async def review_content(wiki, obj_token):
    """读取文档全文并显示。"""
    raw = await wiki.get_doc_raw_content(obj_token)
    content = raw.get("data", {}).get("content", "")
    print(content)
    print(f"\n--- {len(content)} chars ---")
```

### 3.2 向 Claude 请求修改

```
请检查我刚才填充到 1.1 小节的内容，要求：
1. 去除AI味道（避免大量重复废话、过度热情的语气）
2. 检查每小节前后逻辑，避免前后不一致
3. 确保内容连贯性
4. 引用的论文和年份要准确

文档 obj_token: B16Bdn0vqopi8XxQaERcZPdenHd
```

Claude 会生成追加内容或修改建议的脚本。

---

## 第四步：为每个小节制作 PPT 课件

### 4.1 生成 PPT 文件

```python
"""为每个小节生成 PPT 课件。"""
from pptx import Presentation
from pptx.util import Inches, Pt

def make_ppt(title, slides_content, output_path):
    """slides_content: list of (slide_title, [bullet_points])"""
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 标题页
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    txBox = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(11), Inches(3))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(44)
    p.font.bold = True

    # 内容页
    for slide_title, bullets in slides_content:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        # 标题
        txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12), Inches(1))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = slide_title
        p.font.size = Pt(32)
        p.font.bold = True
        # 要点
        txBox2 = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11), Inches(5))
        tf2 = txBox2.text_frame
        for i, bullet in enumerate(bullets):
            if i == 0:
                p = tf2.paragraphs[0]
            else:
                p = tf2.add_paragraph()
            p.text = bullet
            p.font.size = Pt(22)
            p.space_after = Pt(12)

    prs.save(output_path)
```

### 4.2 上传到云盘并移入知识库

```python
from feishu_kit.modules.drive import DriveService

async def upload_ppt(client, wiki, drive, space_id, parent_node, file_path, file_name):
    # 1. 上传到云盘
    with open(file_path, "rb") as f:
        file_data = f.read()
    upload_result = await drive.upload_file("", file_name, file_data)
    file_token = upload_result["data"]["file_token"]

    # 2. 移入知识库
    move_result = await wiki.move_docs_to_wiki(
        space_id=space_id,
        parent_wiki_token=parent_node,
        obj_token=file_token,
        obj_type="file",  # PPT 用 "file"
    )
    return move_result
```

> **重要**: `obj_type="file"` 是关键 — PPT 不是 "doc"，而是 "file" 类型。

### 4.3 批量处理所有小节

```python
async def batch_create_and_upload_ppts(client, wiki, space_id, sections):
    """sections: list of (obj_token, node_token, title)"""
    drive = DriveService(client)

    for obj_token, node_token, title in sections:
        ppt_path = f"/tmp/{title}.pptx"

        # 从文档获取内容（简化版，实际需要解析 blocks）
        raw = await wiki.get_doc_raw_content(obj_token)
        content = raw.get("data", {}).get("content", "")

        # 生成 PPT（这里简化，实际用 AI 生成更好的内容）
        slides = generate_slides_from_content(content)
        make_ppt(title, slides, ppt_path)

        # 上传
        result = await upload_ppt(
            client, wiki, drive, space_id, node_token, ppt_path, f"{title}.pptx"
        )
        print(f"{title}: {result.get('code')}")


def generate_slides_from_content(content):
    """将文档内容拆分为幻灯片（简化版）。"""
    slides = []
    paragraphs = [p.strip() for p in content.split("\n") if p.strip()]

    current_title = "概述"
    current_bullets = []

    for p in paragraphs:
        if len(p) < 30 and not p.endswith(("。", "，")):
            # 短文本可能是标题
            if current_bullets:
                slides.append((current_title, current_bullets))
            current_title = p
            current_bullets = []
        else:
            # 截断过长的段落
            current_bullets.append(p[:100] + ("..." if len(p) > 100 else ""))

    if current_bullets:
        slides.append((current_title, current_bullets))

    return slides
```

---

## 第五步：内容扩充与引用

课程内容需要学术引用来增强可信度。

### 5.1 引用搜索策略

向 Claude 提供明确要求：

```
为 1.1 节「具身智能的概念与内涵」补充以下内容（追加到文档末尾）：

1. 学术溯源 — Brooks (1986/1991) 包容架构、Pfeifer & Bongard (2007) 形态计算
2. 产业数据 — MarketsandMarkets 市场预测、投融资数据（Figure AI、Physical Intelligence）
3. 典型系统案例 — Tesla Optimus Gen2、Boston Dynamics Atlas、Figure 02、智元机器人
4. 关键技术指标对比表
5. 扩充参考文献列表

要求：
- 每个论点必须有具体引用（作者、年份、来源）
- 数据点注明出处
- 不要与已有内容重复
- 不要太技术化，这是绪论
```

### 5.2 追加内容的代码模式

```python
# 追加内容到现有文档末尾（index=-1）
await wiki.create_doc_block(obj_token, obj_token, new_blocks, index=-1)
```

---

## 完整工作流回顾

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

## 常见问题

### Q: API 返回 "forbidden"
检查飞书应用的权限范围是否已开通并发布。部分 API 需要管理员审批。

### Q: 上传 PPT 后在知识库看不到文件节点
确保使用 `move_docs_to_wiki` 而非 `create_node`。`create_node` 不支持 file 类型。

### Q: 文档块写入返回 "invalid param"
检查是否有空的 text_run（`elements: []`），飞书 API 不接受空元素列表。用空格代替：`text_run(" ")`。

### Q: 如何处理批量操作中的错误
建议每个小节单独 try/except，记录失败的 obj_token，最后统一重试：

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

---

## 下一步

- 将工作流封装成 CLI 工具
- 添加自动化测试
- 探索飞书多维表格作为课程进度管理
- 集成 LLM API 实现全自动内容生成
