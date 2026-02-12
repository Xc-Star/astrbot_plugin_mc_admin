import sqlite3
from typing import Tuple, Dict, Optional

import aiohttp
import asyncio

from astrbot.core import logger
from ..command.helpers import (
    get_whitelist, send_command,
)

# 常量定义
MOJANG_PROFILES_API = "https://api.mojang.com/profiles/minecraft"
MOJANG_USER_API = "https://api.mojang.com/users/profiles/minecraft"
HISTORY_ID_API = "https://uapis.cn//api/v1/game/minecraft/historyid"
BATCH_SIZE = 10
REQUEST_TIMEOUT = 10


class WhitelistUtils:

    def __init__(self, conn: sqlite3.Connection, servers: list[dict], bot_prefix: str):
        self.conn = conn
        self.servers = servers
        self.bot_prefix = bot_prefix
        
        # 查询user_profile表是否有数据
        if self._is_database_empty():
            asyncio.create_task(self.initialize())

    # ==================== 数据库辅助方法 ====================
    
    def _is_database_empty(self) -> bool:
        """检查数据库是否为空"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_profile")
        return cursor.fetchone()[0] == 0
    
    def _user_exists_in_db(self, username: str) -> bool:
        """检查用户名是否在数据库中"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_profile WHERE username = ?", (username,))
        return cursor.fetchone()[0] > 0
    
    def _uuid_exists_in_db(self, uuid: str) -> bool:
        """检查UUID是否在数据库中"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM user_profile WHERE uuid = ?", (uuid,))
        return cursor.fetchone()[0] > 0
    
    def _get_user_by_uuid(self, uuid: str) -> Optional[tuple]:
        """根据UUID查询用户"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM user_profile WHERE uuid = ?", (uuid,))
        return cursor.fetchone()
    
    def _insert_user(self, uuid: Optional[str], username: str) -> None:
        """插入用户到数据库"""
        cursor = self.conn.cursor()
        if uuid:
            cursor.execute("INSERT INTO user_profile (uuid, username) VALUES (?, ?)", (uuid, username))
        else:
            cursor.execute("INSERT INTO user_profile (username) VALUES (?)", (username,))
        self.conn.commit()
    
    def _update_username(self, uuid: str, username: str) -> None:
        """更新用户名"""
        cursor = self.conn.cursor()
        cursor.execute("UPDATE user_profile SET username = ? WHERE uuid = ?", (username, uuid))
        self.conn.commit()
    
    def _update_user_by_history(self, uuid: str, username: str, old_username: str) -> None:
        """通过历史用户名更新用户信息"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE user_profile SET username = ?, uuid = ? WHERE username = ?",
            (username, uuid, old_username)
        )
        self.conn.commit()
    
    def _delete_user(self, username: str) -> None:
        """从数据库删除用户"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM user_profile WHERE username = ?", (username,))
        self.conn.commit()
    
    # ==================== API 调用辅助方法 ====================
    
    async def _fetch_uuid_batch(self, usernames: list[str]) -> list[dict]:
        """批量获取UUID"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    MOJANG_PROFILES_API,
                    json=usernames,
                    timeout=REQUEST_TIMEOUT
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data if isinstance(data, list) else []
                    else:
                        logger.warning(f"获取 UUID 失败，状态码: {response.status}, 批次: {usernames}")
                        return []
            except Exception as e:
                logger.error(f"请求 UUID 接口失败: {e}, 批次: {usernames}")
                return []
    
    async def _fetch_uuid_by_username(self, username: str) -> Optional[dict]:
        """根据用户名获取UUID"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{MOJANG_USER_API}/{username}",
                    timeout=REQUEST_TIMEOUT
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("errorMessage"):
                            return None
                        return data
                    return None
            except Exception as e:
                logger.error(f"获取用户 UUID 失败: {e}, 用户名: {username}")
                return None
    
    async def _fetch_history_names(self, uuid: str) -> Optional[dict]:
        """获取历史用户名"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    f"{HISTORY_ID_API}?uuid={uuid}",
                    timeout=REQUEST_TIMEOUT
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    return None
            except Exception as e:
                logger.error(f"获取历史用户名失败: {e}, UUID: {uuid}")
                return None
    
    # ==================== 业务逻辑方法 ====================
    
    async def initialize(self):
        """初始化白名单数据"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM user_profile")

            # 获取服务器内白名单
            whitelist = await get_whitelist(self.servers)
            if len(whitelist) == 0:
                self.conn.commit()
                logger.info("白名单为空，跳过初始化")
                return

            # 批量获取UUID
            response_data_list = []
            for i in range(0, len(whitelist), BATCH_SIZE):
                batch_usernames = whitelist[i:i + BATCH_SIZE]
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
                        (uuid, username)
                    )
                    remaining.discard(username)

            # 保存没有UUID的用户（仅用户名）
            for username in remaining:
                cursor.execute("INSERT INTO user_profile (username) VALUES (?)", (username,))

            self.conn.commit()
        except Exception as e:
            logger.error(f"初始化白名单失败: {e}")
            self.conn.rollback()

    def _is_bot_username(self, username: str) -> bool:
        """检查是否为机器人用户名（根据前缀判断）"""
        return len(username) > len(self.bot_prefix) and username[:len(self.bot_prefix)] == self.bot_prefix
    
    async def _sync_whitelist_user_to_db(self, username: str) -> bool:
        """同步白名单中的用户到数据库"""
        data = await self._fetch_uuid_by_username(username)
        if data and data.get("id"):
            self._insert_user(data.get("id"), username)
            return True
        return False
    
    async def _verify_by_uuid(self, username: str) -> bool:
        """通过UUID验证用户"""
        data = await self._fetch_uuid_by_username(username)
        if not data or not data.get("id"):
            return False
        
        uuid = data.get("id")
        # 检查UUID是否已存在数据库
        existing_user = self._get_user_by_uuid(uuid)
        if existing_user:
            # 更新用户名
            self._update_username(uuid, data.get("name"))
            return True
        
        return False
    
    async def _verify_by_history_names(self, username: str) -> bool:
        """通过历史用户名验证用户"""
        data = await self._fetch_uuid_by_username(username)
        if not data or not data.get("id"):
            return False
        
        uuid = data.get("id")
        history_data = await self._fetch_history_names(uuid)
        if not history_data or not history_data.get("history"):
            return False
        
        # 检查历史用户名是否在数据库中
        for history in history_data.get("history", []):
            history_name = history.get("name")
            if history_name and self._user_exists_in_db(history_name):
                # 更新用户信息
                self._update_user_by_history(uuid, data.get("name"), history_name)
                return True
        
        return False
    
    async def real_player_verify(self, username: str) -> bool:
        """验证是否为真实玩家"""
        # 检查是否为机器人用户名
        if self._is_bot_username(username):
            return False

        # 检查数据库中是否存在
        if self._user_exists_in_db(username):
            return True

        # 检查服务器白名单（防止在游戏内添加白名单，没有存在数据库里）
        whitelist_list = await get_whitelist(self.servers)
        if username in whitelist_list:
            if await self._sync_whitelist_user_to_db(username):
                return True
        
        # 通过UUID验证
        if await self._verify_by_uuid(username):
            return True
        
        # 通过历史用户名验证
        try:
            return await self._verify_by_history_names(username)
        except Exception as e:
            logger.error(f"验证玩家失败: {e}, 用户名: {username}")
            return False

    async def is_real_player(self, username: str) -> bool:
        """兼容方法别名，供外部调用判断是否为真人玩家"""
        return await self.real_player_verify(username)
    
    async def _execute_whitelist_command(self, operation: str, username: str) -> None:
        """在所有服务器上执行白名单命令"""
        async def do_op(server: Dict):
            try:
                await send_command(server, f'whitelist {operation} {username}')
            except Exception:
                pass
        
        await asyncio.gather(*[do_op(s) for s in self.servers], return_exceptions=True)
    
    async def _add_user_to_whitelist(self, username: str) -> Tuple[bool, str]:
        """添加用户到白名单"""
        # 获取UUID
        data = await self._fetch_uuid_by_username(username)
        if not data or data.get("errorMessage"):
            return False, '没查到UUID喵~'
        
        uuid = data.get("id")
        # 检查是否已存在
        if self._uuid_exists_in_db(uuid):
            return False, '该玩家已在白名单中喵~'
        
        # 添加到数据库
        self._insert_user(uuid, username)
        return True, f'已将{username}添加到白名单喵~'
    
    async def _remove_user_from_whitelist(self, username: str) -> Tuple[bool, str]:
        """从白名单移除用户"""
        self._delete_user(username)
        return True, f'已将{username}移除白名单喵~'

    async def operation_whitelist(self, operation: str, username: str) -> Tuple[bool, str]:
        """处理白名单添加/移除操作"""
        # 在所有服务器上执行命令
        await self._execute_whitelist_command(operation, username)
        
        # 根据操作类型处理数据库
        if operation == 'add':
            return await self._add_user_to_whitelist(username)
        else:
            return await self._remove_user_from_whitelist(username)
