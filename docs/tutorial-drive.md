# Drive Tutorial — File Upload and Management

This tutorial covers the `DriveService` module for managing files in Feishu cloud drive.

## Setup

```python
from feishu_kit import FeishuClient
from feishu_kit.modules.drive import DriveService

client = FeishuClient(app_id="...", app_secret="...")
drive = DriveService(client)
```

## 1. List Files

```python
result = await drive.list_files("folder_token")
for f in result.get("data", {}).get("files", []):
    print(f"{f['name']} — type={f['type']} token={f['token']}")
```

## 2. Upload a File

```python
with open("report.pdf", "rb") as f:
    file_data = f.read()

result = await drive.upload_file(
    folder_token="target_folder_token",
    file_name="report.pdf",
    file_data=file_data,
)
file_token = result.get("data", {}).get("file_token")
print(f"Uploaded: {file_token}")
```

## 3. Download a File

```python
result = await drive.download("file_token")
# result contains a temporary download URL
```

## 4. Create a Folder

```python
result = await drive.create_folder("parent_folder_token", "New Folder")
folder_token = result.get("data", {}).get("token")
```

## 5. Manage Permissions

```python
# List who has access
members = await drive.list_file_members("file_token")

# Grant access
await drive.add_file_member(
    "file_token",
    member_type="openid",
    member_id="ou_xxx",
    perm="full_access",
)
```

## 6. Upload + Move to Wiki (Complete Workflow)

```python
from feishu_kit.modules.wiki import WikiService

wiki = WikiService(client)

# Upload to Drive
result = await drive.upload_file("", "slides.pptx", pptx_bytes)
file_token = result["data"]["file_token"]

# Move into Wiki
await wiki.move_docs_to_wiki(
    space_id="space_id",
    parent_wiki_token="parent_node",
    obj_token=file_token,
    obj_type="file",
)
```

## Cleanup

```python
await client.close()
```

## Next: [Messaging Tutorial](tutorial-messaging.md)
