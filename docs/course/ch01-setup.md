# Ch1: 环境准备与飞书应用配置

## 1.1 安装依赖

```bash
# Python 3.11+
python --version

# 安装 feishu-kit
pip install feishu-kit

# 安装 Claude Code（用于 AI 辅助）
#    参考 https://docs.anthropic.com/en/docs/claude-code

# 安装 PPT 生成工具（可选，用于课件制作）
pip install python-pptx
```

## 1.2 创建飞书应用

1. 前往 [open.feishu.cn/app](https://open.feishu.cn/app) 创建自建应用
2. 记录 **App ID** 和 **App Secret**
3. 开通以下权限：
   - `wiki:wiki` — 读写知识库
   - `drive:drive` — 云盘读写
   - `drive:file:upload` — 文件上传
4. 发布应用版本

## 1.3 配置环境变量

```bash
export FEISHU_APP_ID="cli_xxx"
export FEISHU_APP_SECRET="xxx"
```

## 1.4 验证连接

```python
import asyncio
from feishu_kit import FeishuClient

async def check():
    async with FeishuClient(
        app_id="cli_xxx", app_secret="xxx"
    ) as client:
        result = await client.request("GET", "/wiki/v2/spaces")
        print("OK!" if result.get("code") == 0 else f"Error: {result}")

asyncio.run(check())
```

或使用 CLI：

```bash
feishu-kit spaces
```

---

下一章：[Ch2: 创建知识空间与文档骨架](ch02-outline.md)
