# Ch6: 内容扩充与学术引用

上一章：[Ch5: PPT 课件](ch05-ppt.md) | 下一章：[Ch7: 工作流与 FAQ](ch07-workflow.md)

---

## 本章目标

完成本章后，你将学会：

- 为课程内容补充学术引用和产业数据
- 使用块构建函数格式化参考文献
- 使用 `Md2FeishuService` 快速推送补充内容
- 构建数据对比表格

> 换句话说：完成本章后，你的课程将从"科普文"升级为有学术引用支撑的专业教材。

---

## 6.1 为什么要补充引用？

想象你写了一段话：

> 具身智能市场规模将在 2030 年达到 XX 亿美元。

读者会问：**这个数据从哪来的？** 如果没有引用，这段话就没有可信度。学术引用的作用就是告诉读者：**这不是我编的，这是某某在某年某篇论文/报告中说的。**

### 引用前 vs 引用后

**引用前**（没有出处）：

> 具身智能是当前AI领域最重要的研究方向之一。

**引用后**（有出处）：

> Brooks (1991) 在 *Artificial Intelligence* 期刊上提出，智能不需要依赖复杂的内部表征，而可以通过与环境的直接交互来实现。这一观点奠定了具身智能的理论基础。

差别很明显——后者让读者知道这个观点来自哪里，可以自己去查证。

---

## 6.2 让 Claude 帮你搜索引用

直接告诉 Claude 你需要什么类型的引用：

```
为 1.1 节「具身智能的概念与内涵」补充以下内容（追加到文档末尾）：

1. 学术溯源 — Brooks (1986/1991) 包容架构、Pfeifer & Bongard (2007) 形态计算
2. 产业数据 — MarketsandMarkets 市场预测、投融资数据
3. 典型系统案例 — Tesla Optimus Gen2、Boston Dynamics Atlas、Figure 02
4. 关键技术指标对比表
5. 扩充参考文献列表

要求：
- 每个论点必须有具体引用（作者、年份、来源）
- 数据点注明出处
- 不要与已有内容重复
- 不要太技术化，这是绪论
```

!!! warning "AI 生成的引用也需要验证"
    Claude 也可能编造不存在的论文。拿到引用后，建议用 Google Scholar 搜索确认论文是否真实存在。

---

## 6.3 用代码追加引用内容

### 追加到文档末尾

```python
"""追加学术引用到文档末尾。"""
import asyncio
import os

from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

# （工具函数定义省略，参见 Ch3）
OBJ_TOKEN = "B16Bdn0vqopi8XxQaERcZPdenHd"


async def main():
    async with FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    ) as client:
        wiki = WikiService(client)

        # 构建参考文献块
        # 注意：期刊名用 italic=True（斜体），这是学术规范
        new_blocks = [
            heading2("参考文献"),

            # 每条参考文献是一个 bullet（圆点列表项）
            # 用多个 t() 拼接：作者(年份). 标题. *期刊名*, 卷号.
            bullet(
                t("Brooks, R. (1986). A robust layered control system for a mobile robot. "),
                t("IEEE Journal on Robotics and Automation", italic=True),  # 期刊名斜体
                t(", 2(1), 14-23."),
            ),
            bullet(
                t("Pfeifer, R. & Bongard, J. (2007). "),
                t("How the Body Shapes the Way We Think", italic=True),  # 书名斜体
                t(". MIT Press."),
            ),
            bullet(
                t("Wiener, N. (1948). "),
                t("Cybernetics", italic=True),
                t(". MIT Press."),
            ),
            bullet(
                t("Google DeepMind (2023). RT-2: Vision-Language-Action Models. "),
                t("arXiv:2307.15818", italic=True),
                t("."),
            ),
        ]

        # 追加到文档末尾（index=-1）
        result = await wiki.create_doc_block(OBJ_TOKEN, OBJ_TOKEN, new_blocks, index=-1)
        print(f"追加结果: code={result.get('code')}")


asyncio.run(main())
```

### 引用格式规范

| 元素 | 格式 | 代码写法 |
|------|------|---------|
| 期刊名 | 斜体 | `t("Nature", italic=True)` |
| 书名 | 斜体 | `t("Cybernetics", italic=True)` |
| 关键术语 | 加粗 | `t("具身智能", bold=True)` |
| 英文术语首次出现 | 括号内英文 | `t("具身智能（Embodied AI）")` |

---

## 6.4 用 Md2FeishuService 快速推送

如果你有大量补充内容，用 Markdown 写好再一键推送更高效：

### 用 CLI 推送

```bash
# 把 Markdown 文件推送到飞书知识库
feishu-kit push references.md $WIKU_SPACE_ID --title "参考文献汇总"
```

成功后显示：

```
✓ Pushed 参考文献汇总
  Blocks written: 25
  URL: https://your-domain.feishu.cn/wiki/xxxxx
```

### 用 Python 推送

```python
from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService
from feishu_kit.modules.md2feishu import Md2FeishuService


async def main():
    async with FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    ) as client:
        wiki = WikiService(client)
        # Md2FeishuService 接收 WikiService（不是 FeishuClient）
        md = Md2FeishuService(wiki)

        # 先预览（不调 API，只在本地转换）
        markdown = """
# 参考文献汇总

- Brooks, R. (1991). Intelligence Without Representation. *Artificial Intelligence*, 47.
- Pfeifer, R. & Bongard, J. (2007). *How the Body Shapes the Way We Think*. MIT Press.
"""
        blocks = await md.preview(markdown)
        print(f"将生成 {len(blocks)} 个块")

        # 确认后推送到知识库
        result = await md.push_markdown(
            markdown,
            title="参考文献汇总",
            space_id=os.environ["WIKU_SPACE_ID"],
        )
        print(f"推送成功！URL: {result['url']}")


asyncio.run(main())
```

!!! info "Md2FeishuService 的设计"
    注意 `Md2FeishuService` 的构造函数接收的是 `WikiService` 而不是 `FeishuClient`。这是因为 Markdown 推送的本质是「创建文档 + 写入内容」——这两步都需要 WikiService。通过注入 WikiService，`Md2FeishuService` 可以复用已有的知识库操作能力，而不需要自己创建新的连接。

---

## 6.5 构建数据对比表格

飞书文档支持表格块，可以展示机器人参数对比等数据：

```python
# 构建一个表格块
# block_type 23 表示表格
table_block = {
    "block_type": 23,
    "table": {
        "rows": 5,          # 5 行（包含表头）
        "columns": 4,       # 4 列
        "header_row": True,  # 第一行是表头
        "cells": [
            # 第一行：表头（加粗显示）
            [
                t("机器人", bold=True),
                t("自由度", bold=True),
                t("重量", bold=True),
                t("亮点", bold=True),
            ],
            # 后续行：数据
            [t("Tesla Optimus Gen2"), t("28"), t("57kg"), t("灵巧手，FSD芯片")],
            [t("Figure 02"), t("41"), t("70kg"), t("OpenAI大模型驱动")],
            [t("Atlas (Boston Dynamics)"), t("28"), t("89kg"), t("液压→电动转型")],
            [t("智元远征A2"), t("49"), t("65kg"), t("国产开源生态")],
        ],
    },
}
```

在飞书文档中显示效果：

| 机器人 | 自由度 | 重量 | 亮点 |
|--------|:------:|------|------|
| Tesla Optimus Gen2 | 28 | 57kg | 灵巧手，FSD芯片 |
| Figure 02 | 41 | 70kg | OpenAI大模型驱动 |
| Atlas (Boston Dynamics) | 28 | 89kg | 液压→电动转型 |
| 智元远征A2 | 49 | 65kg | 国产开源生态 |

---

## 引用质量检查清单

为每个小节检查以下项目：

- [ ] 每个引用包含：作者、年份、标题、出处
- [ ] 期刊名和书名使用斜体
- [ ] 关键术语首次出现时给出英文原文
- [ ] 数据点标注了来源和年份
- [ ] 没有编造的引用（用 Google Scholar 验证）

---

上一章：[Ch5: PPT 课件](ch05-ppt.md) | 下一章：[Ch7: 工作流与 FAQ](ch07-workflow.md)
