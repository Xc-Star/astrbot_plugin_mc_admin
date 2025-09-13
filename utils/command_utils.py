from .message_utils import MessageUtils
from astrbot.api.event import AstrMessageEvent
from .rcon import Rcon
from .config_utils import ConfigUtils
from .image_utils import ImageUtils
from .message_utils import MessageUtils
from astrbot.api import logger
from .pojo.loc_result import LocResult
from .loc_utils import LocUtils
from .pojo.loc import Loc
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
            result = LocResult()
            result.msg_result(loc_utils.list_loc())
            return result
        elif msg.startswith('loc add'):
            # 添加
            try:
                parts = msg.split()
                if len(parts) < 5:
                    message_utils = MessageUtils()
                    result = LocResult()
                    result.msg_result("参数不足，请使用格式: /loc add <项目名字> <0-主世界 1-地狱 2-末地> <坐标>")
                    return result
                
                name = parts[2]
                dimension = int(parts[3])
                coordinates = ' '.join(parts[4:])
                
                # 验证坐标格式
                coord_parts = coordinates.split()
                if len(coord_parts) != 3:
                    result = LocResult()
                    result.msg_result("坐标格式错误，请使用格式: x y z")
                    return result
                
                # 验证坐标是否为数字
                try:
                    x, y, z = int(coord_parts[0]), int(coord_parts[1]), int(coord_parts[2])
                except ValueError:
                    result = LocResult()
                    result.msg_result("坐标必须为数字")
                    return result
                
                # 验证坐标范围（Minecraft世界坐标范围）
                if not (-30000000 <= x <= 30000000 and -30000000 <= z <= 30000000 and -64 <= y <= 368):
                    result = LocResult()
                    result.msg_result("坐标超出有限范围")
                    return result
                
                # 创建Loc对象
                loc = Loc(name=name)
                if dimension == 0:
                    loc.overworld = (x, y, z)
                elif dimension == 1:
                    loc.nether = (x, y, z)
                elif dimension == 2:
                    loc.end = (x, y, z)
                else:
                    result = LocResult()
                    result.msg_result("维度参数错误，0-主世界 1-地狱 2-末地")
                    return result
                
                loc_utils = LocUtils()
                res = loc_utils.add_loc(loc)
                result = LocResult()
                result.msg_result(res)
                return result
            except Exception as e:
                result = LocResult()
                result.msg_result(f"添加位置失败: {str(e)}")
                return result
        elif msg.startswith('loc remove'):
            # 删除
            try:
                parts = msg.split()
                if len(parts) < 3:
                    result = LocResult()
                    result.msg_result("参数不足，请使用格式: /loc remove <项目名字>")
                    return result
                
                name = parts[2]
                loc_utils = LocUtils()
                res = loc_utils.remove_loc(name)
                result = LocResult()
                result.msg_result(res)
                return result
            except Exception as e:
                result = LocResult()
                result.msg_result(f"删除位置失败: {str(e)}")
                return result
        elif msg.startswith('loc set'):
            # 修改
            try:
                parts = msg.split()
                if len(parts) < 5:
                    result = LocResult()
                    result.msg_result("参数不足，请使用格式: /loc set <项目名字> <0-主世界 1-地狱 2-末地> <坐标>")
                    return result
                
                name = parts[2]
                dimension = int(parts[3])
                coordinates = ' '.join(parts[4:])
                
                # 验证坐标格式
                coord_parts = coordinates.split()
                if len(coord_parts) != 3:
                    result = LocResult()
                    result.msg_result("坐标格式错误，请使用格式: x y z")
                    return result
                
                # 验证坐标是否为数字
                try:
                    x, y, z = int(coord_parts[0]), int(coord_parts[1]), int(coord_parts[2])
                except ValueError:
                    result = LocResult()
                    result.msg_result("坐标必须为数字")
                    return result
                
                # 验证坐标范围（Minecraft世界坐标范围）
                if not (-30000000 <= x <= 30000000 and -30000000 <= z <= 30000000 and -64 <= y <= 368):
                    result = LocResult()
                    result.msg_result("坐标超出有限范围")
                    return result
                
                # 创建Loc对象
                loc = Loc(name=name)
                if dimension == 0:
                    loc.overworld = (x, y, z)
                elif dimension == 1:
                    loc.nether = (x, y, z)
                elif dimension == 2:
                    loc.end = (x, y, z)
                else:
                    result = LocResult()
                    result.msg_result("维度参数错误，0-主世界 1-地狱 2-末地")
                    return result
                
                loc_utils = LocUtils()
                res = loc_utils.set_loc(loc)
                result = LocResult()
                result.msg_result(res)
                return result
            except Exception as e:
                result = LocResult()
                result.msg_result(f"修改位置失败: {str(e)}")
                return result
        elif msg.startswith('loc '):
            # 查询
            try:
                name = msg[4:].strip()
                if not name:
                    result = LocResult()
                    result.msg_result("请输入位置名称")
                    return result
                
                loc_utils = LocUtils()
                loc = loc_utils.get_loc_by_name(name)
                if loc:
                    result_str = f"位置: {loc.name}\n"
                    if loc.overworld:
                        result_str += f"主世界: {loc.overworld[0]} {loc.overworld[1]} {loc.overworld[2]}\n"
                    if loc.nether:
                        result_str += f"下界: {loc.nether[0]} {loc.nether[1]} {loc.nether[2]}\n"
                    if loc.end:
                        result_str += f"末地: {loc.end[0]} {loc.end[1]} {loc.end[2]}"
                    result = LocResult()
                    result.msg_result(result_str.strip())
                    return result
                else:
                    result = LocResult()
                    result.msg_result(f"未找到位置: {name}")
                    return result
            except Exception as e:
                result = LocResult()
                result.msg_result(f"查询位置失败: {str(e)}")
                return result

        message_utils = MessageUtils()
        result = LocResult()
        result.msg_result(message_utils.get_loc_help_message())
        return result
