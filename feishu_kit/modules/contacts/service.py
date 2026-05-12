"""通讯录服务 — 封装飞书 Contacts 全部 API"""


class ContactsService:
    def __init__(self, client):
        self._client = client

    # ── 用户 ────────────────────────────────────────────────────────
    async def get_user(self, user_id: str, user_id_type: str = "open_id") -> dict:
        """获取用户信息。"""
        return await self._client.request(
            "GET",
            f"/contact/v3/users/{user_id}",
            params={"user_id_type": user_id_type},
        )

    async def list_users(
        self,
        department_id: str = "0",
        department_id_type: str = "open_department_id",
        user_id_type: str = "open_id",
        page_size: int = 50,
        page_token: str | None = None,
    ) -> dict:
        """获取部门直属用户列表。"""
        params: dict = {
            "department_id_type": department_id_type,
            "user_id_type": user_id_type,
            "page_size": str(page_size),
            "department_id": department_id,
        }
        if page_token:
            params["page_token"] = page_token
        return await self._client.request("GET", "/contact/v3/users", params=params)

    async def batch_get_user_id(
        self, mobiles: list[str] | None = None, emails: list[str] | None = None,
    ) -> dict:
        """通过手机号或邮箱批量获取用户 ID。"""
        body: dict = {}
        if mobiles:
            body["mobiles"] = mobiles
        if emails:
            body["emails"] = emails
        return await self._client.request(
            "POST", "/contact/v3/users/batch_get_id", json=body,
        )

    # ── 部门 ────────────────────────────────────────────────────────
    async def list_departments(
        self, parent_department_id: str = "0", page_size: int = 20,
        department_id_type: str = "open_department_id", fetch_child: bool = False,
    ) -> dict:
        """获取子部门列表。"""
        return await self._client.request(
            "GET",
            f"/contact/v3/departments/{parent_department_id}",
            params={
                "department_id_type": department_id_type,
                "fetch_child": str(fetch_child).lower(),
                "page_size": str(page_size),
            },
        )

    async def get_department_sub_departments(
        self, parent_department_id: str = "0", page_size: int = 20,
        department_id_type: str = "open_department_id",
    ) -> dict:
        """获取子部门列表 — 使用 list 接口。"""
        return await self._client.request(
            "GET",
            "/contact/v3/departments",
            params={
                "parent_department_id": parent_department_id,
                "department_id_type": department_id_type,
                "fetch_child": "false",
                "page_size": str(page_size),
            },
        )

    async def get_department(
        self, department_id: str, department_id_type: str = "open_department_id",
    ) -> dict:
        """获取部门详情。"""
        return await self._client.request(
            "GET",
            f"/contact/v3/departments/{department_id}",
            params={"department_id_type": department_id_type},
        )

    # ── 用户组 ──────────────────────────────────────────────────────
    async def list_group_members(
        self, group_id: str, page_size: int = 20,
    ) -> dict:
        """获取用户组成员列表。"""
        return await self._client.request(
            "GET", "/contact/v3/group/list",
            params={"group_id": group_id, "page_size": str(page_size)},
        )

    # ── 角色管理 ────────────────────────────────────────────────────
    async def list_roles(self) -> dict:
        """获取角色列表。"""
        return await self._client.request("GET", "/contact/v3/roles")
