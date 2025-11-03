import asyncio
import json
import re
import sqlite3
from typing import Optional, List, Dict, Tuple, TypedDict

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.core import AstrBotConfig
from cachetools import TTLCache

from ..command.helpers import (
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
from ..config_utils import ConfigUtils
from ..loc.main import LocUtils
from ..loc.vo import Loc
from ..media.image import ImageUtils
from ..message import MessageUtils
from ..rcon.pool import get_rcon_pool
from ..task import TaskUtils


# ==================== 类型定义 ====================
class TaskResponse(TypedDict):
    """任务命令响应结构"""
    type: str | list[str]  # "text" | "image" | "image_list"
    msg: str  # 当 type 为 "image_list" 时，msg 为图片 URL 列表


# ==================== 常量定义 ====================
# Minecraft 坐标边界
MC_COORD_X_MIN, MC_COORD_X_MAX = -30000000, 30000000
MC_COORD_Y_MIN, MC_COORD_Y_MAX = -64, 368
MC_COORD_Z_MIN, MC_COORD_Z_MAX = -30000000, 30000000

# 支持的文件后缀
ALLOWED_FILE_EXTENSIONS = ('.txt', '.csv', '.litematic')

# 材料单位映射
MATERIAL_UNIT_MAP = {
    '个': (1, 0, 0),
    '组': (0, 1, 0),
    '盒': (0, 0, 1),
}

class CommandUtils:
    """Minecraft 服务器命令工具类"""
    
    def __init__(self, config: AstrBotConfig, conn: sqlite3.Connection):
        """初始化命令工具"""
        # 工具类初始化
        self.config_utils = ConfigUtils(config)
        self.message = MessageUtils()
        self.image_utils = ImageUtils(self.config_utils)
        self.loc_utils = LocUtils(conn)  # 使用数据库存储
        self.task_utils = TaskUtils(self.config_utils, conn, self.image_utils)
        
        # 服务器与连接池
        self.servers = self.config_utils.get_server_list()
        self.rcon_pool = get_rcon_pool()
        
        # 常量
        self.PERMISSION_DENIED = PERMISSION_DENIED

    # ==================== MC 命令处理 ====================
    async def mc(self, msg: str, event: AstrMessageEvent) -> str:
        """处理 MC 相关命令"""
        # 优先处理白名单命令
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

    # ==================== 玩家列表 ====================
    async def list_players(self) -> str:
        """获取所有服务器的玩家列表并生成图片"""
        bot_prefix = self.config_utils.get_bot_prefix()

        async def process_server(server: Dict) -> Optional[Tuple[str, Dict[str, List[str]]]]:
            """处理单个服务器的玩家列表"""
            try:
                res = await send_command(self.rcon_pool, server, "list")
            except Exception:
                return None
            
            players = parse_list_players(res)
            if not players:
                return server["name"], {"bot_players": [], "real_players": []}

            # 根据配置选择分类方式
            if self.config_utils.enable_whitelist_compare:
                wl = await get_whitelist(self.rcon_pool, server)
                bot_players, real_players = split_players_by_whitelist(players, wl)
            else:
                bot_players, real_players = split_players_by_prefix(players, bot_prefix)
            
            return server["name"], {"bot_players": bot_players, "real_players": real_players}

        # 并发处理所有服务器
        tasks = [process_server(s) for s in self.servers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 汇总结果
        servers_players: Dict[str, Dict[str, List[str]]] = {}
        for r in results:
            if isinstance(r, tuple) and len(r) == 2:
                name, data = r
                servers_players[name] = data

        # 生成图片
        image_path = await self.image_utils.generate_list_image(servers_players)
        return image_path

    # ==================== 工具方法 ====================
    def validate_coordinates(self, coordinates: str) -> Tuple[bool, str]:
        """验证 Minecraft 坐标的有效性"""
        try:
            coord_parts = coordinates.split()
            if len(coord_parts) != 3:
                return False, "是<x y z>喵~"

            x, y, z = int(coord_parts[0]), int(coord_parts[1]), int(coord_parts[2])
            
            # 验证坐标范围
            if not (MC_COORD_X_MIN <= x <= MC_COORD_X_MAX and 
                    MC_COORD_Z_MIN <= z <= MC_COORD_Z_MAX and 
                    MC_COORD_Y_MIN <= y <= MC_COORD_Y_MAX):
                return False, "坐标不可以太大喵~"
            
            return True, ""
        except ValueError:
            return False, "坐标是整数喵~"

    # ==================== 白名单管理 ====================
    async def wl(self, msg: str, event: AstrMessageEvent) -> str:
        """处理白名单命令"""
        # 权限检查
        if not event.is_admin():
            return self.PERMISSION_DENIED

        # 查询白名单列表
        if msg == 'wl list':
            return await self._handle_wl_list()

        # 解析命令
        arr = msg.split(' ')
        if len(arr) != 3:
            return self.message.get_help_message()

        # 白名单添加/移除操作
        if arr[1] in ('add', 'remove'):
            return await self._handle_wl_operation(arr[1], arr[2])
        
        return '未知错误喵~'
    
    async def _handle_wl_list(self) -> str:
        """处理白名单列表查询"""
        aggregated: List[str] = []
        had_error = False
        
        for server in self.servers:
            try:
                wl_list = await get_whitelist(self.rcon_pool, server)
                if wl_list:
                    aggregated.extend(wl_list)
            except Exception:
                had_error = True
                continue
        
        # 去重并排序
        aggregated = sorted(set(aggregated))
        if aggregated:
            return '\n'.join(aggregated)
        return '没有白名单喵~' if not had_error else '服务器连接失败喵~'
    
    async def _handle_wl_operation(self, operation: str, player_name: str) -> str:
        """处理白名单添加/移除操作"""
        async def do_op(server: Dict):
            try:
                await send_command(self.rcon_pool, server, f'whitelist {operation} {player_name}')
            except Exception:
                pass
        
        await asyncio.gather(*[do_op(s) for s in self.servers], return_exceptions=True)
        method = '添加到' if operation == 'add' else '移除'
        return f'已将{player_name}{method}白名单喵~'

    # ==================== 位置管理 ====================
    async def loc(self, msg: str, event: AstrMessageEvent) -> str:
        """处理位置(Location)命令
        
        支持的命令格式:
        - /loc list: 显示所有位置列表
        - /loc add <名字> <维度> <x y z>: 添加位置
        - /loc remove <名字>: 删除位置
        - /loc set <名字> <维度> <x y z>: 修改位置
        - /loc <名字>: 查看位置详情
        
        Args:
            msg: 命令消息
            event: 消息事件对象
            
        Returns:
            处理结果消息
        """
        # 列出所有位置
        if msg.startswith('loc list'):
            return self.loc_utils.list_loc()

        # 添加位置
        if msg.startswith('loc add'):
            return self._handle_loc_add(msg)

        # 删除位置
        if msg.startswith('loc remove'):
            parts = msg.split(' ')
            if len(parts) != 3:
                return "是/loc remove <项目名字>喵"
            return self.loc_utils.remove_loc(parts[2])

        # 修改位置
        if msg.startswith('loc set'):
            return self._handle_loc_set(msg)

        # 查看位置详情
        if msg.startswith('loc '):
            return self._handle_loc_query(msg)

        return self.message.get_loc_help_message()
    
    def _handle_loc_add(self, msg: str) -> str:
        """处理位置添加"""
        match = LOC_ADD_RE.match(msg)
        if not match:
            return "是/loc add <项目名字> <0-主世界 1-地狱 2-末地> <x y z>喵~"

        name, dimension, x, y, z = match.groups()
        coordinates = f"{x} {y} {z}"

        # 验证坐标
        is_valid, error_msg = self.validate_coordinates(coordinates)
        if not is_valid:
            return error_msg

        # 创建并添加 Loc 对象
        loc = Loc(name=name, dimension=int(dimension), location=coordinates)
        return self.loc_utils.add_loc(loc)
    
    def _handle_loc_set(self, msg: str) -> str:
        """处理位置修改"""
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
    
    def _handle_loc_query(self, msg: str) -> str:
        """处理位置查询"""
        parts = msg.split(' ')
        if len(parts) != 2:
            return self.message.get_loc_help_message()

        loc_name = parts[1]
        loc = self.loc_utils.get_loc_by_name(loc_name)
        if not loc:
            return f'没找到"{loc_name}"喵~\n可以使用/loc list查看列表'

        # 构建返回信息
        result_parts = [f"位置: {loc.name}"]
        if loc.overworld:
            result_parts.append(f"主世界: {loc.overworld}")
        if loc.nether:
            result_parts.append(f"地狱: {loc.nether}")
        if loc.end:
            result_parts.append(f"末地: {loc.end}")
        
        return "\n".join(result_parts)

    # ==================== 任务管理 ====================
    async def task(self, msg: str, event: AstrMessageEvent, task_temp: TTLCache) -> TaskResponse:
        """处理任务(Task)命令
        
        支持的命令格式:
        - /task list: 显示工程列表
        - /task add <名字> <维度> <x y z>: 添加工程
        - /task remove <名字>: 删除工程
        - /task set <旧名> <新名> <维度> <x y z>: 修改工程
        - /task claim <名字> <材料编号>: 认领材料
        - /task commit <名字> <材料编号> <数量 单位> <位置>: 提交材料
        - /task <名字>: 查看工程详情
        
        Args:
            msg: 命令消息
            event: 消息事件对象
            task_temp: 临时任务缓存
            
        Returns:
            {"type": "text"|"image", "msg": "消息内容"}
        """
        # 添加工程
        if msg.startswith('task add'):
            return self._handle_task_add(msg, event, task_temp)

        # 删除工程
        if msg.startswith('task remove'):
            parts = msg.split(' ')
            if len(parts) != 3:
                return {"type": "text", "msg": "是/task remove <项目名字>喵~"}
            return {"type": "text", "msg": self.task_utils.remove_task(parts[2], event)}

        # 工程列表
        if msg.startswith('task list'):
            return {"type": "text", "msg": self.task_utils.get_task_list()}

        # 修改工程
        if msg.startswith('task set'):
            return self._handle_task_set(msg, event)

        # 认领材料
        if msg.startswith('task claim'):
            return self._handle_task_claim(msg, event)

        # 提交材料
        if msg.startswith('task commit'):
            return self._handle_task_commit(msg)

        # 查看工程详情
        if msg.startswith('task'):
            return await self._handle_task_query(msg)

        return {"type": "text", "msg": self.message.get_task_help_message()}
    
    def _handle_task_add(self, msg: str, event: AstrMessageEvent, task_temp: TTLCache) -> TaskResponse:
        """处理任务添加"""
        # 校验命令格式
        parts = msg.split(' ')
        if len(parts) != 7:
            return {"type": "text", "msg": "是/task add <工程名字> <0-主世界 1-地狱 2-末地> <x y z>喵~"}

        # 解析参数
        name, dimension = parts[2], parts[3]
        location = f"{parts[4]} {parts[5]} {parts[6]}"

        # 校验坐标
        is_valid, error_msg = self.validate_coordinates(location)
        if not is_valid:
            return {"type": "text", "msg": error_msg}

        # 校验是否重名
        task = self.task_utils.get_task_by_name(name)
        if task["code"] == 200:
            return {"type": "text", "msg": f"已经有{name}了喵~"}

        # 校验是否已经在创建中
        for key in task_temp:
            if task_temp[key]["name"] == name:
                if not event.is_admin():
                    return {"type": "text", "msg": f"{task_temp[key]['sender_name']}({task_temp[key]['sender_id']})已经申请创建{name}了喵~"}
                # 管理员强制创建
                task_temp.pop(key)
                break

        # 创建临时信息
        session_id = f'{event.get_group_id()}_{event.get_sender_id()}'
        return self._create_task_cache(task_temp, session_id, name, event.get_sender_name(),
                                       event.get_sender_id(), dimension, location)
    
    def _handle_task_set(self, msg: str, event: AstrMessageEvent) -> TaskResponse:
        """处理任务修改"""
        parts = msg.split(' ')
        if len(parts) != 8:
            return {"type": "text", "msg": "是: /task set <工程名字> <新工程名称> <0-主世界 1-地狱 2-末地> <x y z>喵！"}

        original_name, name, dimension = parts[2], parts[3], parts[4]
        location = f"{parts[5]} {parts[6]} {parts[7]}"

        # 校验坐标
        is_valid, error_msg = self.validate_coordinates(location)
        if not is_valid:
            return {"type": "text", "msg": error_msg}

        return {"type": "text", "msg": self.task_utils.set_task(location, dimension, original_name, name, event)}
    
    def _handle_task_claim(self, msg: str, event: AstrMessageEvent) -> TaskResponse:
        """处理材料认领"""
        parts = msg.split(' ')
        if len(parts) != 4:
            return {"type": "text", "msg": "是/task claim <工程名字> <材料编号>喵~"}
        
        task_name, material_number = parts[2], parts[3]
        return {"type": "text", "msg": self.task_utils.update_material(task_name, material_number, event)}
    
    def _handle_task_commit(self, msg: str) -> TaskResponse:
        """处理材料提交"""
        parts = msg.split(' ', 5)
        if len(parts) < 6:
            return {"type": "text", "msg": "是/task commit <工程名称> <材料序号> <n 个/组/盒> <材料所在位置/假人>喵~"}
        
        task_name, material_number, quantity_str, location = parts[2], parts[3], parts[4], parts[5]
        
        # 解析数量与单位
        individual, stack, shulker = 0, 0, 0
        
        for unit, (i, s, sh) in MATERIAL_UNIT_MAP.items():
            if quantity_str.endswith(unit):
                try:
                    count = int(quantity_str[:-len(unit)])
                    individual, stack, shulker = count * i, count * s, count * sh
                    break
                except ValueError:
                    return {"type": "text", "msg": "是/task commit <工程名称> <材料序号> <n 个/组/盒> <材料所在位置/假人>喵~"}
        else:
            # 没有单位，尝试纯数字，默认按"个"处理
            if quantity_str.isdigit():
                individual = int(quantity_str)
            else:
                return {"type": "text", "msg": "是/task commit <工程名称> <材料序号> <n 个/组/盒> <材料所在位置/假人>喵~"}
        
        return {"type": "text", "msg": self.task_utils.commit_material(
            task_name, material_number, location, individual, stack, shulker
        )}
    
    async def _handle_task_query(self, msg: str) -> TaskResponse:
        """处理任务查询"""
        parts = msg.split(' ')
        
        # task 不带参数返回帮助
        if len(parts) != 2:
            return {"type": "text", "msg": self.message.get_task_help_message()}

        # task 带名称返回工程详情（图片）
        task_name = parts[1]
        task = self.task_utils.get_task_by_name(task_name)
        if task["code"] != 200:
            return {"type": "text", "msg": f"没找到{task_name}喵~"}
        
        materia = self.task_utils.get_material_list_by_task_id(task['msg'][0][0])
        material_list = materia['msg']
        material_count = len(material_list)
        
        # 根据材料数量决定返回类型
        if material_count <= 230:
            # 200-230种材料或更少，返回单张图片
            url = await self.task_utils.render(task["msg"], material_list, filename='task.png')
            return {"type": "image", "msg": url}
        else:
            # 超过230种材料，每200种分割成一张图片
            image_urls = []
            # 每200种材料生成一张图片
            for idx, i in enumerate(range(0, material_count, 200), start=1):
                chunk = material_list[i:i + 200]
                # 为每张图片生成唯一的文件名
                filename = f'task_{idx}.png'
                url = await self.task_utils.render(task["msg"], chunk, filename=filename)
                image_urls.append(url)
            
            # 返回图片列表
            return {"type": "image_list", "msg": image_urls}
    
    def _create_task_cache(self,
                           task_temp: TTLCache,
                           session_id: str,
                           name: str,
                           sender_name: str,
                           sender_id: str,
                           dimension: str,
                           location: str) -> TaskResponse:
        """创建任务临时缓存"""
        task_temp[session_id] = {
            "name": name,
            "sender_name": sender_name,
            "sender_id": sender_id,
            "dimension": dimension,
            "location": location,
        }
        return {"type": "text", "msg": "好的喵~快发我litematic、txt、csv吧"}

    # ==================== 材料文件处理 ====================
    async def material(self, task_temp: TTLCache, event: AstrMessageEvent) -> Optional[str]:
        """处理任务材料文件上传"""
        try:
            # 尝试解析事件中的原始消息
            raw_message = event.message_obj.raw_message
            match = re.search(r'<Event, (\{.*})>', str(raw_message), re.DOTALL)
            if not match:
                return None
            
            event_dict_str = match.group(1).replace("'", '"')
            json_dict = json.loads(event_dict_str)
        except (AttributeError, json.JSONDecodeError, Exception) as e:
            logger.error(f"消息解析失败: {e}")
            return None

        # 检查消息类型
        message = json_dict.get('message')
        if not message or not isinstance(message, list) or len(message) == 0:
            return None
        
        # 只处理文件类型消息
        if message[0].get('type') != 'file':
            return None
        
        # 提取文件信息
        file_data = message[0].get('data', {})
        filename = file_data.get('file', '')
        
        # 校验文件扩展名
        if not filename.endswith(ALLOWED_FILE_EXTENSIONS):
            return None

        # 获取文件下载链接
        try:
            client = event.bot
            payloads = {
                "group_id": json_dict['group_id'],
                "file_id": file_data['file_id'],
            }
            ret = await client.api.call_action('get_group_file_url', **payloads)
        except Exception as e:
            logger.error(f"文件获取失败: {e}")
            return f'文件获取失败喵~\n{e}'
        
        # 调用任务工具处理材料文件
        session_id = f'{event.get_group_id()}_{event.get_sender_id()}'
        return self.task_utils.task_material(ret['url'], filename, session_id, task_temp)

    # ==================== 其他工具方法 ====================
    def get_image(self) -> str:
        """获取最后生成的图片路径"""
        return self.image_utils.get_last_image()
