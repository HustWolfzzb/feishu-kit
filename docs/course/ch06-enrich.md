# Ch6: 内容扩充与学术引用

课程内容需要学术引用和产业数据来增强可信度和深度。

## 6.1 引用搜索策略

向 Claude 提供明确的引用要求：

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

## 6.2 追加内容的代码模式

```python
# 追加内容到现有文档末尾（index=-1）
await wiki.create_doc_block(obj_token, obj_token, new_blocks, index=-1)
```

## 6.3 学术引用的块构建示例

```python
# 参考文献条目
references = [
    bullet(
        t("Brooks, R. (1986). A robust layered control system for a mobile robot. "),
        t("IEEE Journal on Robotics and Automation", italic=True),
        t(", 2(1), 14-23."),
    ),
    bullet(
        t("Pfeifer, R. & Bongard, J. (2007). "),
        t("How the Body Shapes the Way We Think", italic=True),
        t(". MIT Press."),
    ),
    bullet(
        t("Brostow, G.J. et al. (2023). RT-2: Vision-Language-Action Models. "),
        t("arXiv:2307.15818", italic=True),
        t("."),
    ),
]
```

## 6.4 数据表格的块构建

飞书文档支持表格块，可以展示对比数据：

```python
table_block = {
    "block_type": 23,
    "table": {
        "rows": 5,
        "columns": 4,
        "header_row": True,
        "cells": [
            # Header
            [t("机器人", bold=True), t("自由度", bold=True),
             t("重量", bold=True), t("亮点", bold=True)],
            # Data rows
            [t("Tesla Optimus Gen2"), t("28"), t("57kg"), t("灵巧手，FSD芯片")],
            [t("Figure 02"), t("41"), t("70kg"), t("OpenAI大模型驱动")],
            [t("Atlas (BD)"), t("28"), t("89kg"), t("液压→电动转型")],
            [t("智元远征A2"), t("49"), t("65kg"), t("国产开源生态")],
        ],
    },
}
```

---

上一章：[Ch5: PPT 课件](ch05-ppt.md) | 下一章：[Ch7: 完整工作流与 FAQ](ch07-workflow.md)
