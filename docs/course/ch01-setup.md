# Ch1: 环境准备与飞书应用配置

上一章：[目录](index.md) | 下一章：[Ch2: 创建知识空间与文档骨架](ch02-outline.md)

---

## 本章目标

完成本章后，你将拥有：

- 一个能正常工作的 Python 环境，并且 feishu-kit 已经安装好
- 一个在飞书开放平台上创建好的应用（机器人），拥有操作知识库的权限
- 配置好的环境变量，让代码能安全地读取你的凭证
- 一条成功连接飞书 API 的验证结果

> 换句话说：完成本章后，你就可以开始用代码操控飞书了。

---

## 1.1 安装 feishu-kit

### 什么是 pip？

`pip` 是 Python 的"软件商店"——你用它在命令行里输入一行命令，就能自动从互联网下载并安装别人写好的 Python 库。就像手机上的应用商店一样，只不过 pip 装的是给开发者用的代码包。

打开你的终端（Windows 上叫"命令提示符"或 PowerShell，Mac/Linux 上叫 Terminal），输入以下命令：

**第 1 步：检查 Python 版本**

```bash
python --version
```

你应该看到类似这样的输出：

```
Python 3.12.4
```

!!! warning "Python 版本要求"
    feishu-kit 需要 Python 3.11 或更高版本。如果你的版本低于 3.11，请先去 [python.org](https://www.python.org/downloads/) 下载安装最新版。

    如果输入 `python --version` 后系统提示"找不到命令"，说明你还没有安装 Python，或者安装时没有勾选"添加到 PATH"选项。

**第 2 步：安装 feishu-kit**

```bash
pip install feishu-kit
```

你会看到 pip 在自动下载依赖包，最后显示：

```
Successfully installed feishu-kit-0.1.0 ...
```

!!! info "feishu-kit 安装了什么"
    这一条命令会安装两个东西：

    - `feishu_kit` —— Python 代码包，你在自己的 Python 脚本里 `import` 它来调用飞书 API
    - `feishu-kit` —— 命令行工具（CLI），在终端里直接输入 `feishu-kit` 就能用，不需要写代码

    它还包含 7 个 API 模块：wiki（知识库）、drive（云盘）、messaging（消息）、contacts（通讯录）、calendar（日历）、task（任务）、md2feishu（Markdown 转飞书）。

**第 3 步（可选）：安装额外工具**

```bash
# Ch5 课件制作需要这个包（可以以后再装）
pip install python-pptx
```

**第 4 步：验证安装成功**

```bash
feishu-kit version
```

你应该看到 ASCII 艺术字 banner 和版本号：

```
 ███████╗███████╗██╗     ██╗         ██████╗ ██╗  ██╗██╗████████╗
 ██╔════╝██╔════╝██║     ██║         ██╔══██╗██║ ██╔╝██║╚══██╔══╝
 █████╗  █████╗  ██║     ██║         ██████╔╝█████╔╝ ██║   ██║
 ██╔══╝  ██╔══╝  ██║     ██║         ██╔═══╝ ██╔═██╗ ██║   ██║
 ██║     ███████╗███████╗███████╗    ██║     ██║  ██╗██║   ██║
 ╚═╝     ╚══════╝╚══════╝╚══════╝    ╚═╝     ╚═╝  ╚═╝╚═╝   ╚═╝

  feishu-kit v0.1.0
```

如果你看到了这个 banner，说明安装成功了！

### 如果你遇到了问题

| 现象 | 可能原因 | 解决方法 |
|------|---------|---------|
| `pip` 不是内部或外部命令 | Python 未安装或未加入 PATH | 重新安装 Python，勾选 "Add Python to PATH" |
| `feishu-kit` 不是内部或外部命令 | pip 安装路径不在系统 PATH 中 | 尝试 `python -m feishu_kit.cli version`，或重新打开终端 |
| 安装时网络超时 | 网络问题或 pip 源访问慢 | 使用国内镜像：`pip install feishu-kit -i https://pypi.tuna.tsinghua.edu.cn/simple` |

---

## 1.2 创建飞书应用

在用代码操作飞书之前，你需要先在飞书开放平台上创建一个"应用"（也可以理解为"机器人"）。这个应用就是你的代码和飞书之间的桥梁——飞书需要知道"谁在调用我的接口"，而应用就是身份证明。

**第 1 步：打开飞书开放平台**

在浏览器中打开 [open.feishu.cn/app](https://open.feishu.cn/app)，用你的飞书账号登录。

> 你会看到一个"开发者后台"页面，左侧有导航栏，中间可能显示你已有的应用列表（第一次来就是空的）。

**第 2 步：创建新应用**

点击页面上的「**创建自建应用**」按钮。

> 会弹出一个表单，让你填写应用名称和上传图标。

- **应用名称**：随便起一个你能认出来的名字，比如「课程构建助手」
- **图标**：随便上传一张图片，或者用默认的也行
- 点击「**确定创建**」

**第 3 步：记录凭证**

创建完成后，你会自动跳转到应用的详情页面。在这个页面找到：

- **App ID** —— 格式类似 `cli_a5xxxxxxxxxxxxx`，这是你应用的"用户名"
- **App Secret** —— 一串随机字符，这是你应用的"密码"

!!! warning "保管好你的 App Secret"
    App Secret 就像你银行卡的密码，不要分享给别人，也不要提交到 Git 代码仓库中。如果泄露了，任何人都可以用你的应用身份调用飞书 API。

    请现在就把 App ID 和 App Secret 记下来（记到笔记本或临时文件中），下一步就要用到。

**第 4 步：开通权限**

你的应用需要获得"许可"才能操作飞书的各种功能。就像新员工入职需要开通各种系统权限一样。

在左侧菜单点击「**权限管理**」，然后搜索并开通以下权限：

| 权限名称 | 权限标识 | 为什么需要 |
|---------|---------|-----------|
| 读写知识库 | `wiki:wiki` | 创建和编辑知识库文档（核心功能） |
| 云盘读写 | `drive:drive` | 上传 PPT 等文件到云盘 |
| 文件上传 | `drive:file:upload` | 上传文件 |
| 发送消息 | `im:message` | 让 Bot 发送消息（可选，后续章节用） |

> 在权限管理页面，你会看到一个搜索框。输入权限标识（比如 `wiki:wiki`），就能找到对应的权限，点击「**开通**」即可。

**第 5 步：发布应用**

权限开通后，还需要"发布"应用才能让权限真正生效。

在左侧菜单点击「**版本管理与发布**」→ 点击「**创建版本**」→ 填写版本号（比如 `1.0.0`）和更新说明（随便写）→ 点击「**申请发布**」。

!!! warning "权限生效需要时间"
    点击发布后，权限可能需要 **1-2 分钟**才能完全生效。如果马上就去验证连接，可能会遇到 `forbidden` 错误。耐心等一下就好。

### 如果你遇到了问题

| 现象 | 可能原因 | 解决方法 |
|------|---------|---------|
| 找不到"创建自建应用"按钮 | 你的飞书账号没有管理员权限 | 联系你们公司的飞书管理员，让他们帮你创建或授予权限 |
| 权限搜索不到 | 飞书版本或套餐不支持该功能 | 确认你的飞书是企业版（免费版部分 API 不可用） |
| 发布后一直显示"审核中" | 企业开启了审批流程 | 需要管理员在飞书管理后台审批通过 |

---

## 1.3 配置环境变量

### 什么是"环境变量"？

**环境变量**是操作系统提供的一种"全局备忘录"。你可以把一些信息（比如密码、配置）写进环境变量，然后任何程序都能读取到它们。

为什么要用环境变量来存 App ID 和 App Secret，而不是直接写在代码里？原因有两个：

1. **安全**：如果你把密码写在代码里，然后把代码上传到 GitHub，全世界都能看到你的密码。环境变量只在你的电脑上存在，不会被上传。
2. **方便**：换一台电脑或换一个飞书应用，只需要改环境变量，不用改代码。

### 设置方法

**第 1 步：创建 .env 文件**

在你的项目根目录下创建一个名为 `.env` 的文件，内容如下：

```bash
# .env 文件 —— 把下面的 xxx 替换成你自己的真实值
export FEISHU_APP_ID="cli_a5xxxxxxxxxxxxx"
export FEISHU_APP_SECRET="你的App_Secret粘贴在这里"
```

**第 2 步：加载环境变量**

每次打开新终端后，需要运行一次 `source` 命令让环境变量生效：

```bash
source .env
```

没有任何输出就说明成功了。

**第 3 步：验证环境变量已设置**

```bash
echo $FEISHU_APP_ID
```

你应该看到你设置的 App ID（比如 `cli_a5xxxxxxxxxxxxx`）被打印出来。

!!! tip "每次打开新终端都要 source"
    `source .env` 只对当前终端窗口有效。如果你关闭终端再重新打开，需要再次运行 `source .env`。

!!! warning "把 .env 加入 .gitignore"
    如果你使用 Git 管理代码，务必在 `.gitignore` 文件中加入 `.env`，防止凭证被意外提交到代码仓库。

    ```bash
    echo ".env" >> .gitignore
    ```

### 如果你遇到了问题

| 现象 | 可能原因 | 解决方法 |
|------|---------|---------|
| `echo $FEISHU_APP_ID` 输出为空 | 没有 source .env，或者 .env 文件路径不对 | 确认你在 .env 文件所在的目录运行 `source .env` |
| Windows 上 `echo $FEISHU_APP_ID` 不生效 | Windows PowerShell 语法不同 | PowerShell 用 `$env:FEISHU_APP_ID`；CMD 用 `echo %FEISHU_APP_ID%` |
| Windows 上 `source` 命令不存在 | CMD/PowerShell 不支持 source | CMD 中用 `.env` 文件内容直接改为 `set FEISHU_APP_ID=xxx`，然后运行 `.\.env` 或逐行粘贴 |

---

## 1.4 验证连接

环境变量配好之后，我们来验证一下你的代码能不能成功和飞书"对话"。

我们提供两种验证方式：命令行工具（简单快捷）和 Python 代码（帮你理解原理）。两种都试试！

### 方法一：CLI 命令行工具（推荐先用这个）

```bash
feishu-kit spaces
```

这条命令会调用飞书 API，获取你账号下所有"知识空间"的列表。

成功时你会看到一张彩色表格：

```
         Name          │         Space ID        │ Description
 ──────────────────────┼─────────────────────────┼─────────────
  Embodied AI Course    │  7594752784659073978     │  Course wiki

Total: 1 spaces
```

> 如果你刚创建飞书应用、还没有任何知识空间，表格会是空的，但只要没有报错，就说明连接成功了。

### 方法二：Python 代码

下面这段代码做的事情和上面的 CLI 命令完全一样，只是用 Python 代码写的。通过这段代码你可以理解 feishu-kit 是怎么工作的。

> **我们接下来要做什么**：用 Python 代码连接飞书 API，获取知识空间列表并打印出来。这是你第一次用 feishu-kit 写代码！

```python
# 导入 asyncio 模块 —— Python 的异步编程工具
# 飞书 API 调用都是"异步"的（不会阻塞程序），所以需要 asyncio
import asyncio

# 导入 os 模块 —— 用来读取环境变量
import os

# 导入 FeishuClient —— feishu-kit 的核心客户端
# 它负责和飞书服务器通信，你只需要告诉它"做什么"，不用关心底层细节
from feishu_kit import FeishuClient


# 定义一个异步函数 —— async def 表示这是一个"异步函数"
# 异步函数可以让程序在等待网络响应时去做别的事情，提高效率
async def check():
    # 从环境变量读取 App ID 和 App Secret
    app_id = os.environ["FEISHU_APP_ID"]        # 你的应用"用户名"
    app_secret = os.environ["FEISHU_APP_SECRET"] # 你的应用"密码"

    # async with ... as client —— 创建客户端连接
    # FeishuClient 是一个"上下文管理器"，用 with 语句可以确保用完自动关闭连接
    async with FeishuClient(app_id=app_id, app_secret=app_secret) as client:
        # client.request() —— 向飞书 API 发送请求
        # "GET" 表示我们要"获取"数据（不是创建或修改）
        # "/wiki/v2/spaces" 是飞书知识库 API 的路径，意思是"列出所有知识空间"
        result = await client.request("GET", "/wiki/v2/spaces")

        # 检查返回结果
        # 飞书 API 的返回格式是 {"code": 0, "data": {...}}
        # code 为 0 表示成功
        if result.get("code") == 0:
            # 从返回数据中取出知识空间列表
            spaces = result["data"]["items"]
            # 打印成功信息和空间数量
            print(f"连接成功！共 {len(spaces)} 个知识空间")
            # 遍历每个空间，打印名称和 ID
            for s in spaces:
                print(f"  - {s['name']} (id={s['space_id']})")
        else:
            # 如果 code 不为 0，说明出错了，打印错误信息
            print(f"出错了: {result}")


# asyncio.run() —— 启动异步函数的固定写法
# 每个 Python 异步程序都需要这样来"启动"最外层的异步函数
asyncio.run(check())
```

把这段代码保存为 `test_connection.py`，然后运行：

```bash
python test_connection.py
```

成功时你会看到：

```
连接成功！共 1 个知识空间
  - Embodied AI Course (id=7594752784659073978)
```

> 看到这个输出，说明你的代码已经成功和飞书服务器通信了！

### FeishuClient 内部做了什么？

你可能会好奇：我只给了 App ID 和 App Secret，为什么就能直接调 API 了？`FeishuClient` 在背后帮你做了这些事：

1. **自动获取 Token**：每次调用飞书 API 都需要一个叫 `tenant_access_token` 的临时令牌。`FeishuClient` 会在第一次请求时自动用你的 App ID 和 Secret 去换取这个令牌，你不需要手动操作。

2. **自动刷新 Token**：这个令牌有效期只有 2 小时。`FeishuClient` 会在过期前 5 分钟自动刷新，你完全无感。

3. **连接池**：`FeishuClient` 内部使用 httpx 库管理了一个连接池（最多 20 个连接），避免每次请求都重新建立 TCP 连接，速度更快。

4. **自动重试**：如果遇到网络波动（429 限流或 5xx 服务器错误），`FeishuClient` 会自动重试最多 3 次，每次等待时间翻倍（指数退避），你不需要自己写重试逻辑。

> 简单说：你只管告诉 FeishuClient "我要做什么"，它会自动帮你处理令牌、连接、重试这些麻烦事。

### 如果你遇到了问题

| 错误信息 | 含义 | 解决方法 |
|---------|------|---------|
| `KeyError: 'FEISHU_APP_ID'` | 环境变量没设置 | 运行 `source .env`，再运行 `echo $FEISHU_APP_ID` 确认 |
| `AuthenticationError: Token request failed` | App ID 或 App Secret 不正确 | 回到飞书开放平台，重新复制 App ID 和 Secret，确保没有多余空格 |
| `AuthenticationError: Unauthorized` | 凭证无效 | 检查 App Secret 是否完整，是否不小心多了换行符 |
| `API error 99991668: ...` | 权限未开通 | 回到 1.2 节第 4 步，确认 `wiki:wiki` 权限已开通 |
| `API error 99991663: ...` | 应用未发布 | 回到 1.2 节第 5 步，确认已创建版本并发布 |
| 连接超时 / 无响应 | 网络问题 | 检查网络连接；如果你在公司内网，可能需要配置代理 |
| `pip` 安装失败 | 权限不足 | 尝试 `pip install --user feishu-kit` 或使用虚拟环境 |

!!! tip "推荐使用虚拟环境"
    如果你同时有多个 Python 项目，推荐用虚拟环境把每个项目的依赖隔离开：

    ```bash
    # 创建虚拟环境
    python -m venv .venv

    # 激活虚拟环境（每次打开新终端都要运行）
    # Linux / Mac:
    source .venv/bin/activate
    # Windows:
    .venv\Scripts\activate

    # 然后在虚拟环境里安装 feishu-kit
    pip install feishu-kit
    ```

---

## 小结

如果 `feishu-kit spaces` 或 Python 脚本都能正常返回结果，那么恭喜你，环境准备全部完成了！你的工具链已经就绪，下一章我们将正式开始创建飞书知识库中的文档结构。

---

上一章：[目录](index.md) | 下一章：[Ch2: 创建知识空间与文档骨架](ch02-outline.md)
