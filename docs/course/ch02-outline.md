# Ch2: 创建知识空间与文档骨架

上一章：[Ch1: 环境准备与飞书应用配置](ch01-setup.md) | 下一章：[Ch3: AI 辅助填充内容](ch03-fill-content.md)

---

## 本章目标

完成本章后，你将拥有：

- 一个在飞书知识库中创建好的"知识空间"
- 一个完整的课程文档树结构（包含章、节两层），每个节点都是一篇飞书文档
- 对 `WikiService` 核心方法的实践经验
- 清楚理解 `obj_token` 和 `node_token` 的区别

> 换句话说：完成本章后，你的飞书知识库里就会出现一棵像文件夹树一样的课程大纲，每个节点都是一篇空文档，等着你后续填充内容。

---

## 2.1 创建知识空间

### 什么是"知识空间"？

**知识空间**是飞书知识库中最顶层的容器，你可以把它理解为一个"大文件夹"或者"课程容器"。一个知识空间里可以包含很多文档，文档下面还可以有子文档，形成树形结构。

打个比方：如果飞书是一栋大楼，知识空间就是大楼里的一层——你可以在这一层里建很多房间（文档），每个房间里还可以有隔间（子文档）。

### 操作步骤

**第 1 步：在飞书客户端中创建知识空间**

打开飞书客户端（电脑版），按以下步骤操作：

1. 在左侧导航栏找到「**知识库**」图标并点击
2. 点击右上角的「**+**」按钮
3. 选择「**创建知识空间**」
4. 在弹出的表单中：
   - **名称**填写：`具身智能导论`（你可以换成自己的课程名）
   - **类型**选择：「**文档**」类型
5. 点击确认

**第 2 步：获取 space_id**

创建完成后，浏览器地址栏或飞书客户端会显示这个知识空间的 URL。你需要从中提取 **space_id**——这是这个知识空间的唯一编号，后面所有操作都要用到它。

```
https://your-domain.feishu.cn/wiki/space/7594752784659073978
                                       ^^^^^^^^^^^^^^^^^^^^
                                       这就是 space_id
```

> 就是 URL 中 `/wiki/space/` 后面那一串数字。

**第 3 步：用 CLI 快速确认**

让我们用命令行工具验证一下，确认 feishu-kit 能看到你刚创建的知识空间：

```bash
feishu-kit spaces
```

你应该看到类似这样的表格：

```
         Name          │         Space ID        │ Description
 ──────────────────────┼─────────────────────────┼─────────────
  具身智能导论           │  7594752784659073978     │
```

**第 4 步：保存 space_id 到环境变量**

找到你的知识空间后，把 space_id 保存到环境变量，方便后续使用：

```bash
export WIKU_SPACE_ID="7594752784659073978"
```

!!! tip "把 space_id 也写入 .env 文件"
    为了不用每次都手动 export，建议把这个变量也加到你的 `.env` 文件中：

    ```bash
    # 在 .env 文件末尾追加这一行（替换成你自己的 space_id）
    export WIKU_SPACE_ID="7594752784659073978"
    ```

### 如果你遇到了问题

| 现象 | 可能原因 | 解决方法 |
|------|---------|---------|
| `feishu-kit spaces` 显示空表格 | 知识空间还没创建，或者创建在了另一个飞书账号下 | 回到飞书客户端确认知识空间已创建 |
| 找不到知识库入口 | 飞书客户端版本太旧，或企业未开通知识库功能 | 更新飞书客户端，或联系管理员 |
| URL 中看不到 space_id | 可能是飞书客户端内嵌浏览器，URL 被隐藏了 | 尝试在浏览器中打开知识库，或在飞书客户端的"分享"中复制链接 |

---

## 2.2 理解 WikiService

### 什么是"节点"？

在飞书知识库中，每一篇文档、每一个文件夹都叫做一个**节点（Node）**。知识空间中的文档树，就是由一个个节点组成的。

你可以把知识空间想象成电脑上的文件夹系统：

- **知识空间** = 硬盘分区（比如 D 盘）
- **顶层节点** = 根目录下的文件夹（比如 `D:\绪论\`、`D:\感知基础\`）
- **子节点** = 文件夹里的文件或子文件夹（比如 `D:\绪论\1.1 概念与内涵.docx`）

每个节点都有一个标题，并且可以包含子节点，形成树形结构。

### WikiService 是什么？

`WikiService` 是 feishu-kit 封装的一个"服务类"，专门用来操作飞书知识库。它把飞书原始 API 的复杂调用包装成了简单易用的方法。你不需要记住飞书 API 的 URL 和参数格式，只需要调用 `WikiService` 的方法就行。

核心方法一览：

| 方法 | 作用 | 什么时候用 |
|------|------|-----------|
| `list_spaces()` | 列出所有知识空间 | 查看你有哪些知识空间 |
| `create_node()` | 创建一个文档节点 | 创建新的文档或文件夹 |
| `list_all_nodes()` | 获取空间下所有节点 | 查看文档树结构 |
| `get_node()` | 获取单个节点详情 | 查看某个文档的信息 |
| `rename_node()` | 重命名节点 | 修改文档标题 |
| `create_doc_block()` | 写入内容块 | 往文档中添加内容 |
| `search_nodes()` | 搜索节点 | 按关键词查找文档 |

### 使用模式

feishu-kit 的所有 Service 都遵循一个固定模式：先创建 `FeishuClient`，再把它传给 Service 的构造函数。这叫"依赖注入"——Service 不自己创建连接，而是从外部接收一个已经配好的客户端。

```python
# 导入 FeishuClient —— 核心客户端，负责和飞书服务器通信
from feishu_kit import FeishuClient
# 导入 WikiService —— 知识库服务，封装了知识库相关的所有操作
from feishu_kit.modules.wiki import WikiService

# 创建客户端连接，传入 App ID 和 App Secret
async with FeishuClient(app_id="...", app_secret="...") as client:
    # 把 client 传给 WikiService，这样 wiki 就能用 client 来调用 API 了
    wiki = WikiService(client)   # "注入" client
    # 现在可以调用 wiki 的方法了
    spaces = await wiki.list_spaces()
```

!!! info "为什么要把 client 传给 WikiService？"
    因为一个 `FeishuClient` 实例管理着令牌刷新、连接池、重试等底层逻辑。把同一个 client 传给不同的 Service（WikiService、DriveService 等），可以共享这些资源，避免重复创建连接。这也方便你在测试时用一个假的（mock）client 替换真实 client。

---

## 2.3 用脚本批量创建文档骨架

现在到了本章最核心的部分：用一段 Python 脚本，自动在知识空间中创建完整的课程大纲结构。

> **我们接下来要做什么**：写一个脚本，按照预定义的课程大纲（章 + 节），在飞书知识库中批量创建文档。脚本会先创建"章"节点（顶层），然后在每个章下面创建"节"节点（子层）。

**第 1 步：创建脚本文件**

在你的项目目录下创建 `scripts/create_outline.py` 文件。

```python
# -*- coding: utf-8 -*-
"""
创建课程文档骨架 —— 使用 WikiService 批量创建章节和小节。

运行方式:
    python scripts/create_outline.py

前提:
    1. 已设置环境变量 FEISHU_APP_ID 和 FEISHU_APP_SECRET（Ch1 完成）
    2. 已设置环境变量 WIKU_SPACE_ID（本节第 4 步）
"""

# 导入 asyncio —— Python 异步编程模块
# 因为飞书 API 调用是异步的，所有需要 await 的代码都要在异步环境中运行
import asyncio

# 导入 os —— 操作系统模块，用来读取环境变量
import os

# 导入 FeishuClient —— feishu-kit 核心客户端
# 它负责和飞书服务器建立连接、自动管理令牌
from feishu_kit import FeishuClient

# 导入 WikiService —— 知识库服务类
# 它封装了所有知识库相关的 API 调用
from feishu_kit.modules.wiki import WikiService


# 从环境变量读取 space_id
# os.environ["XXX"] 会读取名为 XXX 的环境变量
# 如果没有设置，程序会直接报错 KeyError，提醒你先去设置
SPACE_ID = os.environ["WIKU_SPACE_ID"]

# 定义课程大纲 —— 用 Python 字典（dict）表示
# 字典的 key 是"章"的标题，value 是该章下面所有"节"的标题列表
# 你可以修改这个大纲来创建自己的课程结构
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


# 定义异步主函数 —— async def 表示这是一个异步函数
# 异步函数中可以使用 await 来等待网络请求完成
async def main():
    # 创建 FeishuClient 并建立连接
    # async with 确保用完后自动关闭连接，释放资源
    # 从环境变量读取 App ID 和 Secret
    async with FeishuClient(
        os.environ["FEISHU_APP_ID"],       # 应用的"用户名"
        os.environ["FEISHU_APP_SECRET"],   # 应用的"密码"
    ) as client:
        # 把 client 传给 WikiService，创建知识库服务实例
        wiki = WikiService(client)

        # 遍历大纲字典 —— items() 返回 (key, value) 对
        # chapter_title 是章名（如"绪论"），sections 是该章下所有小节的列表
        for chapter_title, sections in OUTLINE.items():

            # === 创建章节点（顶层节点） ===
            print(f"创建章节: {chapter_title}")

            # 调用 WikiService 的 create_node 方法创建一个新节点
            # 参数说明:
            #   SPACE_ID —— 在哪个知识空间中创建
            #   obj_type="docx" —— 创建的是飞书新版文档（docx 格式）
            #   title=chapter_title —— 文档的标题
            # 不传 parent_node_token，所以这是顶层节点
            result = await wiki.create_node(
                SPACE_ID, obj_type="docx", title=chapter_title
            )

            # 从返回结果中提取 node_token
            # result["data"]["node"] 是飞书 API 返回的节点信息
            # node_token 是这个节点在知识库树中的位置标识
            # 后续创建子节点时需要它来指定"挂在哪个父节点下面"
            parent_token = result["data"]["node"]["node_token"]
            print(f"  node_token: {parent_token}")

            # === 在章节下创建子节点（小节） ===
            for section_title in sections:
                print(f"  创建小节: {section_title}")

                # 同样调用 create_node，但这次多传了 parent_node_token
                # parent_node_token 指定"这个子节点挂在哪个父节点下面"
                # 这样就形成了 层级关系: 章 > 节
                await wiki.create_node(
                    SPACE_ID,
                    obj_type="docx",
                    title=section_title,
                    parent_node_token=parent_token,  # 指定父节点
                )

            # 每创建完一章后打印一个空行，让输出更清晰
            print()

        # 所有节点创建完成
        print("文档骨架创建完成!")


# Python 脚本的标准入口
# __name__ == "__main__" 表示"当这个文件被直接运行时"执行以下代码
# （如果被其他文件 import 则不会执行）
if __name__ == "__main__":
    # asyncio.run() —— 启动异步函数的固定写法
    # 它会创建一个事件循环，运行 main() 函数，然后关闭循环
    asyncio.run(main())
```

**第 2 步：运行脚本**

确保你已经 `source .env` 加载了环境变量，然后运行：

```bash
python scripts/create_outline.py
```

### 预期输出

终端中你会看到类似这样的输出（node_token 的值每次都不同，这是正常的）：

```
创建章节: 绪论
  node_token: FjrFwzqwbiRixckwuzncfL8TnBg
  创建小节: 1.1 具身智能的概念与内涵
  创建小节: 1.2 发展背景与研究意义
  创建小节: 1.3 与机器人、人工智能的关系
  创建小节: 1.4 具身智能操作系统
  创建小节: 1.5 学习目标与学习方法
  创建小节: 1.6 教材整体结构说明

创建章节: 第二章 感知基础
  node_token: AbcD1234eFgH5678iJkLmN0oPq
  创建小节: 2.1 视觉感知
  创建小节: 2.2 深度相机原理
  创建小节: 2.3 激光雷达与SLAM

创建章节: 第三章 运动与控制
  node_token: XyZ9876wVuT5432sRqPoNmLkJi
  创建小节: 3.1 运动学基础
  创建小节: 3.2 路径规划
  创建小节: 3.3 力控制

文档骨架创建完成!
```

> 每一行"创建小节"代表飞书 API 成功创建了一篇新文档。`node_token` 是飞书分配给每个节点的唯一标识。

### 如果你遇到了问题

| 错误信息 | 可能原因 | 解决方法 |
|---------|---------|---------|
| `KeyError: 'WIKU_SPACE_ID'` | 没有设置 WIKU_SPACE_ID 环境变量 | 运行 `export WIKU_SPACE_ID="你的space_id"` 或在 .env 中添加 |
| `API error 99991668` | 权限不足 | 回到 Ch1 确认 `wiki:wiki` 权限已开通且应用已发布 |
| `API error -1: ...` | space_id 不正确 | 检查 WIKU_SPACE_ID 是否正确，运行 `feishu-kit spaces` 确认 |
| 运行后只创建了部分节点 | 网络不稳定导致中间某次请求失败 | 删除已创建的节点，重新运行脚本 |
| `ModuleNotFoundError: No module named 'feishu_kit'` | 没有安装 feishu-kit 或没激活虚拟环境 | 运行 `pip install feishu-kit` 或激活你的虚拟环境 |

---

## 2.4 验证骨架结构

### 停下来看看

在继续之前，让我们先确认文档骨架确实创建成功了。你有两种方式验证：

### 方法一：用 CLI 查看节点树

```bash
feishu-kit nodes $WIKU_SPACE_ID
```

你会看到树形输出，就像文件管理器中的文件夹树一样：

```
7594752784659073978
├── 绪论 (docx)
│   ├── 1.1 具身智能的概念与内涵 (docx)
│   ├── 1.2 发展背景与研究意义 (docx)
│   ├── 1.3 与机器人、人工智能的关系 (docx)
│   ├── 1.4 具身智能操作系统 (docx)
│   ├── 1.5 学习目标与学习方法 (docx)
│   └── 1.6 教材整体结构说明 (docx)
├── 第二章 感知基础 (docx)
│   ├── 2.1 视觉感知 (docx)
│   ├── 2.2 深度相机原理 (docx)
│   └── 2.3 激光雷达与SLAM (docx)
└── 第三章 运动与控制 (docx)
    ├── 3.1 运动学基础 (docx)
    ├── 3.2 路径规划 (docx)
    └── 3.3 力控制 (docx)

Total: 12 nodes
```

### 方法二：在飞书 UI 中查看

打开飞书客户端，进入你创建的知识空间「具身智能导论」。你应该能看到完整的文档树结构，包含"绪论"、"第二章 感知基础"、"第三章 运动与控制"三个章节点，每个章下面有对应的小节。

点击任意一篇文档，你会发现里面是空的——这是因为我们目前只创建了"骨架"（标题和层级结构），还没有往里面填充正文内容。下一章我们将开始填充内容。

> 此时停下来确认一下：如果你在飞书 UI 中看到了完整的文档树，说明一切顺利！如果缺少某些节点，可能是网络问题导致部分创建失败，可以尝试重新运行脚本。

---

## 2.5 记录节点 Token

后续章节中，我们需要往每篇文档里填充内容。为此，我们需要知道每个文档的 **obj_token**（文档对象 ID）。

### obj_token vs node_token —— 一个关键区别

飞书知识库中每个文档有两个不同的 ID，很容易混淆。用一个生活中的比喻来理解：

> 想象一本书放在书架上。
>
> - **obj_token** 是"书的内容 ID"——就像 ISBN 编号，代表这本书本身的内容。你要**读**这本书或**改写**这本书的内容，就用 obj_token。
> - **node_token** 是"书在书架上的位置 ID"——就像"第 3 排第 5 本"这样的位置编号。你要**移动**这本书（换个位置）、**重命名**这本书、或者在这本书下面**添加子节点**，就用 node_token。

| Token | 是什么 | 用在什么操作 |
|-------|--------|-------------|
| `obj_token` | 文档对象的 ID（内容 ID） | 读/写文档内容、操作文档内部的块（block） |
| `node_token` | 文档在知识库树中的位置 ID | 创建子节点、移动、重命名、删除 |

!!! warning "不要混淆这两个 token"
    这是最常见的错误来源之一。如果你传错了 token 类型，API 会返回错误或操作错误的文档。记住：**操作内容用 obj_token，操作结构用 node_token**。

### 获取所有节点的 Token

你可以用以下代码获取知识空间中所有节点的两个 token：

```python
# 获取知识空间中所有节点
# list_all_nodes 会自动处理分页，返回一个包含所有节点的列表
nodes = await wiki.list_all_nodes(SPACE_ID)

# 遍历每个节点，打印标题和两种 token
for node in nodes:
    print(f"{node['title']}: obj={node['obj_token']}, node={node['node_token']}")
```

输出示例：

```
绪论: obj=ABC123docx001, node=FjrFwzqwbiRixckwuzncfL8TnBg
1.1 具身智能的概念与内涵: obj=ABC123docx002, node=Qrs789xyz0001
1.2 发展背景与研究意义: obj=ABC123docx003, node=Def456uvw0002
...
```

> `obj=` 后面的是文档内容 ID，后续 Ch3 填充内容时会用到。`node=` 后面的是位置 ID，创建子节点、移动节点时会用到。

---

## 小结

本章你完成了：

1. 在飞书客户端中创建了一个知识空间
2. 理解了 WikiService 的使用方式和核心方法
3. 用脚本自动创建了完整的课程文档树（3 章 12 节）
4. 在 CLI 和飞书 UI 中验证了文档骨架
5. 了解了 obj_token 和 node_token 的区别

下一章，我们将开始往这些空文档中填充内容。

---

上一章：[Ch1: 环境准备与飞书应用配置](ch01-setup.md) | 下一章：[Ch3: AI 辅助填充内容](ch03-fill-content.md)
