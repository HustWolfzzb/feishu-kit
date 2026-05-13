# Ch4: 内容审查与修正

上一章：[Ch3: 填充内容](ch03-fill-content.md) | 下一章：[Ch5: PPT 课件](ch05-ppt.md)

---

## 本章目标

完成本章后，你将学会：

- 查看已写入飞书文档的内容
- 识别 AI 生成内容的常见问题
- 使用 Claude 进行内容审查
- 向文档追加修正内容
- 处理常见的 API 错误

> 换句话说：完成本章后，你的课程内容将更加准确、自然、专业。

---

## 4.1 为什么要审查？

AI 生成的内容看起来很通顺，但常常暗藏问题：

- **事实错误**：AI 可能编造不存在的论文或数据
- **逻辑矛盾**：前后段落说的不一致
- **AI 味道**：大量使用「值得注意的是」「总而言之」等套话
- **引用不准**：论文名字对了但年份错了，或作者张冠李戴

!!! warning "AI 生成的内容必须审查"
    即使看起来很专业，也一定要逐段检查。特别是论文引用和数据——AI 经常"一本正经地胡说八道"。

---

## 4.2 查看已写入的内容

### 方法一：CLI 命令（最简单）

```bash
# 查看文档内容，obj_token 替换成你的文档 ID
feishu-kit inspect B16Bdn0vqopi8XxQaERcZPdenHd
```

输出是格式化的 JSON，你会看到每个块的完整结构：

```json
{
  "block_type": 4,
  "heading2": {
    "elements": [{"text_run": {"content": "什么是具身智能", ...}}]
  }
}
```

### 方法二：Python 代码

```python
"""查看飞书文档内容。"""
import asyncio
import os

from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService

# 替换成你的文档 ID
OBJ_TOKEN = "B16Bdn0vqopi8XxQaERcZPdenHd"


async def main():
    async with FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    ) as client:
        wiki = WikiService(client)

        # 获取文档原始内容（返回纯文本）
        raw = await wiki.get_doc_raw_content(OBJ_TOKEN)

        # 从返回结果中提取文本内容
        content = raw.get("data", {}).get("content", "")

        # 打印内容和字符数
        print(content)
        print(f"\n--- 共 {len(content)} 个字符 ---")


asyncio.run(main())
```

### 方法三：直接在飞书中查看

最直观的方式——打开飞书客户端或网页版，找到对应文档，像阅读普通文档一样查看。这是检查排版效果最好的方式。

---

## 4.3 识别常见问题

### 什么是「AI 味道」？

下面是一个有 AI 味道的例子：

> ❌ **值得注意的是**，具身智能在近年来**毫无疑问**地成为了人工智能领域的重要研究方向。**总而言之**，这一领域的未来发展前景**令人振奋**。

修正后：

> ✅ 具身智能在 2023 年迎来了爆发期，Google RT-2、Tesla Optimus 等系统的出现标志着技术从实验室走向应用。

**区别在哪？**

| AI 味道特征 | 修正方法 |
|-----------|---------|
| 大量使用「值得注意的是」「毋庸置疑」 | 删除套话，直接说事 |
| 空洞的总结（"前景令人振奋"） | 换成具体数据或案例 |
| 过度使用加粗强调 | 只对关键术语加粗 |
| 段落长度几乎一样 | 变化段落长短，有节奏感 |
| 每段都是「首先...其次...最后...」 | 用更自然的过渡 |

### 审查清单

检查每个小节时，逐项确认：

- [ ] 没有编造的论文引用（检查每篇引用是否真实存在）
- [ ] 数据有出处（比如"市场规模达 XX 亿"要有来源）
- [ ] 没有自相矛盾的论述
- [ ] 没有 AI 套话（在文档中搜索「值得注意」「毋庸置疑」「令人振奋」）
- [ ] 加粗只用于关键术语，不是每段都加粗
- [ ] 段落间有自然过渡，不是突然跳转

---

## 4.4 用 Claude 进行内容审查

### 怎么做？

在 Claude Code 中输入：

```
请检查我刚才填充到 1.1 小节的内容，要求：
1. 去除AI味道（避免大量重复废话、过度热情的语气）
2. 检查每小节前后逻辑，避免前后不一致
3. 确保内容连贯性
4. 引用的论文和年份要准确

文档 obj_token: B16Bdn0vqopi8XxQaERcZPdenHd
```

Claude 会分析内容并指出问题，然后生成修正脚本。

### 审查提示词模板

你可以根据需要调整重点：

```
请帮我审查飞书文档中的课程内容，重点关注：

[  ] 论文引用是否准确（标题、作者、年份、期刊）
[ ] 数据是否有出处
[ ] 是否有AI生成的套话
[ ] 逻辑是否连贯

文档 obj_token: _______
```

---

## 4.5 向文档追加内容

飞书 API 的一个限制：**不能删除或修改已写入的块，只能追加新内容**。

所以修正内容的策略是：**在文档末尾追加修正内容**。

```python
"""向文档追加修正内容。"""
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

        # 追加的内容块
        new_blocks = [
            heading2("补充说明"),
            text("经过审查，对上文做以下补充和修正："),
            bullet(t("第 3 段的数据引用有误"), t("，正确数据来自 MarketsandMarkets 2024 年报告")),
            bullet(t("参考文献第 2 条年份应为 2006"), t("，非 2007 年")),
        ]

        # index=-1 表示追加到文档末尾
        result = await wiki.create_doc_block(
            OBJ_TOKEN,   # 文档 ID
            OBJ_TOKEN,   # 父块 ID（文档自身）
            new_blocks,  # 新内容块
            index=-1,    # 追加到末尾
        )
        print(f"追加结果: code={result.get('code')}")


asyncio.run(main())
```

!!! warning "如果问题太多怎么办？"
    如果一个文档的问题非常多，追加修正块会让文档变得混乱。这时候建议**删除文档重建**：

    1. 在飞书客户端中手动删除这个文档
    2. 用 `wiki.create_node()` 重新创建
    3. 写入修正后的完整内容

    飞书 API 目前不支持删除知识库节点，所以需要手动操作。

---

## 4.6 处理 API 错误

feishu-kit 提供了几种自定义异常，帮你区分不同类型的错误：

```python
from feishu_kit.core.exceptions import (
    FeishuKitError,        # 所有错误的基类
    AuthenticationError,   # 凭证错误（App ID/Secret 不对）
    RateLimitError,        # 请求太频繁（被限流了）
    APIError,              # 飞书 API 返回的错误
)


async def safe_write(wiki, obj_token, blocks):
    """安全写入内容，自动处理常见错误。"""
    try:
        # 尝试写入
        result = await wiki.create_doc_block(obj_token, obj_token, blocks)
        print(f"  写入成功: {len(blocks)} 个块")
        return result

    except AuthenticationError:
        # 凭证错误 —— 检查环境变量
        print("  ✗ 凭证无效！请检查 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        return None

    except RateLimitError as e:
        # 限流 —— 等一会儿再试
        print(f"  ⚠ 触发限流，需要等 {e.retry_after} 秒")
        return None

    except APIError as e:
        # API 错误 —— 根据错误码判断问题
        print(f"  ✗ API 错误 code={e.code}: {e.msg}")
        if e.code == 99991672:
            print("    文档不存在，检查 obj_token 是否正确")
        elif "invalid" in e.msg:
            print("    参数格式错误，检查是否有空内容块")
        return None
```

!!! info "feishu-kit 内置了自动重试"
    你不需要自己写重试逻辑。FeishuClient 在遇到 429（限流）和 5xx（服务器错误）时会自动重试最多 3 次，每次等待时间翻倍（1 秒、2 秒、4 秒）。只有 3 次都失败后才会抛出 `RateLimitError`。

---

## 审查工作流总结

```
1. 用 CLI 或 Python 查看文档内容
2. 用审查清单逐项检查
3. 发现问题 → 让 Claude 生成修正脚本
4. 运行脚本追加修正内容
5. 再次检查确认
```

---

上一章：[Ch3: 填充内容](ch03-fill-content.md) | 下一章：[Ch5: PPT 课件](ch05-ppt.md)
