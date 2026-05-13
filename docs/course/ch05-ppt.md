# Ch5: 制作 PPT 课件

为每个小节制作配套 PPT 课件，上传到飞书云盘后移入知识库。

## 5.1 生成 PPT 文件

```python
from pptx import Presentation
from pptx.util import Inches, Pt


def make_ppt(title, slides_content, output_path):
    """生成 PPT 文件。

    Args:
        title: 课件标题（标题页）
        slides_content: list of (slide_title, [bullet_points])
        output_path: 保存路径
    """
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 标题页
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    txBox = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(11), Inches(3))
    tf = txBox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(44)
    p.font.bold = True

    # 内容页
    for slide_title, bullets in slides_content:
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        # 标题
        txBox = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12), Inches(1))
        tf = txBox.text_frame
        p = tf.paragraphs[0]
        p.text = slide_title
        p.font.size = Pt(32)
        p.font.bold = True
        # 要点
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

## 5.2 上传到云盘并移入知识库

```python
from feishu_kit.modules.drive import DriveService


async def upload_ppt(client, wiki, drive, space_id, parent_node, file_path, file_name):
    """上传 PPT 到云盘并移入知识库。"""
    # 1. 上传到云盘
    with open(file_path, "rb") as f:
        file_data = f.read()
    upload_result = await drive.upload_file("", file_name, file_data)
    file_token = upload_result["data"]["file_token"]

    # 2. 移入知识库
    move_result = await wiki.move_docs_to_wiki(
        space_id=space_id,
        parent_wiki_token=parent_node,
        obj_token=file_token,
        obj_type="file",  # PPT 用 "file"
    )
    return move_result
```

!!! warning "obj_type 必须是 file"
    PPT 不是 `"doc"` 类型，必须使用 `obj_type="file"`，否则 API 会返回参数错误。

## 5.3 完整的课件生成脚本

```python
"""为所有小节批量生成 PPT 并上传。"""
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
        sections = [
            ("obj1", "node1", "1.1 什么是具身智能", [
                ("什么是具身智能", [
                    "Embodied AI = 智能体 + 物理环境 + 持续交互",
                    "与传统AI的核心区别：拥有身体，与环境交互",
                ]),
                ("核心特征", [
                    "感知—行动闭环",
                    "环境交互性",
                    "多模态感知",
                ]),
            ]),
            # ... 添加更多小节
        ]

        for obj_token, node_token, title, slides in sections:
            # 生成 PPT
            with tempfile.NamedTemporaryFile(suffix=".pptx", delete=False) as f:
                ppt_path = f.name
            make_ppt(title, slides, ppt_path)

            # 上传
            with open(ppt_path, "rb") as f:
                file_data = f.read()
            upload_result = await drive.upload_file("", f"{title}.pptx", file_data)
            file_token = upload_result.get("data", {}).get("file_token", "")

            # 移入知识库
            if file_token:
                result = await wiki.move_docs_to_wiki(
                    space_id=space_id,
                    parent_wiki_token=node_token,
                    obj_token=file_token,
                    obj_type="file",
                )
                print(f"{title}: code={result.get('code')}")

            os.unlink(ppt_path)


if __name__ == "__main__":
    asyncio.run(main())
```

---

上一章：[Ch4: 内容审查](ch04-review.md) | 下一章：[Ch6: 内容扩充与引用](ch06-enrich.md)
