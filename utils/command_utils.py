import json

from astrbot.api.event import AstrMessageEvent
from cachetools import TTLCache

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
from .task_utils import TaskUtils
import re
import asyncio
from typing import Optional, List, Dict, Tuple
import sqlite3

class CommandUtils:
    def __init__(self, config: AstrBotConfig, conn: sqlite3.Connection):

        self.PERMISSION_DENIED = PERMISSION_DENIED
        self.config_utils = ConfigUtils(config)
        self.message = MessageUtils()
        self.image_utils = ImageUtils(self.config_utils)
        self.loc_utils = LocUtils(self.config_utils)
        self.servers = self.config_utils.get_server_list()
        self.rcon_pool = get_rcon_pool()
        self.task_utils = TaskUtils(self.config_utils, conn)

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
                return "找不到服务器喵~"
            match = MC_COMMAND_RE.match(msg)
            command = match.group(1) if match else ''
            return await send_command(self.rcon_pool, server, command)

        return self.message.get_help_message()

    async def list_players(self) -> str:
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

    def is_bot_player(self, player_name, bot_prefix) -> bool:
        """判断是否是bot"""
        if not player_name or len(player_name) < 3:  # 防止玩家ID过短
            return False

        # 将玩家名和前缀都转换为小写进行比较
        player_lower = player_name.lower()
        prefix_lower = bot_prefix.lower()

        # 检查是否以假人前缀开头（忽略大小写）
        return player_lower.startswith(prefix_lower)

    # 验证坐标范围
    def validate_coordinates(self, coordinates: str) -> tuple[bool, str]:
        try:
            coord_parts = coordinates.split()
            if len(coord_parts) != 3:
                return False, "是<x y z>喵~"

            x, y, z = int(coord_parts[0]), int(coord_parts[1]), int(coord_parts[2])
            # 验证坐标范围（Minecraft世界坐标范围）
            if not (-30000000 <= x <= 30000000 and -30000000 <= z <= 30000000 and -64 <= y <= 368):
                return False, "坐标不可以太大喵~"
            return True, ""
        except ValueError:
            return False, "坐标是整数喵~"

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
                        return '没有白名单喵~'
                    return '\n'.join(wl_list)
                except Exception:
                    continue
            return "服务器连接失败喵~"

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
            return f'已将{arr[2] + method}白名单喵~'
        return '未知错误喵~'

    async def loc(self, msg: str, event: AstrMessageEvent) -> str:
        """处理loc命令的函数
        
        命令格式:
        /loc add <项目名字> <0-主世界 1-地狱 2-末地> <坐标> 添加服务器项目
        /loc remove <项目名字> 删除服务器项目
        /loc list 服务器项目坐标列表
        /loc <项目名字> 查看项目地址
        /loc set <项目名字> <0-主世界 1-地狱 2-末地> <坐标> 修改项目坐标
        """

        # list
        if msg.startswith('loc list'):
            # 显示所有位置列表
            return self.loc_utils.list_loc()

        elif msg.startswith('loc add'):
            match = LOC_ADD_RE.match(msg)
            if not match:
                return "是/loc add <项目名字> <0-主世界 1-地狱 2-末地> <x y z>喵~"

            name, dimension, x, y, z = match.groups()
            coordinates = f"{x} {y} {z}"

            # 验证坐标
            is_valid, error_msg = self.validate_coordinates(coordinates)
            if not is_valid:
                return error_msg

            # 创建并添加Loc对象
            loc = Loc(name=name, dimension=int(dimension), location=coordinates)
            return self.loc_utils.add_loc(loc)

        elif msg.startswith('loc remove'):
            # loc remove <项目名字>
            parts = msg.split(maxsplit=2)
            if len(parts) != 3:
                return "是/loc remove <项目名字>喵"

            name = parts[2]
            return self.loc_utils.remove_loc(name)

        elif msg.startswith('loc set'):
            match = LOC_SET_RE.match(msg)
            if not match:
                return "是/loc set <项目名字> <0-主世界 1-地狱 2-末地> <x y z>喵~"

            name, dimension, x, y, z = match.groups()
            coordinates = f"{x} {y} {z}"

            # 验证坐标
            is_valid, error_msg = self.validate_coordinates(coordinates)
            if not is_valid:
                return error_msg

            # 检查位置是否存在
            loc = self.loc_utils.get_loc_by_name(name)
            if loc is None:
                return f'没找到"{name}"喵~\n可以使用/loc list查看列表'

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

            return f'没找到"{loc_name}"喵~\n可以使用/loc list查看列表'

        # 命令格式不正确，返回帮助信息
        return self.message.get_loc_help_message()

    async def task(self, msg: str, event: AstrMessageEvent, task_temp:TTLCache) -> dict:
        """处理task命令的函数
        命令格式:
        /task add <工程名字> <0-主世界 1-地狱 2-末地> <坐标> 添加服务器工程
        /task remove <工程名字> 删除服务器工程
        /task list 服务器工程坐标列表
        /task <工程名字> 查看服务器工程详细信息
        /task set <工程名字> <0-主世界 1-地狱 2-末地> <坐标> 修改服务器工程
        /task commit <工程id> <材料id> <已备数量> 提交材料的备货情况
        /task export <工程id> <0-txt 1-csv 2-excel> 导出工程相关信息 (正在开发中)
        /task claim <工程名称> <材料编号> 认领材料
        函数返回结构：
        返回的为文本类型时：{"type":"text","msg":""}
        返回的为图片链接时：{"type":"image","msg":""}
        """
        if msg.startswith('task add'):
            # 添加工程
            """
            命令结构: task add <工程名字> <0-主世界 1-地狱 2-末地> <坐标>
            不符合命令结构 -> 返回命令结构
            符合命令结构 -> 记录相关信息(创建人、工程名称、工程纬度、工程坐标)[如果存在则替换信息] -> 持续检测创建人的消息 -> 判断消息类型是否为文件(是)|pass(非) [此流程在main文件] 
            -> 判断后缀是否为合法后缀(是)|发送提示(非) -> 解析文件(是)|返回提示(非) -> 上传数据库(解析成功)|发送提示(解析失败)
            """

            # 校验命令格式
            parts = msg.split(maxsplit=6)
            if len(parts) != 7:
                return {"type": "text", "msg": "是/task add <工程名字> <0-主世界 1-地狱 2-末地> <x y z>喵~"}

            # 校验坐标
            coordinates = f"{parts[4]} {parts[5]} {parts[6]}"
            is_valid, error_msg = self.validate_coordinates(coordinates)
            if not is_valid:
                return {"type": "text", "msg": error_msg}

            # 校验是否重名
            task = self.task_utils.get_task_by_name(parts[2])
            if task["code"] == 200:
                return {"type":"text", "msg": f"已经有{parts[2]}了喵~"}

            # 校验是否已经创建，TODO: 改为存数据库缓存。添加发送者id
            for i in task_temp:
                if task_temp[i]["name"] == parts[2]:
                    return {"type":"text", "msg": f"{task_temp[i]['CreateUser']}已经申请创建{parts[2]}了喵~"}

            # 创建临时信息，TODO: 改为存数据库缓存
            task_temp[event.message_obj.sender.user_id] = {
                "name": parts[2],
                "location": parts[3],
                "dimension": coordinates,
                "CreateUser": event.message_obj.sender.nickname
            }
            return {"type":"text", "msg": "好的喵~快发我litematic、txt、csv吧"}

        elif msg.startswith('task remove'):
            # 删除工程
            """
            命令结构：task remove <工程名字>
            处理逻辑:
            不符合命令结构 -> 返回命令结构
            符合命令结构 -> 调用数据库 -> 判断工程是否存在 -> 删除相关数据(存在)｜返回提示(不存在) -> 提交数据库修改
            """
            # 符合命令结构 -> 调用数据库 -> 删除相关数据 -> 提交数据库修改
            # 不符合命令结构 -> 返回task remove命令的结构
            parts = msg.split(maxsplit=2)
            if len(parts) != 3:
                return {"type":"text","msg":"是/task remove <项目名字>喵~"}

            # 数据库移除
            name = parts[2]
            return {"type":"text","msg":self.task_utils.remove_task(name, event)}

        elif msg.startswith('task list'):
            # 工程列表
            # 返回工程列表
            return {"type":"text","msg":self.task_utils.get_task_list()}

        elif msg.startswith('task commit'):
            # 提交材料，TODO: 提交进度，接取任务
            """
            命令结构：task commit <工程id> <材料id> <已备数量> 提交材料的备货情况
            处理逻辑:
            不符合命令结构 -> 返回命令结构
            符合命令结构 -> 调用数据库 -> 判断工程是否存在 -> 修改数据(存在)｜返回提示(不存在) -> 提交数据修改(存在)
            """
            parts = msg.split(maxsplit=5)
            if len(parts) != 6:
                return {"type": "text", "msg": "是/task commit <工程名称> <材料序号> <进度> <材料所在假人>喵~"}

            return {"type":"text","msg":self.task_utils.commit_task(parts, event)}

        elif msg.startswith('task set'):
            # 修改工程信息
            """
            命令结构：/task set <工程名字> <新工程名称> <0-主世界 1-地狱 2-末地> <坐标(x y z)>
            处理逻辑：
            不符合命令结构 -> 返回命令结构
            符合命令结构 -> 调用数据库 -> 判断工程是否存在 -> 修改数据(存在)｜返回提示(不存在) -> 提交数据修改
            PS:暂时不支持修改材料列表，在后续版本进行新增
            """

            # 校验命令
            parts = msg.split(maxsplit=7)
            if len(parts) != 8:
                return {"type": "text",  "msg": "请使用: /task set <工程名字> <新工程名称> <0-主世界 1-地狱 2-末地> <x y z>"}

            # 校验坐标
            coordinates = f"{parts[5]} {parts[6]} {parts[7]}"
            is_valid, error_msg = self.validate_coordinates(coordinates)
            if not is_valid:
                return {"type": "text", "msg": error_msg}

            return {"type": "text", "msg": self.task_utils.set_task(parts, event)}

        elif msg.startswith('task'):
            """
            处理逻辑：
            task不带参数 - > 返回task命令的help
            task带名称 -> 返回工程详情(图片)
            """
            parts = msg.split(maxsplit=1)

            # task不带参数 - > 返回task命令的help
            if len(parts) != 2:
                return {"type":"text","msg":self.message.get_task_help_message()}

            # task带名称 -> 返回工程详情(图片)
            task_name = parts[1]
            task = self.task_utils.get_task_by_name(task_name)
            if task["code"] != 200:
                return {"type":"text","msg":f"没找到{task_name}喵~"}
            url = self.task_utils.render(task["msg"])
            return {"type":"image", "msg":url}

        # TODO 认领材料
        elif msg.startswith('task claim'):
            pass

        # TODO 取消认领材料
        elif msg.startswith('task EscClaim'):
            pass

        return {"type": "text", "msg": self.message.get_task_help_message()}

    async def material(self, task_temp:TTLCache, event: AstrMessageEvent) -> str | None:

        # TODO: 数据缓存改数据库
        # 获取原信息
        raw_message = event.message_obj.raw_message
        match = re.search(r'<Event, (\{.*})>', str(raw_message), re.DOTALL)
        event_dict_str = match.group(1).replace("'", '\"')
        json_dict = json.loads(event_dict_str)

        # 消息类型
        message = json_dict.get('message')
        if message:
            if message[0]['type'] == 'text':
                return None
            elif message[0]['type'] == 'file':
                client = event.bot  # 得到 client
                payloads = {
                    "group_id": json_dict['group_id'],
                    "file_id": json_dict['message'][0]['data']['file_id'],
                }
                filename = json_dict['message'][0]['data']['file']

                # TODO: 解析投影源文件
                if not filename.endswith('.txt') and not filename.endswith('.csv'):
                    return None

                ret = await client.api.call_action('get_group_file_url', **payloads)
                return self.task_utils.task_material(ret['url'], filename, event.message_obj.sender.user_id, task_temp)
        return None

    def get_image(self) -> str:
        return self.image_utils.get_last_image()
