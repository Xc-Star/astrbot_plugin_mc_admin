from .message_utils import MessageUtils
from astrbot.api.event import AstrMessageEvent
from .rcon import Rcon
from .config_utils import ConfigUtils
from .image_utils import ImageUtils
from .message_utils import MessageUtils
from astrbot.api import logger
from .pojo.loc_result import LocResult
from .loc_utils import LocUtils
import re


class CommandUtils:
    def __init__(self):
        pass

    def mc(self, msg: str, event: AstrMessageEvent) -> str:
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

                # 获取服务器列表
                server_list = ConfigUtils().get_server_list()

                # 获取服务器Rcon连接参数
                server = None
                for s in server_list:
                    if s['name'] == arr[2]:
                        server = s
                        break
                if server is None:
                    return "没有找到服务器"

                rcon = Rcon(host=server["host"], password=server["password"], port=server["port"])
                match = re.match(r'^mc command \w+ (.*)$', msg)
                command = match.group(1)
                return rcon.send_command(command)

        # 默认返回帮助信息
        message = MessageUtils()
        return message.get_help_message()

    def list(self):
        """处理list命令的函数"""

        # 获取服务器列表
        config_utils = ConfigUtils()
        servers = config_utils.get_server_list()
        bot_prefix = config_utils.get_bot_prefix()

        # 遍历服务器列表
        servers_players = dict()
        for server in servers:
            # 发送命令，如果init抛异常，则跳过此次连接
            try:
                rcon = Rcon(host=server["host"], password=server["password"], port=server["port"])
            except:
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
        logger.info(servers_players)
        image_utils = ImageUtils()
        image_path = image_utils.generate_list_image(servers_players)
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

        config_utils = ConfigUtils()
        server_list = config_utils.get_server_list()

        # 优先处理查询列表
        if msg == 'wl list':

            for server in server_list:
                try:
                    rcon = Rcon(host=server['host'], password=server['password'], port=server['port'])
                    # TODO: 白名单列表
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
            for server in server_list:
                rcon = Rcon(host=server['host'], password=server['password'], port=server['port'])
                rcon.send_command(f'whitelist {arr[1]} {arr[2]}')
            method = '添加到' if arr[1] == 'add' else '移除'
            return f'已将{arr[2] + method}白名单'

    def loc(self, msg: str, event: AstrMessageEvent) -> LocResult:
        """处理loc命令的函数"""
        """
        /loc add <项目名字> <0-主世界 1-地狱 2-末地> <坐标> 添加服务器项目 (开发中)
        /loc remove <项目名字> 删除服务器项目 (开发中)
        /loc list 服务器项目坐标列表 (开发中)
        /loc <项目名字> 查看项目地址 (开发中)
        /loc set <项目名字> <0-主世界 1-地狱 2-末地> <坐标> 修改项目坐标 (开发中)
        """
        # 校验命令是否为 loc add/remove/list/set开头
        if msg.startswith('loc list'):
            # 列表
            loc_utils = LocUtils()
            return LocResult(LocResult().type_image, loc_utils.list_loc())
        elif msg.startswith('loc add'):
            # 添加
            loc_utils = LocUtils()
            return loc_utils.add_loc(msg)
        elif msg.startswith('loc remove'):
            # 删除
            loc_utils = LocUtils()
            return loc_utils.remove_loc(msg)
        elif msg.startswith('loc set'):
            # 修改
            loc_utils = LocUtils()
            return loc_utils.set_loc(msg)
        elif msg.startswith('loc '):
            # 查询
            name = msg[4:]
            loc_utils = LocUtils()
            return loc_utils.get_loc(name)

        message_utils = MessageUtils()
        return message_utils.get_loc_help_message()
