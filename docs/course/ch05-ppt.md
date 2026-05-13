# Ch5: 制作 PPT 课件

上一章：[Ch4: 内容审查](ch04-review.md) | 下一章：[Ch6: 学术引用](ch06-enrich.md)

---

## 本章目标

完成本章后，你将学会：

- 用 Python 自动生成 PPT 课件
- 把 PPT 上传到飞书云盘
- 把云盘中的 PPT 挂载到知识库中作为子文档

> 换句话说：完成本章后，每个小节下面都会挂一份配套的 PPT 课件。

---

## 5.1 整体流程

我们先看一下从"内容"到"PPT 挂在知识库中"需要几步：

```
第 1 步：生成 PPT 文件        → 保存到本地临时文件
第 2 步：上传到飞书云盘        → DriveService.upload_file()
第 3 步：从云盘移入知识库      → WikiService.move_docs_to_wiki()
```

这三步缺一不可。飞书知识库不能直接接收 PPT 文件——必须先上传到"云盘"，再从云盘"搬"到知识库。

---

## 5.2 安装 python-pptx

生成 PPT 文件需要 `python-pptx` 库，它是一个纯 Python 库，不需要安装 Microsoft Office。

```bash
pip install python-pptx
```

---

## 5.3 生成 PPT 文件的函数

下面这个函数接收标题和幻灯片内容，生成一个 `.pptx` 文件。每行都有注释：

```python
# 导入 python-pptx 库的核心类
from pptx import Presentation
# 导入单位换算工具（把英寸和磅转换成 PPT 内部单位）
from pptx.util import Inches, Pt


def make_ppt(title, slides_content, output_path):
    """生成一个简单的 PPT 文件。

    参数说明：
        title          -- PPT 的总标题（显示在第一页）
        slides_content -- 列表，每个元素是一个元组：(幻灯片标题, [要点1, 要点2, ...])
        output_path    -- 保存路径（比如 "/tmp/1.1.pptx"）

    使用示例：
        make_ppt("具身智能概述", [
            ("什么是具身智能", ["要点1", "要点2"]),
            ("核心特征", ["要点A", "要点B"]),
        ], "output.pptx")
    """
    # 创建一个空的 PPT 演示文稿对象
    prs = Presentation()

    # 设置幻灯片尺寸（标准 16:9 宽屏）
    prs.slide_width = Inches(13.333)   # 宽度 13.333 英寸
    prs.slide_height = Inches(7.5)     # 高度 7.5 英寸

    # ============ 制作封面页 ============
    # slide_layouts[6] 是"空白"布局——没有任何预设占位符
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # 在封面上添加一个文本框（位置：左边距1英寸，上边距2英寸，宽11英寸，高3英寸）
    txBox = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(11), Inches(3))
    tf = txBox.text_frame           # 获取文本框的文字编辑器
    p = tf.paragraphs[0]            # 获取第一个段落
    p.text = title                  # 设置文字内容
    p.font.size = Pt(44)            # 字号 44 磅（很大）
    p.font.bold = True              # 加粗

    # ============ 制作内容页 ============
    for slide_title, bullets in slides_content:
        # 创建一页新的幻灯片（空白布局）
        slide = prs.slides.add_slide(prs.slide_layouts[6])

        # 添加幻灯片标题（上方）
        txBox = slide.shapes.add_textbox(
            Inches(0.5),    # 左边距 0.5 英寸
            Inches(0.3),    # 上边距 0.3 英寸
            Inches(12),     # 宽度 12 英寸
            Inches(1),      # 高度 1 英寸
        )
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = slide_title     # 幻灯片标题文字
        p.font.size = Pt(32)     # 字号 32 磅
        p.font.bold = True       # 加粗

        # 添加要点列表（下方）
        txBox2 = slide.shapes.add_textbox(
            Inches(0.8),    # 左边距 0.8 英寸
            Inches(1.5),    # 上边距 1.5 英寸（标题下方）
            Inches(11),     # 宽度 11 英寸
            Inches(5),      # 高度 5 英寸
        )
        tf2 = txBox2.text_frame

        for i, bullet_text in enumerate(bullets):
            if i == 0:
                # 第一条要点使用已有的段落
                p = tf2.paragraphs[0]
            else:
                # 后续要点添加新段落
                p = tf2.add_paragraph()
            p.text = bullet_text      # 要点文字
            p.font.size = Pt(22)      # 字号 22 磅
            p.space_after = Pt(12)     # 段后间距 12 磅

    # 保存文件到指定路径
    prs.save(output_path)
```

---

## 5.4 上传 PPT 到飞书

PPT 生成后，需要通过 `DriveService` 上传到飞书云盘。

### 什么是 DriveService？

`DriveService` 是 feishu-kit 封装的飞书云盘服务。就像 `WikiService` 操作知识库一样，`DriveService` 操作云盘——上传文件、下载文件、列出文件等。

```python
from feishu_kit.modules.drive import DriveService


async def upload_ppt(client, wiki, drive, space_id, parent_node, file_path, file_name):
    """上传 PPT 到飞书云盘，然后移入知识库。

    参数说明：
        client       -- FeishuClient 实例
        wiki         -- WikiService 实例
        drive        -- DriveService 实例
        space_id     -- 知识空间 ID
        parent_node  -- 父节点 token（PPT 会挂在这个节点下面）
        file_path    -- 本地 PPT 文件路径
        file_name    -- 上传后的文件名

    返回：
        移入知识库的结果
    """
    # ============ 第 1 步：读取本地文件 ============
    # 以二进制模式打开文件，读取全部内容
    with open(file_path, "rb") as f:
        file_data = f.read()  # file_data 是 bytes 类型

    # ============ 第 2 步：上传到飞书云盘 ============
    # drive.upload_file() 把文件上传到云盘
    # 第一个参数是目标文件夹 token（空字符串表示根目录）
    upload_result = await drive.upload_file("", file_name, file_data)
    # 从返回结果中提取 file_token（这是文件在云盘中的 ID）
    file_token = upload_result["data"]["file_token"]

    # ============ 第 3 步：从云盘移入知识库 ============
    # wiki.move_docs_to_wiki() 把云盘中的文件"搬"到知识库中
    move_result = await wiki.move_docs_to_wiki(
        space_id=space_id,               # 目标知识空间
        parent_wiki_token=parent_node,    # 挂在哪个节点下面
        obj_token=file_token,             # 文件的 ID
        obj_type="file",                  # !! PPT 必须用 "file"
    )
    return move_result
```

!!! danger "obj_type 必须是 file"
    这是本教程最常见的踩坑点。飞书的文件类型有严格的区分：

    | 文件类型 | obj_type 值 | 说明 |
    |---------|:-----------:|------|
    | 飞书文档 | `"doc"` 或 `"docx"` | 用 `create_node()` 创建的文档 |
    | 飞书表格 | `"sheet"` | 电子表格 |
    | PPT / PDF / 图片等 | `"file"` | 必须先上传到云盘，再移入知识库 |

    如果 PPT 用了 `"doc"` 或 `"docx"`，API 会返回参数错误。

---

## 5.5 完整的批量课件生成脚本

把前面的函数组合起来，就可以批量处理所有小节：

```python
"""批量生成 PPT 课件并上传到飞书知识库。"""
import asyncio
import os
import tempfile  # 临时文件模块，用于生成临时的 .pptx 文件

from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService
from feishu_kit.modules.drive import DriveService


async def main():
    # 从环境变量读取凭证
    space_id = os.environ["WIKU_SPACE_ID"]

    async with FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    ) as client:
        wiki = WikiService(client)     # 知识库服务
        drive = DriveService(client)   # 云盘服务

        # 定义每个小节的 PPT 内容
        # 格式: (obj_token, node_token, 标题, 幻灯片内容)
        #   obj_token  -- 文档内容 ID（不需要用，但记录在这里方便管理）
        #   node_token -- 知识库节点 ID（PPT 要挂在这个节点下面）
        #   标题       -- PPT 的文件名和封面标题
        #   幻灯片内容 -- list of (幻灯片标题, [要点列表])
        sections = [
            ("obj1", "node1", "1.1 什么是具身智能", [
                ("什么是具身智能", [
                    "Embodied AI = 智能体 + 物理环境 + 持续交互",
                    "与传统AI的核心区别：拥有身体，与环境交互",
                    "感知→认知→决策→执行→感知 闭环",
                ]),
                ("核心特征", [
                    "感知—行动闭环：主动获取信息",
                    "环境交互性：在真实物理环境中实现智能",
                    "多模态感知：视觉+听觉+触觉+力觉融合",
                ]),
            ]),
            # ... 在这里添加更多小节
        ]

        # 遍历每个小节，生成 PPT 并上传
        for obj_token, node_token, title, slides in sections:
            print(f"处理: {title}")

            # --- 第 1 步：生成 PPT 到临时文件 ---
            # tempfile.NamedTemporaryFile 创建一个临时文件
            # suffix=".pptx" 确保文件扩展名正确
            # delete=False 表示不自动删除（我们需要手动控制）
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
                ppt_path = f.name  # 获取临时文件路径
            make_ppt(title, slides, ppt_path)  # 调用 5.3 节的函数

            # --- 第 2 步：上传到云盘 ---
            with open(ppt_path, "rb") as f:
                file_data = f.read()
            upload_result = await drive.upload_file("", f"{title}.pptx", file_data)
            file_token = upload_result.get("data", {}).get("file_token", "")

            # --- 第 3 步：移入知识库 ---
            if file_token:
                result = await wiki.move_docs_to_wiki(
                    space_id=space_id,
                    parent_wiki_token=node_token,
                    obj_token=file_token,
                    obj_type="file",  # !! PPT 必须是 "file"
                )
                print(f"  结果: code={result.get('code')}")

            # --- 第 4 步：清理临时文件 ---
            os.unlink(ppt_path)


if __name__ == "__main__":
    asyncio.run(main())
```

!!! tip "完整可运行示例"
    feishu-kit 的 `examples/07-course-builder/course_builder.py` 包含了一个完整的、可以直接运行的课程构建器，涵盖了骨架创建 + 内容填充 + PPT 生成 + 上传的全流程。如果你的 token 都配置好了，直接运行它就能一键构建整个课程。

---

### 如果你遇到了问题

| 现象 | 可能原因 | 解决方法 |
|------|---------|---------|
| 上传成功但知识库中看不到 PPT | `obj_type` 写错了 | 确认用的是 `"file"` 不是 `"docx"` |
| `drive.upload_file` 报错 | 没有开通 `drive:drive` 权限 | 回到 Ch1 检查权限配置 |
| `move_docs_to_wiki` 返回 forbidden | 应用没有知识库写入权限 | 检查 `wiki:wiki` 权限是否已开通并发布 |
| PPT 中文乱码 | python-pptx 默认字体不支持中文 | 在生成时指定中文字体：`p.font.name = "微软雅黑"` |

---

上一章：[Ch4: 内容审查](ch04-review.md) | 下一章：[Ch6: 学术引用](ch06-enrich.md)
