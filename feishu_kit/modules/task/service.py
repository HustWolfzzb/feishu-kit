"""任务服务 — 封装飞书 Task API"""


class TaskService:
    def __init__(self, client):
        self._client = client

    # ── 任务 ────────────────────────────────────────────────────────
    async def list_tasks(self, page_size: int = 20) -> dict:
        return await self._client.request(
            "GET", "/task/v1/tasks", params={"page_size": str(page_size)},
        )

    async def get_task(self, task_id: str) -> dict:
        return await self._client.request("GET", f"/task/v2/tasks/{task_id}")

    async def create_task(self, task: dict) -> dict:
        return await self._client.request("POST", "/task/v2/tasks", json=task)

    async def update_task(self, task_id: str, task: dict) -> dict:
        return await self._client.request(
            "PATCH", f"/task/v2/tasks/{task_id}", json=task,
        )

    async def delete_task(self, task_id: str) -> dict:
        return await self._client.request("DELETE", f"/task/v2/tasks/{task_id}")

    async def complete_task(self, task_id: str) -> dict:
        return await self._client.request(
            "PATCH", f"/task/v2/tasks/{task_id}", json={"status": "done"},
        )

    async def add_members(
        self, task_id: str, members: list[dict], *,
        user_id_type: str = "open_id",
    ) -> dict:
        """添加任务成员（v2）。

        members 格式: [{"id": "ou_xxx", "type": "user", "role": "assignee"}]
        role 可选: assignee（负责人）, follower（关注人）
        """
        return await self._client.request(
            "POST", f"/task/v2/tasks/{task_id}/add_members",
            params={"user_id_type": user_id_type},
            json={"members": members},
        )

    # ── 任务评论 ──────────────────────────────────────────────────
    async def list_comments(self, task_id: str) -> dict:
        return await self._client.request(
            "GET", f"/task/v2/tasks/{task_id}/comments",
        )

    async def add_comment(self, task_id: str, content: str) -> dict:
        return await self._client.request(
            "POST", f"/task/v2/tasks/{task_id}/comments",
            json={"content": content},
        )
