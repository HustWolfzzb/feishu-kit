# Ch6: 内容扩充与学术引用

课程内容需要学术引用和产业数据来增强可信度和深度。本章介绍内容扩充策略和引用格式。

## 6.1 引用搜索策略

向 Claude 提供明确的引用要求，避免模糊的"帮我加引用"：

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

### 引用质量检查清单

- [ ] 每个引用有作者、年份、标题、出处
- [ ] 期刊名用斜体（`italic=True`）
- [ ] 关键术语首次出现时给出英文原文
- [ ] 数据点标注来源和年份

## 6.2 追加内容的代码模式

```python
# 追加到文档末尾
await wiki.create_doc_block(obj_token, obj_token, new_blocks, index=-1)
```

### 用 Md2FeishuService 快速推送

如果你的补充内容已经是 Markdown 格式，可以用 `Md2FeishuService` 推送到已有空间：

```bash
# CLI 方式 — 一行推送 Markdown 文件
feishu-kit push references.md $WIKU_SPACE_ID --title "参考文献汇总"
```

```python
# Python 方式
from feishu_kit.modules.md2feishu import Md2FeishuService

md = Md2FeishuService(wiki)
result = await md.push_markdown(
    "# 参考文献\n\n- Brooks, R. (1991)...\n",
    title="参考文献汇总",
    space_id=space_id,
)
```

!!! info "Md2FeishuService 的依赖注入"
    注意 `Md2FeishuService` 接收 `WikiService` 实例而不是 `FeishuClient`。这是 feishu-kit 的设计模式：Service 之间通过依赖注入组合，而不是各自创建连接。`Md2FeishuService` 内部调用 `WikiService` 的方法来完成文档创建和写入。

## 6.3 学术引用的块构建示例

```python
# 参考文献条目 — 混合使用 bold 和 italic
references = [
    heading2("参考文献"),
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
        t("Wiener, N. (1948). "),
        t("Cybernetics: Or Control and Communication in the Animal and the Machine", italic=True),
        t(". MIT Press."),
    ),
    bullet(
        t("Google DeepMind (2023). RT-2: Vision-Language-Action Models Transfer Web Knowledge to Robotic Control. "),
        t("arXiv:2307.15818", italic=True),
        t("."),
    ),
]
```

## 6.4 数据表格的块构建

飞书文档支持表格块（`block_type: 23`），展示对比数据：

```python
# 机器人技术指标对比表
table_block = {
    "block_type": 23,
    "table": {
        "rows": 5,
        "columns": 4,
        "header_row": True,
        "cells": [
            # Header row
            [t("机器人", bold=True), t("自由度", bold=True),
             t("重量", bold=True), t("亮点", bold=True)],
            # Data rows
            [t("Tesla Optimus Gen2"), t("28"), t("57kg"), t("灵巧手，FSD芯片")],
            [t("Figure 02"), t("41"), t("70kg"), t("OpenAI大模型驱动")],
            [t("Atlas (Boston Dynamics)"), t("28"), t("89kg"), t("液压→电动转型")],
            [t("智元远征A2"), t("49"), t("65kg"), t("国产开源生态")],
        ],
    },
}
```

## 6.5 从现有文档提取内容生成 PPT 扩充

结合 Ch5 的 PPT 生成方法，可以为扩充内容也生成配套课件：

```python
# 读取已有文档内容
raw = await wiki.get_doc_raw_content(obj_token)
# ... 解析 blocks 提取要点 ...
# 生成 PPT 并上传
```

或者使用 CLI 快速查看文档内容后手动编写 PPT 要点：

```bash
feishu-kit inspect $OBJ_TOKEN
```

---

上一章：[Ch5: PPT 课件](ch05-ppt.md) | 下一章：[Ch7: 完整工作流与 FAQ](ch07-workflow.md)
