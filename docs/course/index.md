# 实战项目：用 AI Agent + 飞书构建一门完整课程

> **保姆级教程** — 从注册飞书应用到课程上线，每一步都有代码和说明。
> 你将学到如何用 Claude Code + [feishu-kit](https://github.com/HustWolfzzb/feishu-kit) 在飞书知识库里构建一门完整的课程。

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

## 我们用什么工具

| 工具 | 作用 | 为什么选它 |
|------|------|-----------|
| [feishu-kit](https://github.com/HustWolfzzb/feishu-kit) | 飞书 API Python 封装 | 异步优先、模块化、零框架绑定 |
| [Claude Code](https://docs.anthropic.com/en/docs/claude-code) | AI 辅助编程 | 生成内容块、审查质量、自动化脚本 |
| python-pptx | PPT 生成 | 纯 Python，无需 Office |
| 飞书知识库 | 课程托管 | 在线协作、权限管理、版本历史 |

!!! tip "关于 feishu-kit"
    feishu-kit 是本教程配套的开源项目，提供了 7 个飞书 API 模块（Wiki、Drive、Messaging、Contacts、Calendar、Task、md2feishu）、CLI 工具和可选的 FastAPI 服务器层。本教程中用到的所有 API 调用都来自 feishu-kit。

## 课程章节

| 章节 | 内容 |
|------|------|
| [Ch1: 环境准备](ch01-setup.md) | Python 环境、飞书应用创建、权限配置、feishu-kit 安装与验证 |
| [Ch2: 创建文档骨架](ch02-outline.md) | 知识空间创建、WikiService 批量创建章节/小节节点 |
| [Ch3: AI 填充内容](ch03-fill-content.md) | 飞书块模型、块构建工具、Claude 辅助生成、批量填充 |
| [Ch4: 内容审查](ch04-review.md) | CLI 查看内容、AI 辅助审查、去 AI 味、增量更新 |
| [Ch5: PPT 课件](ch05-ppt.md) | python-pptx 生成、DriveService 上传、移入知识库 |
| [Ch6: 学术引用](ch06-enrich.md) | 引用搜索、Md2FeishuService 快速推送、数据表格 |
| [Ch7: 工作流与 FAQ](ch07-workflow.md) | 全流程回顾、异常体系、FAQ、进阶方向 |

## 前置要求

- Python 3.11+
- 一个飞书开放平台应用（免费注册）
- Claude Code（可选，用于 AI 辅助）
