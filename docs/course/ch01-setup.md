# Ch1: 环境准备与飞书应用配置

本章完成所有前置工作，确保你能通过 feishu-kit 与飞书 API 通信。

## 1.1 安装 feishu-kit

```bash
# Python 3.11+ (推荐 3.12/3.13)
python --version

# 安装核心包（包含 CLI 工具）
pip install feishu-kit

# 可选：安装 PPT 生成工具（Ch5 课件制作需要）
pip install python-pptx

# 可选：安装 Claude Code（Ch3 AI 辅助内容生成需要）
# 参考 https://docs.anthropic.com/en/docs/claude-code
```

!!! info "feishu-kit 安装了什么"
    - `feishu_kit` — 核心 Python 包（零 FastAPI 依赖）
    - `feishu-kit` — CLI 命令行工具（基于 typer + rich）
    - 7 个 API 模块：wiki, drive, messaging, contacts, calendar, task, md2feishu

安装后验证：

```bash
feishu-kit version
```

你应该看到 ASCII banner 和版本号。

## 1.2 创建飞书应用

1. 前往 [open.feishu.cn/app](https://open.feishu.cn/app) → 点击「创建自建应用」
2. 填写应用名称（如「课程构建助手」），上传图标
3. 进入应用详情页，记录 **App ID**（`cli_xxx` 格式）和 **App Secret**
4. 在「权限管理」中开通以下权限：

    | 权限 | 权限标识 | 用途 |
    |------|---------|------|
    | 读写知识库 | `wiki:wiki` | 创建/编辑知识库文档 |
    | 云盘读写 | `drive:drive` | 上传 PPT 等文件 |
    | 文件上传 | `drive:file:upload` | 上传文件到云盘 |
    | 发送消息 | `im:message` | Bot 发消息（可选） |

5. 点击「版本管理与发布」→ 创建版本 → 申请发布

!!! warning "权限生效需要时间"
    权限发布后可能需要几分钟生效。如果遇到 `forbidden` 错误，等 1-2 分钟后重试。

## 1.3 配置环境变量

推荐使用 `.env` 文件管理凭证（加入 `.gitignore` 避免泄露）：

```bash
# .env
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="your_secret_here"
```

加载：

```bash
source .env
```

## 1.4 验证连接

### 方法一：CLI（推荐）

```bash
feishu-kit spaces
```

成功时会看到彩色表格列出你的知识空间：

```
         Name          │         Space ID        │ Description
 ──────────────────────┼─────────────────────────┼─────────────
  Embodied AI Course    │  7594752784659073978     │  Course wiki
```

### 方法二：Python 代码

```python
import asyncio
from feishu_kit import FeishuClient

async def check():
    async with FeishuClient(
        app_id="cli_xxx", app_secret="xxx"
    ) as client:
        result = await client.request("GET", "/wiki/v2/spaces")
        if result.get("code") == 0:
            spaces = result["data"]["items"]
            print(f"✓ 连接成功，共 {len(spaces)} 个知识空间")
            for s in spaces:
                print(f"  - {s['name']} (id={s['space_id']})")
        else:
            print(f"✗ 错误: {result}")

asyncio.run(check())
```

!!! tip "FeishuClient 自动管理 Token"
    你不需要手动获取 `tenant_access_token`。`FeishuClient` 会在首次请求时自动获取，并在过期前 5 分钟自动刷新。它还内置了连接池（httpx）和自动重试（429/5xx 指数退避）。

### 常见连接问题

| 错误 | 原因 | 解决 |
|------|------|------|
| `AuthenticationError` | App ID/Secret 错误 | 检查环境变量是否正确 |
| `code: 99991668` | 权限未开通 | 回到 1.2 步骤检查权限 |
| `code: 99991663` | 应用未发布 | 确认已创建版本并发布 |
| 超时 | 网络问题 | 检查代理设置 |

---

上一章：[目录](index.md) | 下一章：[Ch2: 创建知识空间与文档骨架](ch02-outline.md)
