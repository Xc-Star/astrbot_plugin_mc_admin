import asyncio

from wireup import injectable

from astrbot.core import logger

from ..command.helpers import (
    get_whitelist,
    send_command,
)
from ..config_utils import ConfigUtils
from ..config_utils.container import get_service
from ..db.main import DbUtils
from ..http import AsyncHttpClient

# 常量定义
MOJANG_PROFILES_API = "https://api.mojang.com/profiles/minecraft"
MOJANG_USER_API = "https://api.mojang.com/users/profiles/minecraft"
BATCH_SIZE = 10
REQUEST_TIMEOUT = 10


@injectable
class WhitelistUtils:
    def __init__(self):
        db_util = get_service(DbUtils)
        self.conn = db_util.get_conn()
        self.config_utils = get_service(ConfigUtils)
        self.servers = self.config_utils.get_server_list()
        self.bot_prefix = self.config_utils.get_bot_prefix()
        self.http = get_service(AsyncHttpClient)

        # 查询user_profile表是否有数据
        if self._is_database_empty():
            asyncio.create_task(self.initialize())

    async def initialize(self):
        """初始化白名单数据"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM user_profile")

            # 获取服务器内白名单
            whitelist = await get_whitelist(self.config_utils)
            if len(whitelist) == 0:
                self.conn.commit()
                logger.info("白名单为空，跳过初始化")
                return

            # 批量获取UUID
            response_data_list = []
            for i in range(0, len(whitelist), BATCH_SIZE):
                batch_usernames = whitelist[i : i + BATCH_SIZE]
                batch_data = await self._fetch_uuid_batch(batch_usernames)
                response_data_list.extend(batch_data)

            # 结果转为 name -> uuid 映射
            resp_mapping = {
                data.get("name"): data.get("id")
                for data in response_data_list
                if data and data.get("name") and data.get("id")
            }

            # 保存有UUID的用户
            remaining = set(whitelist)
            for username, uuid in resp_mapping.items():
                if username in remaining:
                    cursor.execute(
                        "INSERT INTO user_profile (uuid, username) VALUES (?, ?)",
                        (uuid, username),
                    )
                    remaining.discard(username)

            # 保存没有UUID的用户（仅用户名）
            for username in remaining:
                cursor.execute(
                    "INSERT INTO user_profile (username) VALUES (?)", (username,)
                )

            self.conn.commit()
        except Exception as e:
            logger.error(f"初始化白名单失败: {e}")
            self.conn.rollback()

    # ==================== 数据库辅助方法 ====================

    async def close(self):
        await self.http.close()

    def _is_database_empty(self) -> bool:
        """检查数据库白名单是否为空"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_profile")
        return cursor.fetchone()[0] == 0

    def _user_exists_in_db(self, username: str) -> bool:
        """检查用户名是否在数据库中"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM user_profile WHERE username = ?", (username,)
        )
        return cursor.fetchone()[0] > 0

    def _uuid_exists_in_db(self, uuid: str) -> bool:
        """检查UUID是否在数据库中"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_profile WHERE uuid = ?", (uuid,))
        return cursor.fetchone()[0] > 0

    def _get_user_by_uuid(self, uuid: str) -> str | None:
        """根据UUID查询用户"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM user_profile WHERE uuid = ?", (uuid,))
        res = cursor.fetchone()
        return res[1] if res else None

    def _insert_user(self, uuid: str, username: str) -> None:
        """插入用户到数据库"""
        cursor = self.conn.cursor()
        if uuid:
            cursor.execute(
                "INSERT INTO user_profile (uuid, username) VALUES (?, ?)",
                (uuid, username),
            )
        else:
            cursor.execute(
                "INSERT INTO user_profile (username) VALUES (?)", (username,)
            )
        self.conn.commit()

    def _update_username(self, uuid: str, username: str) -> None:
        """更新用户名"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE user_profile SET username = ? WHERE uuid = ?", (username, uuid)
        )
        self.conn.commit()

    def _update_user_by_history(
        self, uuid: str, username: str, old_username: str
    ) -> None:
        """通过历史用户名更新用户信息"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE user_profile SET username = ?, uuid = ? WHERE username = ?",
            (username, uuid, old_username),
        )
        self.conn.commit()

    def _delete_user(self, username: str) -> None:
        """从数据库删除用户"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM user_profile WHERE username = ?", (username,))
        self.conn.commit()

    # ==================== API 调用辅助方法 ====================

    async def _fetch_uuid_batch(self, usernames: list[str]) -> list[dict]:
        """批量获取UUID API"""
        try:
            data = await self.http.post_json(MOJANG_PROFILES_API, json=usernames)
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.error(f"批量获取 UUID 失败: {e},\r username: {usernames}")
            return []

    async def _fetch_uuid_by_username(self, username: str) -> str | None:
        """根据用户名获取UUID API"""
        try:
            data = await self.http.get_json(f"{MOJANG_USER_API}/{username}")
            if data.get("errorMessage"):
                return None
            return data.get("id")
        except Exception as e:
            logger.error(f"查询 {username} UUID 报错: {e}")
            return None

    def _is_bot_prefix(self, username: str) -> bool:
        """检查是否为假人前缀"""
        return (
            len(username) > len(self.bot_prefix)
            and username[: len(self.bot_prefix)] == self.bot_prefix
        )

    async def _sync_whitelist_user_to_db(self, username: str) -> bool:
        """同步白名单中的用户到数据库"""
        uuid = await self._fetch_uuid_by_username(username)
        if uuid:
            self._insert_user(uuid, username)
            return True
        return False

    async def _verify_by_uuid(self, username: str) -> bool:
        """通过UUID验证用户"""
        uuid = await self._fetch_uuid_by_username(username)
        if not uuid:
            return False

        # 检查UUID是否已存在数据库
        user = self._get_user_by_uuid(uuid)
        if user:
            # 更新用户名
            self._update_username(uuid, username)
            return True

        return False

    async def is_real_player(self, username: str) -> bool:
        """验证是否为真人"""
        # 检查是否为机器人用户名
        if self._is_bot_prefix(username):
            return False

        # 检查数据库中是否存在
        if self._user_exists_in_db(username):
            return True

        # 检查服务器白名单（防止在游戏内添加白名单，没有存在数据库里）
        whitelist_list = await get_whitelist(self.config_utils)
        if username in whitelist_list:
            if await self._sync_whitelist_user_to_db(username):
                return True

        # 通过UUID验证
        if await self._verify_by_uuid(username):
            return True

        return False

        # TODO: 通过历史用户名验证 API 挂了 下次一定

    async def _execute_whitelist_command(self, operation: str, username: str) -> None:
        """在所有服务器上执行白名单命令"""

        async def do_op(server_name: str):
            try:
                await send_command(
                    self.config_utils, server_name, f"whitelist {operation} {username}"
                )
            except Exception:
                logger.warning(
                    f"在服务器 {server_name} 上执行白名单命令失败: {operation} {username}"
                )

        # 异步发送白名单命令
        await asyncio.gather(
            *[do_op(s) for s in await self.config_utils.get_online_servers_name()],
            return_exceptions=True,
        )

    async def _add_user_to_whitelist(self, username: str) -> tuple[bool, str]:
        """添加用户到白名单"""
        # 获取UUID
        uuid = await self._fetch_uuid_by_username(username)
        if not uuid:
            return False, "没查到UUID喵~"
        # 检查是否已存在
        if self._uuid_exists_in_db(uuid):
            return False, "该玩家已在白名单中喵~"
        # 添加到数据库
        self._insert_user(uuid, username)
        return True, f"已将{username}添加到白名单喵~"

    async def _remove_user_from_whitelist(self, username: str) -> tuple[bool, str]:
        """从白名单移除用户"""
        self._delete_user(username)
        return True, f"已将{username}移除白名单喵~"

    async def operation_whitelist(self, operation: str, username: str) -> str:
        """处理白名单添加/移除操作"""
        success, msg = False, ""
        # 根据操作类型处理数据库
        if operation == "add":
            success, msg = await self._add_user_to_whitelist(username)
        elif operation == "remove":
            success, msg = await self._remove_user_from_whitelist(username)
        # 在所有服务器上执行命令
        if success:
            await self._execute_whitelist_command(operation, username)
            return msg
        else:
            return msg
