import time

from .message_utils import MessageUtils
from astrbot.api.event import AstrMessageEvent
from .rcon import Rcon
from .config_utils import ConfigUtils
from .image_utils import ImageUtils
from .message_utils import MessageUtils
from astrbot.api import logger
from .pojo.loc_result import LocResult
from astrbot.core import AstrBotConfig
from .loc_utils import LocUtils
from .pojo.loc import Loc
import re


class CommandUtils:
    def __init__(self, config: AstrBotConfig):
        self.config_utils = ConfigUtils(config)
        self.message = MessageUtils()
        self.image_utils = ImageUtils(self.config_utils)
        self.loc_utils = LocUtils()
        self.servers = self.config_utils.get_server_list()

        # loc add/set <项目名字> <0-主世界 1-地狱 2-末地> <x y z>
        self.loc_add_pattern = r'^loc add\s+([\w\\s]+?)\s+([012])\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)$'
        self.loc_set_pattern = r'^loc set\s+([\w\\s]+?)\s+([012])\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)$'
        self.mc_command_pattern = r'^mc command \w+ (.*)$'

    async def mc(self, msg: str, event: AstrMessageEvent) -> str:
        """处理mc命令的函数"""

        # 优先处理mc wl
        if msg.startswith('mc wl'):
            # 截取命令
            parts = msg.split()
            command = ' '.join(parts[1:])
            return self.wl(command, event)

        # 获取命令长度
        arr = msg.split(' ')

        # 长度大于等于3的命令。如：mc command 生存服 time set 0
        if len(arr) >= 3:
            if arr[1] == 'command':
                # 管理员权限
                if not event.is_admin():
                    return '我才不听你的呢'

                # 获取服务器Rcon连接参数
                server = None
                for s in self.servers:
                    if s['name'] == arr[2]:
                        server = s
                        break
                if server is None:
                    return "没有找到服务器"

                rcon = Rcon(host=server["host"], password=server["password"], port=int(server["port"]))
                match = re.match(self.mc_command_pattern, msg)
                command = match.group(1)
                return rcon.send_command(command)

        # 默认返回帮助信息
        return self.message.get_help_message()

    async def list_players(self):
        """处理list命令的函数"""

        # 获取服务器列表
        bot_prefix = self.config_utils.get_bot_prefix()

        # 遍历服务器列表
        servers_players = dict()
        for server in self.servers:
            # 发送命令，如果init抛异常，则跳过此次连接
            try:
                rcon = Rcon(host=server["host"], password=server["password"], port=int(server["port"]))
            except:
                logger.error(f"服务器 {server['name']} 连接失败")
                continue

            res = rcon.send_command("list")

            # 分割玩家列表，防止玩家ID过短导致报错
            try:
                if ':' not in res:
                    continue
                players_str = res.split(':')[1]
                if not players_str.strip():
                    servers_players[server["name"]] = {
                        "bot_players": [],
                        "real_players": []
                    }
                    continue
                players = [p.strip() for p in players_str.split(',') if p.strip()]
            except (IndexError, AttributeError):
                continue

            # 白名单比对
            if self.config_utils.enable_whitelist_compare:
                rcon = Rcon(host=server["host"], password=server["password"], port=int(server["port"]))
                wl = rcon.send_command('whitelist list')
                if wl == 'There are no whitelisted players':
                    whitelist_list = []
                    pass
                else:
                    players_start = wl.find(':') + 1
                    players_str = wl[players_start:].strip()
                    whitelist_list = [player.strip() for player in players_str.split(',')]
                bot_players = [p for p in players if p not in whitelist_list]
                real_players = [p for p in players if p in whitelist_list]
            # 假人前缀
            else:
                bot_players = [p for p in players if self.is_bot_player(p, bot_prefix)]
                real_players = [p for p in players if not self.is_bot_player(p, bot_prefix)]
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
            servers_players[server["name"]] = {
                "bot_players": bot_players,
                "real_players": real_players
            }


        # 生成在线玩家列表图片
        image_path = await self.image_utils.generate_list_image(servers_players)
        return image_path

        # 处理假人前缀的大小写混用和中英文混用

    def is_bot_player(self, player_name, bot_prefix):
        """判断是否是bot"""
        if not player_name or len(player_name) < 3:  # 防止玩家ID过短
            return False

        # 将玩家名和前缀都转换为小写进行比较
        player_lower = player_name.lower()
        prefix_lower = bot_prefix.lower()

        # 检查是否以假人前缀开头（忽略大小写）
        return player_lower.startswith(prefix_lower)

    def wl(self, msg: str, event: AstrMessageEvent) -> str:
        """处理白名单命令的函数"""

        # 管理员权限
        if not event.is_admin():
            return '我才不听你的呢'

        # 优先处理查询列表
        if msg == 'wl list':

            for server in self.servers:
                try:
                    rcon = Rcon(host=server['host'], password=server['password'], port=int(server['port']))
                    # 白名单列表
                    wl = rcon.send_command(f'whitelist list')
                    if wl == 'There are no whitelisted players':
                        return '暂无白名单'
                    else:
                        players_start = wl.find(':') + 1
                        players_str = wl[players_start:].strip()
                        players_list = [player.strip() for player in players_str.split(',')]
                        players_str = '\n'.join(players_list)
                        return players_str
                except:
                    continue
            return "服务器链接错误"

        # 分割命令
        arr = msg.split(' ')

        # 长度不符合返回帮助信息
        if len(arr) != 3:
            message = MessageUtils()
            return message.get_help_message()

        # 白名单操作
        if arr[1] == 'add' or arr[1] == 'remove':
            for server in self.servers:
                try:
                    rcon = Rcon(host=server['host'], password=server['password'], port=int(server['port']))
                    rcon.send_command(f'whitelist {arr[1]} {arr[2]}')
                except:
                    continue
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
            match = re.match(self.loc_add_pattern, msg)
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
            match = re.match(self.loc_set_pattern, msg)
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
