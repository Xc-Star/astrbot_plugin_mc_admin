from astrbot.api.event import AstrMessageEvent
from .rcon_pool import get_rcon_pool
from .config_utils import ConfigUtils
from .image_utils import ImageUtils
from .message_utils import MessageUtils
from .command_helpers import (
    PERMISSION_DENIED,
    LOC_ADD_RE,
    LOC_SET_RE,
    MC_COMMAND_RE,
    find_server_by_name,
    send_command,
    parse_list_players,
    get_whitelist,
    split_players_by_whitelist,
    split_players_by_prefix,
)
from astrbot.api import logger
from astrbot.core import AstrBotConfig
from .loc_utils import LocUtils
from .pojo.loc import Loc
import re
import asyncio
from typing import Optional, List, Dict, Tuple


class CommandUtils:
    def __init__(self, config: AstrBotConfig):
        self.PERMISSION_DENIED = PERMISSION_DENIED
        self.config_utils = ConfigUtils(config)
        self.message = MessageUtils()
        self.image_utils = ImageUtils(self.config_utils)
        self.loc_utils = LocUtils(self.config_utils)
        self.servers = self.config_utils.get_server_list()
        self.rcon_pool = get_rcon_pool()

        # 常量/正则交由 helper 管理

    async def mc(self, msg: str, event: AstrMessageEvent) -> str:
        """处理mc命令的函数"""

        # 优先处理mc wl
        if msg.startswith('mc wl'):
            parts = msg.split()
            command = ' '.join(parts[1:])
            return await self.wl(command, event)

        arr = msg.split(' ')

        # mc command <服务器> <命令...>
        if len(arr) >= 3 and arr[1] == 'command':
            if not event.is_admin():
                return self.PERMISSION_DENIED
            server = find_server_by_name(self.servers, arr[2])
            if server is None:
                return "没有找到服务器"
            match = MC_COMMAND_RE.match(msg)
            command = match.group(1) if match else ''
            return await send_command(self.rcon_pool, server, command)

        return self.message.get_help_message()

    async def list_players(self):
        """处理list命令的函数"""

        bot_prefix = self.config_utils.get_bot_prefix()

        async def process_server(server: Dict) -> Optional[Tuple[str, Dict[str, List[str]]]]:
            try:
                res = await send_command(self.rcon_pool, server, "list")
            except Exception:
                return None
            players = parse_list_players(res)
            if not players:
                return server["name"], {"bot_players": [], "real_players": []}

            if self.config_utils.enable_whitelist_compare:
                wl = await get_whitelist(self.rcon_pool, server)
                bot_players, real_players = split_players_by_whitelist(players, wl)
            else:
                bot_players, real_players = split_players_by_prefix(players, bot_prefix)
            """
            servers_players: {
                "server1": {
                    "bot_players": ["bot_Xc_Star1", "bot_Xc_Star2"],
                    "real_players": ["Xc_Star1", "Xc_Star2"]
                },
                "server2": {
                    "bot_players": ["bot_SCT1", "bot_SCT2"],
                    "real_players": ["SCT1", "SCT2"]
                }
            }
            """
            return server["name"], {"bot_players": bot_players, "real_players": real_players}

        tasks = [process_server(s) for s in self.servers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        servers_players: Dict[str, Dict[str, List[str]]] = {}
        for r in results:
            if isinstance(r, tuple) and len(r) == 2:
                name, data = r
                servers_players[name] = data

        image_path = await self.image_utils.generate_list_image(servers_players)
        return image_path

    def is_bot_player(self, player_name, bot_prefix):
        """判断是否是bot"""
        if not player_name or len(player_name) < 3:  # 防止玩家ID过短
            return False

        # 将玩家名和前缀都转换为小写进行比较
        player_lower = player_name.lower()
        prefix_lower = bot_prefix.lower()

        # 检查是否以假人前缀开头（忽略大小写）
        return player_lower.startswith(prefix_lower)

    async def wl(self, msg: str, event: AstrMessageEvent) -> str:
        """处理白名单命令的函数"""

        # 管理员权限
        if not event.is_admin():
            return PERMISSION_DENIED

        # 优先处理查询列表
        if msg == 'wl list':
            for server in self.servers:
                try:
                    wl_list = await get_whitelist(self.rcon_pool, server)
                    if not wl_list:
                        return '暂无白名单'
                    return '\n'.join(wl_list)
                except Exception:
                    continue
            return "服务器链接错误"

        # 分割命令
        arr = msg.split(' ')

        # 长度不符合返回帮助信息
        if len(arr) != 3:
            return self.message.get_help_message()

        # 白名单操作
        if arr[1] == 'add' or arr[1] == 'remove':
            async def do_op(server: Dict):
                try:
                    await send_command(self.rcon_pool, server, f'whitelist {arr[1]} {arr[2]}')
                except Exception:
                    pass
            await asyncio.gather(*[do_op(s) for s in self.servers], return_exceptions=True)
            method = '添加到' if arr[1] == 'add' else '移除'
            return f'已将{arr[2] + method}白名单'

    async def loc(self, msg: str, event: AstrMessageEvent) -> str:
        """处理loc命令的函数
        
        命令格式:
        /loc add <项目名字> <0-主世界 1-地狱 2-末地> <坐标> 添加服务器项目
        /loc remove <项目名字> 删除服务器项目
        /loc list 服务器项目坐标列表
        /loc <项目名字> 查看项目地址
        /loc set <项目名字> <0-主世界 1-地狱 2-末地> <坐标> 修改项目坐标
        """

        # 验证坐标范围
        def validate_coordinates(coordinates: str) -> tuple[bool, str]:
            try:
                coord_parts = coordinates.split()
                if len(coord_parts) != 3:
                    return False, "坐标格式不正确，请提供x y z三个坐标值"

                x, y, z = int(coord_parts[0]), int(coord_parts[1]), int(coord_parts[2])
                # 验证坐标范围（Minecraft世界坐标范围）
                if not (-30000000 <= x <= 30000000 and -30000000 <= z <= 30000000 and -64 <= y <= 368):
                    return False, "坐标超出有效范围"
                return True, ""
            except ValueError:
                return False, "坐标必须为整数"

        # list
        if msg.startswith('loc list'):
            # 显示所有位置列表
            return self.loc_utils.list_loc()

        elif msg.startswith('loc add'):
            match = LOC_ADD_RE.match(msg)
            if not match:
                return "请使用: /loc add <项目名字> <0-主世界 1-地狱 2-末地> <x y z>"

            name, dimension, x, y, z = match.groups()
            coordinates = f"{x} {y} {z}"

            # 验证坐标
            is_valid, error_msg = validate_coordinates(coordinates)
            if not is_valid:
                return error_msg

            # 创建并添加Loc对象
            loc = Loc(name=name, dimension=int(dimension), location=coordinates)
            return self.loc_utils.add_loc(loc)

        elif msg.startswith('loc remove'):
            # loc remove <项目名字>
            parts = msg.split(maxsplit=2)
            if len(parts) != 3:
                return "请使用: /loc remove <项目名字>"

            name = parts[2]
            return self.loc_utils.remove_loc(name)

        elif msg.startswith('loc set'):
            match = LOC_SET_RE.match(msg)
            if not match:
                return "请使用: /loc set <项目名字> <0-主世界 1-地狱 2-末地> <x y z>"

            name, dimension, x, y, z = match.groups()
            coordinates = f"{x} {y} {z}"

            # 验证坐标
            is_valid, error_msg = validate_coordinates(coordinates)
            if not is_valid:
                return error_msg

            # 检查位置是否存在
            loc = self.loc_utils.get_loc_by_name(name)
            if loc is None:
                return f'未找到"{name}"\n可以使用/loc list查看列表'

            # 更新位置信息
            loc.set_location(dimension=int(dimension), location=coordinates)
            return self.loc_utils.set_loc(loc)

        elif msg.startswith('loc '):
            # 查看指定位置详情
            parts = msg.split(maxsplit=1)
            if len(parts) != 2:
                return self.message.get_loc_help_message()

            loc_name = parts[1]
            loc = self.loc_utils.get_loc_by_name(loc_name)
            if loc:
                # 构建返回信息
                result_parts = [f"位置: {loc.name}"]
                if loc.overworld:
                    result_parts.append(f"主世界: {loc.overworld}")
                if loc.nether:
                    result_parts.append(f"地狱: {loc.nether}")
                if loc.end:
                    result_parts.append(f"末地: {loc.end}")
                return "\n".join(result_parts)

            return f'未找到"{loc_name}"\n可以使用/loc list查看列表'

        # 命令格式不正确，返回帮助信息
        return self.message.get_loc_help_message()

    def get_image(self):
        return self.image_utils.get_last_image()
