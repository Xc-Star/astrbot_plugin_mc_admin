import asyncio
import json
import re
import sqlite3
from typing import Optional, List, Dict, Tuple, TypedDict

import httpx
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.core import AstrBotConfig
from cachetools import TTLCache

from ..command.helpers import (
    PERMISSION_DENIED,
    LOC_ADD_RE,
    LOC_SET_RE,
    MC_COMMAND_RE,
    MCDR_COMMAND_RE,
    find_server_by_name,
    send_command,
    send_mcdr_command,
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
from ..task import TaskUtils
from ..whitelist.main import WhitelistUtils
from ..pearl_calculator import PearlCalculatorUtils
from ..wiki import WikiUtils


# ==================== 类型定义 ====================
class TaskResponse(TypedDict):
    """任务命令响应结构"""

    type: str  # "text" | "image" | "image_list"
    msg: str | list[str]  # 当 type 为 "image_list" 时，msg 为图片 URL 列表


class McResponse(TypedDict):
    """mc 命令响应结构"""

    type: str  # "text" | "image"
    msg: str


# ==================== 常量定义 ====================
# Minecraft 坐标边界
MC_COORD_X_MIN, MC_COORD_X_MAX = -30000000, 30000000
MC_COORD_Y_MIN, MC_COORD_Y_MAX = -64, 368
MC_COORD_Z_MIN, MC_COORD_Z_MAX = -30000000, 30000000

# 支持的文件后缀
ALLOWED_FILE_EXTENSIONS = (".txt", ".csv", ".litematic")

# 材料单位映射
MATERIAL_UNIT_MAP = {
    "个": (1, 0, 0),
    "组": (0, 1, 0),
    "盒": (0, 0, 1),
}


class CommandUtils:
    """Minecraft 服务器命令工具类"""

    def __init__(self, config: AstrBotConfig, conn: sqlite3.Connection, context=None):
        """初始化命令工具"""
        # 工具类初始化
        self.config_utils = ConfigUtils(config)
        self.message = MessageUtils()
        self.image_utils = ImageUtils(self.config_utils)
        self.loc_utils = LocUtils(conn)  # 使用数据库存储
        self.task_utils = TaskUtils(self.config_utils, conn, self.image_utils)
        self.pearl_calculator_util = PearlCalculatorUtils(config)
        self.wiki_utils = WikiUtils(context) if context else None

        # 服务器与连接池
        self.servers = self.config_utils.get_server_list()

        # 白名单工具
        self.whitelist_utils = WhitelistUtils(
            conn, self.servers, self.config_utils.get_bot_prefix()
        )

        # 常量
        self.PERMISSION_DENIED = PERMISSION_DENIED

    # ==================== MC 命令处理 ====================
    async def mc(self, msg: str, event: AstrMessageEvent) -> McResponse:
        """处理 MC 相关命令"""
        # 优先处理白名单命令
        if msg.startswith("mc wl"):
            logger.info(f"开始执行mc wl命令")
            parts = msg.split()
            command = " ".join(parts[1:])
            return await self.wl(command, event)

        if msg.startswith("mc status"):
            """获取服务器状态"""
            logger.info(f"开始执行mc status命令")
            async def get_server_status(
                    server: Dict,
            ) -> Optional[Tuple[str, bool]]:
                """处理单个服务器的状态"""
                try:
                    await send_command(server, "list")
                    return server["name"], True
                except Exception:
                    return server["name"], False

            # 并发处理所有服务器
            tasks = [get_server_status(s) for s in self.servers]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # 汇总结果
            servers_status: Dict[str, bool] = {}
            for r in results:
                if isinstance(r, tuple) and len(r) == 2:
                    name, status = r
                    servers_status[name] = status

            # 生成状态图片
            image_path = await self.image_utils.generate_status_image(servers_status)
            return {"type": "image", "msg": image_path}

        if msg.startswith("mc reset"):
            logger.info(f"开始执行mc reset命令")
            if not event.is_admin():
                logger.warning(f"用户{event.get_sender_name()}({event.get_sender_id()})没有权限执行mc reset命令")
                return {"type": "text", "msg": self.PERMISSION_DENIED}
            parts = msg.split()
            command = " ".join(parts[2:])
            if command == "wldb":
                logger.info(f"开始执行mc reset wldb命令")
                await self.whitelist_utils.initialize()
                return {"type": "text", "msg": "白名单数据库重载成功喵~"}

        arr = msg.split(" ")

        # mc command <服务器> <命令...>
        if len(arr) >= 3 and arr[1] == "command":
            logger.info(f"开始执行mc command命令")
            if not event.is_admin():
                logger.warning(f"用户{event.get_sender_name()}({event.get_sender_id()})没有权限执行mc command命令")
                return {"type": "text", "msg": self.PERMISSION_DENIED}
            server = find_server_by_name(self.servers, arr[2])
            if server is None:
                logger.warning(f"找不到服务器: {arr[2]}")
                return {"type": "text", "msg": "找不到服务器喵~"}
            match = MC_COMMAND_RE.match(msg)
            command = match.group(1) if match else ""
            logger.info(f"开始执行mc command命令: 服务器: {arr[2]}, 命令: {command}")
            send_result = await send_command(server, command)
            logger.info(f"mc command命令执行结果: {send_result}")
            return {"type": "text", "msg": send_result}

        logger.info(f"mc命令未匹配到任何命令, 返回帮助信息")
        help_data = self.message.get_help_data()
        help_image_path = await self.image_utils.generate_help_image(help_data)
        return {"type": "image", "msg": help_image_path}

    async def mcdr(self, msg: str, event: AstrMessageEvent) -> McResponse:
        """处理 MCDR HTTP 命令。"""
        if not event.is_admin():
            return {"type": "text", "msg": self.PERMISSION_DENIED}

        match = MCDR_COMMAND_RE.match(msg.strip())
        if not match:
            logger.warning(f"MCDR命令格式校验失败: {msg}")
            return {
                "type": "text",
                "msg": "是/mcdr <服务器名> <MCDR命令>喵~",
            }

        server_name, command = match.groups()
        server = find_server_by_name(self.servers, server_name)
        if server is None:
            logger.warning(f"没找到服务器: {server_name}")
            return {"type": "text", "msg": f'没找到"{server_name}"喵~'}

        if not server.get("has_mcdr"):
            logger.warning(f"服务器{server_name}还没有配置 MCDR 接口")
            return {
                "type": "text",
                "msg": f"服务器{server_name}还没有配置 MCDR 接口喵~",
            }

        try:
            send_result = await send_mcdr_command(server, command.strip())
        except httpx.HTTPStatusError as e:
            logger.warning(f"MCDR 接口请求失败: {e}")
            return {
                "type": "text",
                "msg": f"MCDR 接口请求失败喵~\nHTTP {e.response.status_code}",
            }
        except httpx.HTTPError as e:
            logger.warning(f"MCDR 接口连接失败: {e}")
            return {"type": "text", "msg": f"MCDR 接口连接失败喵~\n{e}"}
        except ValueError as e:
            logger.warning(f"MCDR 命令格式错误: {e}")
            return {"type": "text", "msg": str(e)}
        except Exception as e:
            logger.error(f"执行 MCDR 命令失败: {e}")
            return {"type": "text", "msg": f"执行 MCDR 命令失败喵~\n{e}"}

        return {"type": "text", "msg": send_result}
    
    async def broadcast_msg(self, msg: str) -> None:
        """广播消息到所有服务器"""
        async def send_broadcast(server: Dict):
            try:
                await send_command(server, f'say {msg}')
            except Exception:
                logger.warning(f"向服务器 {server['name']} 发送广播消息失败")
            
        # 并发发送广播消息到所有服务器，忽略发送失败的服务器
        await asyncio.gather(*[send_broadcast(s) for s in self.servers], return_exceptions=True)

    # ==================== 玩家列表 ====================
    async def list_players(self) -> str:
        """获取所有服务器的玩家列表并生成图片"""
        bot_prefix = self.config_utils.get_bot_prefix()

        async def process_server(
            server: Dict,
        ) -> Optional[Tuple[str, Dict[str, List[str]]]]:
            """处理单个服务器的玩家列表"""
            try:
                res = await send_command(server, "list")
                logger.debug(f"给{server['name']}发送list命令结果: {res}")
            except Exception:
                logger.warning(f"给{server['name']}发送list命令失败")
                return None

            players = parse_list_players(res)
            if not players:
                return server["name"], {"bot_players": [], "real_players": []}

            # 根据配置选择分类方式
            if self.config_utils.enable_whitelist_compare:
                # 使用白名单工具判断是否为真人玩家
                logger.debug(f"使用白名单工具判断是否为真人玩家")
                bot_players: List[str] = []
                real_players: List[str] = []
                for p in players:
                    if await self.whitelist_utils.is_real_player(p):
                        logger.debug(f"判断{p}为真人玩家")
                        real_players.append(p)
                    else:
                        logger.debug(f"判断{p}为机器人玩家")
                        bot_players.append(p)
            else:
                bot_players, real_players = split_players_by_prefix(players, bot_prefix)

            return server["name"], {
                "bot_players": bot_players,
                "real_players": real_players,
            }

        # 并发处理所有服务器
        logger.info(f"并发给所有服务器发送list命令")
        tasks = [process_server(s) for s in self.servers]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        logger.debug(f"并发给所有服务器发送list命令结果: {results}")

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
            if not (
                MC_COORD_X_MIN <= x <= MC_COORD_X_MAX
                and MC_COORD_Z_MIN <= z <= MC_COORD_Z_MAX
                and MC_COORD_Y_MIN <= y <= MC_COORD_Y_MAX
            ):
                return False, "坐标不可以太大喵~"

            return True, ""
        except ValueError:
            return False, "坐标是整数喵~"

    # ==================== 白名单管理 ====================
    async def wl(self, msg: str, event: AstrMessageEvent) -> McResponse:
        """处理白名单命令"""
        # 权限检查
        if not event.is_admin():
            logger.warning(f"用户{event.get_sender_name()}({event.get_sender_id()})没有权限执行wl命令")
            return {"type": "text", "msg": self.PERMISSION_DENIED}

        # 查询白名单列表
        if msg == "wl list":
            logger.info(f"开始执行wl list命令")
            return await self._handle_wl_list()

        # 解析命令
        arr = msg.split(" ")
        if len(arr) != 3:
            logger.warning(f"wl命令格式错误: {msg}")
            return {"type": "text", "msg": self.message.get_help_message()}

        # 白名单添加/移除操作
        if arr[1] in ("add", "remove"):
            logger.info(f"开始执行wl {arr[1]}命令")
            # return await self._handle_wl_operation(arr[1], arr[2])
            success, message = await self.whitelist_utils.operation_whitelist(
                arr[1], arr[2]
            )
            if success:
                logger.info(f"wl {arr[1]}命令成功, 用户名: {arr[2]}")
                return {"type": "text", "msg": message}
            else:
                logger.warning(f"wl {arr[1]}命令失败, 用户名: {arr[2]}")
                return {"type": "text", "msg": message}

        logger.warning(f"发送rcon命令添加白名单失败: 未知错误! 操作: {arr[1]}, 用户名: {arr[2]}")
        return {"type": "text", "msg": "未知错误喵~"}

    async def _handle_wl_list(self) -> McResponse:
        """处理白名单列表查询"""
        wl_list = await get_whitelist(self.servers)
        if len(wl_list) == 0:
            return {"type": "text", "msg": "没有白名单喵~"}

        sorted_wl_list = sorted(wl_list, key=lambda name: name.casefold())
        image_path = await self.image_utils.generate_whitelist_image(sorted_wl_list)
        return {"type": "image", "msg": image_path}

    # async def _handle_wl_operation(self, operation: str, player_name: str) -> str:
    #     """处理白名单添加/移除操作"""
    #     async def do_op(server: Dict):
    #         try:
    #             await send_command(server, f'whitelist {operation} {player_name}')
    #         except Exception:
    #             pass
    #
    #     await asyncio.gather(*[do_op(s) for s in self.servers], return_exceptions=True)
    #     method = '添加到' if operation == 'add' else '移除'
    #     return f'已将{player_name}{method}白名单喵~'

    # ==================== 位置管理 ====================
    async def loc(self, msg: str, event: AstrMessageEvent) -> McResponse:
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
        if msg.startswith("loc list"):
            logger.info(f"开始执行loc list命令: {msg}")
            return {"type": "text", "msg": self.loc_utils.list_loc()}

        # 添加位置
        if msg.startswith("loc add"):
            logger.info(f"开始执行loc add命令: {msg}")
            return {"type": "text", "msg": self._handle_loc_add(msg)}

        # 删除位置
        if msg.startswith("loc remove"):
            logger.info(f"开始执行loc remove命令: {msg}")
            parts = msg.split(" ")
            if len(parts) != 3:
                logger.warning(f"loc remove命令格式错误: {msg}")
                return {"type": "text", "msg": "是/loc remove <项目名字>喵"}
            return {"type": "text", "msg": self.loc_utils.remove_loc(parts[2])}

        # 修改位置
        if msg.startswith("loc set"):
            logger.info(f"开始执行loc set命令: {msg}")
            return {"type": "text", "msg": self._handle_loc_set(msg)}

        # 查看位置详情
        if msg.startswith("loc "):
            logger.info(f"开始执行loc query命令: {msg}")
            return {"type": "text", "msg": self._handle_loc_query(msg)}

        logger.warning(f"loc命令格式错误, 执行默认帮助命令: {msg}")
        help_data = self.message.get_loc_help_data()
        help_image_path = await self.image_utils.generate_help_image(
            help_data, filename="loc_help.png"
        )
        return {"type": "image", "msg": help_image_path}

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
        parts = msg.split(" ")
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
    async def task(
        self, msg: str, event: AstrMessageEvent, task_temp: TTLCache
    ) -> TaskResponse:
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
        if msg.startswith("task add"):
            logger.info(f"开始执行task add命令, 添加标识缓存")
            return self._handle_task_add(msg, event, task_temp)

        # 删除工程
        if msg.startswith("task remove"):
            parts = msg.split(" ")
            if len(parts) != 3:
                logger.warning(f"task remove命令格式错误: {msg}")
                return {"type": "text", "msg": "是/task remove <项目名字>喵~"}
            logger.info(f"开始执行删除工程命令: {parts[2]}")
            return {"type": "text", "msg": self.task_utils.remove_task(parts[2], event)}

        # 工程列表
        if msg.startswith("task list"):
            logger.info(f"开始执行获取工程列表命令")
            return {"type": "text", "msg": self.task_utils.get_task_list()}

        # 修改工程
        if msg.startswith("task set"):
            logger.info(f"开始执行修改工程命令")
            return self._handle_task_set(msg, event)

        # 认领材料
        if msg.startswith("task claim"):
            logger.info(f"开始执行认领材料命令")
            return self._handle_task_claim(msg, event)

        # 提交材料
        if msg.startswith("task commit"):
            logger.info(f"开始执行提交材料命令")
            return self._handle_task_commit(msg)

        # 导出 Excel 文件
        if msg.startswith("task export"):
            logger.info(f"开始执行导出 Excel 文件命令")
            return self._handle_task_export(msg)

        # 查看工程详情
        if msg.startswith("task"):
            logger.info(f"开始执行查看工程详情命令")
            return await self._handle_task_query(msg)

        logger.warning(f"task命令未匹配到任何命令, 返回帮助信息")
        help_data = self.message.get_task_help_data()
        help_image_path = await self.image_utils.generate_help_image(
            help_data, filename="task_help.png"
        )
        return {"type": "image", "msg": help_image_path}

    def _handle_task_add(
        self, msg: str, event: AstrMessageEvent, task_temp: TTLCache
    ) -> TaskResponse:
        """处理任务添加"""
        # 校验命令格式
        parts = msg.split(" ")
        if len(parts) != 7:
            logger.warning(f"task add命令格式错误: {msg}")
            return {
                "type": "text",
                "msg": "是/task add <工程名字> <0-主世界 1-地狱 2-末地> <x y z>喵~",
            }

        logger.info(f"开始执行添加工程命令: name: {parts[2]}, dimension: {parts[3]}, location: {parts[4]} {parts[5]} {parts[6]}")
        # 解析参数
        name, dimension = parts[2], parts[3]
        location = f"{parts[4]} {parts[5]} {parts[6]}"

        # 校验坐标
        is_valid, error_msg = self.validate_coordinates(location)
        if not is_valid:
            logger.warning(f"坐标校验失败: {error_msg}")
            return {"type": "text", "msg": error_msg}

        # 校验是否重名
        task = self.task_utils.get_task_by_name(name)
        if task["code"] == 200:
            logger.warning(f"{name}已存在")
            return {"type": "text", "msg": f"已经有{name}了喵~"}

        # 校验是否已经在创建中
        for key in task_temp:
            if task_temp[key]["name"] == name:
                if not event.is_admin():
                    logger.warning(f"{task_temp[key]['sender_name']}({task_temp[key]['sender_id']})已经申请创建{name}了")
                    return {
                        "type": "text",
                        "msg": f"{task_temp[key]['sender_name']}({task_temp[key]['sender_id']})已经申请创建{name}了喵~",
                    }
                # 管理员强制创建
                logger.info(f"管理员{event.get_sender_name()}({event.get_sender_id()})强制创建{name}")
                task_temp.pop(key)
                break

        # 创建临时信息
        session_id = f"{event.get_group_id()}_{event.get_sender_id()}"
        return self._create_task_cache(
            task_temp,
            session_id,
            name,
            event.get_sender_name(),
            event.get_sender_id(),
            dimension,
            location,
        )

    def _handle_task_set(self, msg: str, event: AstrMessageEvent) -> TaskResponse:
        """处理任务修改"""
        parts = msg.split(" ")
        if len(parts) != 8:
            logger.warning(f"task set命令格式错误: {msg}")
            return {
                "type": "text",
                "msg": "是: /task set <工程名字> <新工程名称> <0-主世界 1-地狱 2-末地> <x y z>喵！",
            }

        logger.info(f"开始执行修改工程命令: original_name: {parts[2]}, name: {parts[3]}, dimension: {parts[4]}, location: {parts[5]} {parts[6]} {parts[7]}")
        original_name, name, dimension = parts[2], parts[3], parts[4]
        location = f"{parts[5]} {parts[6]} {parts[7]}"

        # 校验坐标
        is_valid, error_msg = self.validate_coordinates(location)
        if not is_valid:
            logger.warning(f"坐标校验失败: {error_msg}")
            return {"type": "text", "msg": error_msg}

        return {
            "type": "text",
            "msg": self.task_utils.set_task(
                location, dimension, original_name, name, event
            ),
        }

    def _handle_task_claim(self, msg: str, event: AstrMessageEvent) -> TaskResponse:
        """处理材料认领"""
        parts = msg.split(" ")
        if len(parts) != 4:
            logger.warning(f"task claim命令格式错误: {msg}")
            return {"type": "text", "msg": "是/task claim <工程名字> <材料编号>喵~"}

        logger.info(f"{parts[2]}认领材料{parts[3]}号")
        task_name, material_number = parts[2], parts[3]
        return {
            "type": "text",
            "msg": self.task_utils.update_material(task_name, material_number, event),
        }

    def _handle_task_commit(self, msg: str) -> TaskResponse:
        """处理材料提交"""
        parts = msg.split(" ", 5)
        if len(parts) < 6:
            logger.warning(f"task commit命令格式错误: {msg}")
            return {
                "type": "text",
                "msg": "是/task commit <工程名称> <材料序号> <n 个/组/盒> <材料所在位置/假人>喵~",
            }

        logger.info(f"开始执行提交材料命令: task_name: {parts[2]}, material_number: {parts[3]}, quantity_str: {parts[4]}, location: {parts[5]}")
        task_name, material_number, quantity_str, location = (
            parts[2],
            parts[3],
            parts[4],
            parts[5],
        )

        # 解析数量与单位
        individual, stack, shulker = 0, 0, 0

        for unit, (i, s, sh) in MATERIAL_UNIT_MAP.items():
            if quantity_str.endswith(unit):
                try:
                    count = int(quantity_str[: -len(unit)])
                    individual, stack, shulker = count * i, count * s, count * sh
                    break
                except ValueError:
                    logger.warning(f"材料数量格式错误: {quantity_str}")
                    return {
                        "type": "text",
                        "msg": "是/task commit <工程名称> <材料序号> <n 个/组/盒> <材料所在位置/假人>喵~",
                    }
        else:
            # 没有单位，尝试纯数字，默认按"个"处理
            if quantity_str.isdigit():
                individual = int(quantity_str)
            else:
                logger.warning(f"材料数量格式错误: {quantity_str}")
                return {
                    "type": "text",
                    "msg": "是/task commit <工程名称> <材料序号> <n 个/组/盒> <材料所在位置/假人>喵~",
                }

        return {
            "type": "text",
            "msg": self.task_utils.commit_material(
                task_name, material_number, location, individual, stack, shulker
            ),
        }

    def _handle_task_export(self, msg: str) -> TaskResponse:
        """处理导出 Excel 文件"""
        parts = msg.split(" ")
        if len(parts) != 3:
            logger.warning(f"task export命令格式错误: {msg}")
            return {"type": "text", "msg": "是/task export <工程名字>喵~"}

        task_name = parts[2]
        excel_file_path, file_name, code = self.task_utils.export_task(task_name)
        if code != 200:
            logger.warning(f"导出 Excel 文件失败: {task_name}")
            return {"type": "text", "msg": f"导出 Excel 文件失败: {task_name} 不存在喵～"}
        return {"type": "file", "file_path": excel_file_path, "file_name": file_name}

    async def _handle_task_query(self, msg: str) -> TaskResponse:
        """处理任务查询"""
        parts = msg.split(" ")

        # task 不带参数返回帮助
        if len(parts) != 2:
            logger.info(f"task query命令不带参数, 返回帮助信息")
            help_data = self.message.get_task_help_data()
            help_image_path = await self.image_utils.generate_help_image(
                help_data, filename="task_help.png"
            )
            return {"type": "image", "msg": help_image_path}

        # task 带名称返回工程详情（图片）
        task_name = parts[1]
        task = self.task_utils.get_task_by_name(task_name)
        if task["code"] != 200:
            logger.warning(f"{task_name}不存在")
            return {"type": "text", "msg": f"没找到{task_name}喵~"}

        logger.info(f"开始执行查询工程详情命令: task_name: {task_name}")
        materia = self.task_utils.get_material_list_by_task_id(task["msg"][0][0])
        material_list = materia["msg"]
        material_count = len(material_list)

        # 根据配置决定生成方式
        if self.config_utils.enable_big_task_image:
            # 生成一张大图，所有列并列显示
            url = await self.task_utils.render(
                task["msg"], material_list, use_big_image=True
            )
            return {"type": "image", "msg": url}
        else:
            # 生成多张图片，每200种材料一张
            if material_count <= 200:
                # 200种材料或更少，返回单张图片
                url = await self.task_utils.render(
                    task["msg"], material_list, use_big_image=False
                )
                return {"type": "image", "msg": url}
            else:
                # 超过200种材料，每200种分割成一张图片
                image_urls = []
                # 每200种材料生成一张图片
                for idx, i in enumerate(range(0, material_count, 200), start=1):
                    chunk = material_list[i : i + 200]
                    # 为每张图片生成唯一的文件名
                    filename = f"task_{idx}.png"
                    url = await self.task_utils.render(
                        task["msg"], chunk, filename=filename, use_big_image=False
                    )
                    image_urls.append(url)

                # 返回图片列表
                return {"type": "image_list", "msg": image_urls}

    def _create_task_cache(
        self,
        task_temp: TTLCache,
        session_id: str,
        name: str,
        sender_name: str,
        sender_id: str,
        dimension: str,
        location: str,
    ) -> TaskResponse:
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
    async def material(
        self, task_temp: TTLCache, event: AstrMessageEvent
    ) -> Optional[str]:
        """处理任务材料文件上传"""
        try:
            # 尝试解析事件中的原始消息
            raw_message = event.message_obj.raw_message
            match = re.search(r"<Event, (\{.*})>", str(raw_message), re.DOTALL)
            if not match:
                return None

            event_dict_str = match.group(1).replace("'", '"')
            json_dict = json.loads(event_dict_str)
        except (AttributeError, json.JSONDecodeError, Exception) as e:
            logger.error(f"消息解析失败: {e}")
            return None

        # 检查消息类型
        message = json_dict.get("message")
        if not message or not isinstance(message, list) or len(message) == 0:
            return None

        # 只处理文件类型消息
        if message[0].get("type") != "file":
            return None

        # 提取文件信息
        logger.info(f"开始执行投影处理任务")
        file_data = message[0].get("data", {})
        filename = file_data.get("file", "")

        # 校验文件扩展名
        if not filename.endswith(ALLOWED_FILE_EXTENSIONS):
            logger.warning(f"文件扩展名不支持: {filename}")
            return None

        # 获取文件下载链接
        try:
            client = event.bot
            payloads = {
                "group_id": json_dict["group_id"],
                "file_id": file_data["file_id"],
            }
            ret = await client.api.call_action("get_group_file_url", **payloads)
        except Exception as e:
            logger.error(f"文件获取失败: {e}")
            return f"文件获取失败喵~\n{e}"

        # 调用任务工具处理材料文件
        session_id = f"{event.get_group_id()}_{event.get_sender_id()}"
        return self.task_utils.task_material(
            ret["url"], filename, session_id, task_temp
        )

    # ==================== 其他工具方法 ====================
    def get_image(self) -> str:
        """获取最后生成的图片路径"""
        return self.image_utils.get_last_image()

    def get_random_image(self):
        return self.image_utils.get_random_background_image()

    async def zz(self, msg: str, event) -> McResponse:
        """
        处理计算珍珠方法
        """
        position = msg.split()
        if len(position) != 3:
            logger.warning(f"zz命令格式错误: {msg}")
            return {"type": "text", "msg": "是 /zz <X目标坐标> <Z目标坐标> 喵～"}

        try:
            x = int(position[1])
            z = int(position[2])
        except ValueError:
            logger.warning(f"目标坐标格式错误: x: {position[1]}, z: {position[2]}")
            return {"type": "text", "msg": "是 /zz <X目标坐标> <Z目标坐标> 喵～"}

        res = await self.pearl_calculator_util.pearl_calculator(x, z)
        if res.get("msg") != "success":
            logger.warning(f"珍珠炮计算失败: {res.get('msg', '')}")
            return {"type": "text", "msg": res.get("msg", "")}
        image_path = await self.image_utils.generate_zz_image(res.get("data", {}))
        return {"type": "image", "msg": image_path}

    # ==================== Wiki 查询 ====================
    async def wiki(self, question: str) -> McResponse:
        """处理 Wiki 查询命令

        Args:
            question: 用户的 Minecraft 相关问题

        Returns:
            {"type": "text", "msg": "回答内容"}
        """
        if not self.wiki_utils:
            return {"type": "text", "msg": "Wiki 功能未初始化喵~"}
        answer = await self.wiki_utils.query_wiki(question)
        return {"type": "text", "msg": answer}
