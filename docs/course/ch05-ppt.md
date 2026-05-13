# Ch5: 制作 PPT 课件

为每个小节制作配套 PPT 课件，通过 `DriveService` 上传到云盘后移入知识库。

## 5.1 整体流程

```
内容块 → 提取要点 → python-pptx 生成 PPT → DriveService 上传 → WikiService 移入知识库
```

这个完整流程在 feishu-kit 的 `examples/07-course-builder/course_builder.py` 中有可运行的示例。

## 5.2 生成 PPT 文件

使用 `python-pptx` 库生成 PPT：

```python
from pptx import Presentation
from pptx.util import Inches, Pt


def make_ppt(title, slides_content, output_path):
    """生成 PPT 文件。

    Args:
        title: 课件标题（标题页显示）
        slides_content: list of (slide_title, [bullet_points])
        output_path: 保存路径
    """
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 标题页
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout
    txBox = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(11), Inches(3))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(44)
    p.font.bold = True

    # 内容页
    for slide_title, bullets in slides_content:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        # 幻灯片标题
        txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12), Inches(1))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = slide_title
        p.font.size = Pt(32)
        p.font.bold = True
        # 要点列表
        txBox2 = slide.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11), Inches(5))
        tf2 = txBox2.text_frame
        for i, bullet in enumerate(bullets):
            if i == 0:
                p = tf2.paragraphs[0]
            else:
                p = tf2.add_paragraph()
            p.text = bullet
            p.font.size = Pt(22)
            p.space_after = Pt(12)

    prs.save(output_path)
```

## 5.3 上传到云盘并移入知识库

这里需要两个 Service 配合：`DriveService` 负责上传，`WikiService` 负责移入知识库。

```python
from feishu_kit.modules.drive import DriveService
from feishu_kit.modules.wiki import WikiService


async def upload_ppt(client, wiki, drive, space_id, parent_node, file_path, file_name):
    """上传 PPT 到云盘并移入知识库。"""
    # Step 1: 上传到飞书云盘
    with open(file_path, "rb") as f:
        file_data = f.read()
    upload_result = await drive.upload_file("", file_name, file_data)
    file_token = upload_result["data"]["file_token"]

    # Step 2: 从云盘移入知识库（作为子节点挂载）
    move_result = await wiki.move_docs_to_wiki(
        space_id=space_id,
        parent_wiki_token=parent_node,
        obj_token=file_token,
        obj_type="file",  # !! PPT 必须用 "file"，不能用 "doc"
    )
    return move_result
```

!!! danger "obj_type 必须是 file"
    PPT 不是 `"doc"` 类型，必须使用 `obj_type="file"`。这是一个常见的踩坑点，用错了会返回参数错误。飞书的文件类型映射：
    - 文档 → `"doc"` 或 `"docx"`
    - 表格 → `"sheet"`
    - 文件（PPT/PDF/图片等） → `"file"`

### DriveService 方法概览

| 方法 | 用途 |
|------|------|
| `upload_file(folder_token, name, data)` | 上传文件到云盘 |
| `download(file_token)` | 下载文件 |
| `list_files(folder_token)` | 列出文件夹内容 |
| `create_folder(name, parent_token)` | 创建文件夹 |

## 5.4 完整的批量课件生成脚本

```python
"""为所有小节批量生成 PPT 并上传到知识库。"""
import asyncio
import os
import tempfile

from feishu_kit import FeishuClient
from feishu_kit.modules.wiki import WikiService
from feishu_kit.modules.drive import DriveService


async def main():
    space_id = os.environ["WIKU_SPACE_ID"]

    async with FeishuClient(
        os.environ["FEISHU_APP_ID"],
        os.environ["FEISHU_APP_SECRET"],
    ) as client:
        wiki = WikiService(client)
        drive = DriveService(client)

        # 每个小节: (obj_token, node_token, title, slides)
        # obj_token: 文档内容 ID
        # node_token: 知识库树中的位置 ID（PPT 挂载到这个节点下）
        sections = [
            ("obj1", "node1", "1.1 什么是具身智能", [
                ("什么是具身智能", [
                    "Embodied AI = 智能体 + 物理环境 + 持续交互",
                    "与传统AI的核心区别：拥有身体，与环境交互",
                    "感知→认知→决策→执行→感知 闭环",
                ]),
                ("核心特征", [
                    "感知—行动闭环：主动获取信息而非被动接收",
                    "环境交互性：在真实物理环境中实现智能",
                    "多模态感知：视觉+听觉+触觉+力觉融合",
                ]),
            ]),
            # ... 添加更多小节
        ]

        for obj_token, node_token, title, slides in sections:
            # 1. 生成 PPT 到临时文件
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
                ppt_path = f.name
            make_ppt(title, slides, ppt_path)

            # 2. 上传到云盘
            with open(ppt_path, "rb") as f:
                file_data = f.read()
            upload_result = await drive.upload_file("", f"{title}.pptx", file_data)
            file_token = upload_result.get("data", {}).get("file_token", "")

            # 3. 移入知识库
            if file_token:
                result = await wiki.move_docs_to_wiki(
                    space_id=space_id,
                    parent_wiki_token=node_token,
                    obj_token=file_token,
                    obj_type="file",
                )
                print(f"  {title}: code={result.get('code')}")

            # 4. 清理临时文件
            os.unlink(ppt_path)


if __name__ == "__main__":
    asyncio.run(main())
```

!!! tip "完整示例"
    feishu-kit 的 `examples/07-course-builder/course_builder.py` 包含了一个完整的、可运行的课程构建器，涵盖了骨架创建 + 内容填充 + PPT 生成 + 上传全流程。

---

上一章：[Ch4: 内容审查](ch04-review.md) | 下一章：[Ch6: 内容扩充与引用](ch06-enrich.md)
