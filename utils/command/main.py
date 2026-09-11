import asyncio
import json
import re
from typing import Annotated, NotRequired, TypedDict

from wireup import Inject, injectable

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.core import AstrBotConfig

from ..command.helpers import (
    get_whitelist,
    parse_list_players,
    send_cca_command,
    send_command,
)
from ..config_utils import ConfigUtils
from ..config_utils.container import TaskTempCache, get_service
from ..loc.main import LocUtils
from ..loc.vo import Loc
from ..media.image import ImageUtils
from ..message import MessageUtils
from ..pearl_calculator import PearlCalculatorUtils
from ..task import TaskUtils
from ..whitelist.main import WhitelistUtils
from ..wiki import WikiUtils


class TaskResponse(TypedDict):
    """任务命令响应结构"""

    type: str  # "text" | "image" | "image_list" | "file"
    msg: str | list[str]  # 当 type 为 "image_list" 时，msg 为图片 URL 列表
    file_path: NotRequired[str]
    file_name: NotRequired[str]


class McResponse(TypedDict):
    """mc 命令响应结构"""

    type: str  # "text" | "image"
    msg: str


# 支持处理的投影材料文件后缀
ALLOWED_FILE_EXTENSIONS = (".txt", ".csv", ".litematic")

# 处理命令的正则
LOC_ADD_RE = re.compile(
    r"^loc add\s+([\w\\s]+?)\s+([012])\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)$"
)
LOC_SET_RE = re.compile(
    r"^loc set\s+([\w\\s]+?)\s+([012])\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)$"
)
MC_COMMAND_RE = re.compile(r"^mc command \w+ (.*)$")
MCDR_COMMAND_RE = re.compile(r"^(?:mcdr|dr)\s+(\S+)\s+(.+)$")


@injectable
class CommandUtils:
    """Minecraft 服务器命令工具类"""

    def __init__(
        self,
        astrbot_config: Annotated[AstrBotConfig, Inject(config="astrbot_config")],
    ):
        """初始化命令工具"""
        # 工具类初始化
        self.config_utils = get_service(ConfigUtils)
        self.message = get_service(MessageUtils)
        self.image_utils = get_service(ImageUtils)
        self.wiki_utils = get_service(WikiUtils)
        self.whitelist_utils = get_service(WhitelistUtils)
        self.loc_utils = get_service(LocUtils)
        self.task_utils = get_service(TaskUtils)
        self.task_temp = get_service(TaskTempCache)
        self.pearl_calculator_util = PearlCalculatorUtils(astrbot_config)

        # 服务器与连接池
        self.servers = self.config_utils.get_server_list()
        # cca 地址
        self.cca_url = self.config_utils.get_cca_client_config()

        # 常量
        self.PERMISSION_DENIED = "我才不听你的呢"

    async def mc(self, msg: str, event: AstrMessageEvent) -> McResponse:
        """处理 MC 相关命令"""

        # 获取操作
        parts = msg.split(" ")
        try:
            operation = parts[1]
        except Exception:
            # 返回帮助信息
            return {
                "type": "image",
                "msg": await self.image_utils.generate_help_image(
                    self.message.get_help_data()
                ),
            }

        # 检查权限
        if not event.is_admin():
            logger.warning(
                f"用户{event.get_sender_name()}({event.get_sender_id()})没有权限执行{operation}命令"
            )
            return {"type": "text", "msg": self.PERMISSION_DENIED}

        try:
            # 白名单命令
            if operation == "wl":
                if msg == "mc wl list":
                    # 返回白名单列表图片
                    wl_list = await get_whitelist(self.config_utils)
                    if len(wl_list) == 0:
                        return {"type": "text", "msg": "没有白名单喵~"}
                    sorted_wl_list = sorted(wl_list, key=lambda name: name.casefold())
                    return {
                        "type": "image",
                        "msg": await self.image_utils.generate_whitelist_image(
                            sorted_wl_list
                        ),
                    }

                if len(parts) == 4:
                    # 处理添加/移除白名单
                    msg = await self.whitelist_utils.operation_whitelist(
                        parts[2], parts[3]
                    )
                    return {"type": "text", "msg": msg}

                # 返回帮助信息
                return {"type": "text", "msg": "是 mc wl add ID 喵～"}

            # 重置白名单数据库命令
            if operation == "reset":
                await self.whitelist_utils.initialize()
                return {"type": "text", "msg": "白名单数据库重载成功喵~"}

            # mc command <服务器> <命令...>
            if operation == "command":
                # 获取服务器名
                server_name = parts[2]

                # 获取命令
                match = MC_COMMAND_RE.match(msg)
                command = match.group(1) if match else ""

                # 执行命令
                send_result = await send_command(
                    self.config_utils, server_name, command
                )
                return {"type": "text", "msg": send_result}

            return {
                "type": "text",
                "msg": "命令不对喵～\n可以用 /mc 查看帮助喵～",
            }
        except Exception as e:
            logger.error(f"执行mc命令失败: {e}")
            return {"type": "text", "msg": f"报错了喵呜 >w<\r{e}"}

    async def mcdr(self, msg: str, event: AstrMessageEvent) -> McResponse:
        """处理 MCDR HTTP 命令。"""

        # 校验用户权限
        if not event.is_admin():
            return {"type": "text", "msg": self.PERMISSION_DENIED}

        # 检查是否配置cca
        if not self.cca_url or self.cca_url == "":
            return {
                "type": "text",
                "msg": "CCA Client 还没有配置喵~",
            }

        # 校验命令格式
        match = MCDR_COMMAND_RE.match(msg.strip())
        if not match:
            logger.warning(f"MCDR命令格式校验失败: {msg}")
            return {
                "type": "text",
                "msg": "是/mcdr <服务器名> <MCDR命令>喵~",
            }
        # 拆分命令
        server_name, command = match.groups()

        # 发送MCDR命令
        try:
            send_result = await send_cca_command(
                self.cca_url, server_name, command.strip()
            )
        except Exception as e:
            logger.error(f"执行 MCDR 命令失败: {e}")
            return {"type": "text", "msg": f"执行 MCDR 命令失败喵~\n{e}"}
        return {"type": "text", "msg": send_result}

    async def broadcast_msg(self, msg: str) -> None:
        """广播消息到所有服务器"""

        async def send_broadcast(server_name: str):
            try:
                await send_command(self.config_utils, server_name, f"say {msg}")
            except Exception:
                logger.warning(f"向服务器 {server_name} 发送广播消息失败")

        # 并发发送广播消息到所有服务器，忽略发送失败的服务器
        server_list = await self.config_utils.get_online_servers_name()
        await asyncio.gather(
            *[send_broadcast(s) for s in server_list], return_exceptions=True
        )

    async def list_players(self) -> str:
        """获取所有服务器的玩家列表并生成图片"""
        bot_prefix = self.config_utils.get_bot_prefix()

        async def process_server(
            server_name: str,
        ) -> tuple[str, dict[str, list[str]]] | None:
            """处理单个服务器的玩家列表"""

            # 查询服务器在线玩家
            try:
                res = await send_command(self.config_utils, server_name, "list")
            except Exception:
                logger.warning(f"给{server_name}发送list命令失败")
                return None

            # 解析玩家列表
            players = parse_list_players(res)
            if not players:
                return server_name, {"bot_players": [], "real_players": []}

            # 根据配置选择分类方式
            if self.config_utils.enable_whitelist_compare:
                # 使用白名单工具判断是否为真人玩家
                bot_players: list[str] = []
                real_players: list[str] = []
                for p in players:
                    if await self.whitelist_utils.is_real_player(p):
                        real_players.append(p)
                    else:
                        bot_players.append(p)
            else:
                # 只校验前缀
                def is_bot_player(player_name: str) -> bool:
                    if len(player_name) < len(bot_prefix):
                        return False
                    return player_name.lower().startswith(bot_prefix.lower())

                bot_players = [p for p in players if is_bot_player(p)]
                real_players = [p for p in players if not is_bot_player(p)]

            return server_name, {
                "bot_players": bot_players,
                "real_players": real_players,
            }

        # 并发处理所有服务器
        tasks = [
            process_server(server_name)
            for server_name in await self.config_utils.get_online_servers_name()
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 汇总结果
        servers_players = {}
        for r in results:
            if isinstance(r, tuple) and len(r) == 2:
                name, data = r
                servers_players[name] = data

        # 生成图片
        image_path = await self.image_utils.generate_list_image(servers_players)
        return image_path

    async def loc(self, msg: str) -> McResponse:
        """处理位置loc命令"""

        parts = msg.split(" ")
        try:
            operation = parts[1]
        except Exception:
            # 返回帮助信息
            return {
                "type": "image",
                "msg": await self.image_utils.generate_help_image(
                    self.message.get_loc_help_data()
                ),
            }

        # 列出所有位置
        if operation == "list":
            return {"type": "text", "msg": self.loc_utils.list_loc()}

        # 添加位置
        if operation == "add":
            match = LOC_ADD_RE.match(msg)
            if not match:
                return {
                    "type": "text",
                    "msg": "是/loc add <项目名字> <0-主世界 1-地狱 2-末地> <x y z>喵~",
                }
            name, dimension, x, y, z = match.groups()
            coordinates = f"{x} {y} {z}"
            loc = Loc(name=name, dimension=int(dimension), location=coordinates)
            return {"type": "text", "msg": self.loc_utils.add_loc(loc)}

        # 删除位置
        if operation == "remove":
            if len(parts) != 3:
                return {"type": "text", "msg": "是/loc remove <项目名字>喵~"}
            return {"type": "text", "msg": self.loc_utils.remove_loc(parts[2])}

        # 修改位置
        if operation == "set":
            match = LOC_SET_RE.match(msg)
            if not match:
                return {
                    "type": "text",
                    "msg": "是/loc set <项目名字> <0-主世界 1-地狱 2-末地> <x y z>喵~",
                }
            name, dimension, x, y, z = match.groups()
            coordinates = f"{x} {y} {z}"
            # 更新位置信息
            loc = Loc(name=name, dimension=int(dimension), location=coordinates)
            return {"type": "text", "msg": self.loc_utils.set_loc(loc)}

        # 查看位置详情
        loc_name = msg.removeprefix("loc ").strip()
        loc = self.loc_utils.get_loc_by_name(loc_name)
        if not loc:
            return {
                "type": "text",
                "msg": f'没找到"{loc_name}"喵~\n可以使用 /loc 查看帮助喵～',
            }
        return {"type": "text", "msg": loc.get_info_str()}

    async def task(self, msg: str, event: AstrMessageEvent) -> TaskResponse:
        """处理任务task命令"""

        parts = msg.split(" ")
        is_admin = event.is_admin()
        try:
            operation = parts[1]
        except Exception:
            # 返回帮助信息
            return {
                "type": "image",
                "msg": await self.image_utils.generate_help_image(
                    self.message.get_task_help_data()
                ),
            }

        # 添加工程
        if operation == "add":
            # 校验命令格式
            if len(parts) != 7:
                return {
                    "type": "text",
                    "msg": "是/task add <工程名字> <0-主世界 1-地狱 2-末地> <x y z>喵~",
                }

            # 解析参数
            name, dimension = parts[2], parts[3]
            location = f"{parts[4]} {parts[5]} {parts[6]}"
            create_group_id = event.get_group_id()
            create_user_id = event.get_sender_id()
            create_user_name = event.get_sender_name()

            # 添加队列
            res = self.task_utils.handle_task_add(
                name,
                dimension,
                location,
                create_group_id,
                create_user_id,
                create_user_name,
                is_admin,
            )
            return {"type": "text", "msg": res}

        # 删除工程
        if operation == "remove":
            task_name = msg.removeprefix("task remove ").strip()
            sender_id = event.get_sender_id()
            return {
                "type": "text",
                "msg": self.task_utils.handle_task_remove(
                    task_name, sender_id, is_admin
                ),
            }

        # 工程列表
        if operation == "list":
            return {"type": "text", "msg": self.task_utils.get_task_list_str()}

        # 修改工程
        if operation == "set":
            if len(parts) != 8:
                return {
                    "type": "text",
                    "msg": "是: /task set <工程名字> <新工程名称> <0-主世界 1-地狱 2-末地> <x y z>喵！",
                }

            # 解析参数
            original_name, name, dimension = parts[2], parts[3], parts[4]
            location = f"{parts[5]} {parts[6]} {parts[7]}"
            sender_id = event.get_sender_id()
            # 执行修改
            return {
                "type": "text",
                "msg": self.task_utils.handle_task_set(
                    original_name, name, dimension, location, sender_id, is_admin
                ),
            }

        # 认领材料
        if operation == "claim":
            if len(parts) != 4:
                return {"type": "text", "msg": "是/task claim <工程名字> <材料编号>喵~"}

            # 解析参数
            task_name, material_number = parts[2], parts[3]
            recipient = event.get_sender_name()
            # 执行认领
            return {
                "type": "text",
                "msg": self.task_utils.handle_task_claim(
                    task_name, material_number, recipient
                ),
            }

        # 提交材料
        if operation == "commit":
            return {"type": "text", "msg": self.task_utils.handle_task_commit(msg)}

        # 导出 Excel 文件
        if operation == "export":
            task_name = msg.removeprefix("task export ").strip()
            # 直接开导
            excel_file_path, file_name, success = self.task_utils.export_task(task_name)
            if not success:
                return {
                    "type": "text",
                    "msg": f"导出 Excel 文件失败: {task_name} 不存在喵~",
                }
            return {
                "type": "file",
                "msg": "",
                "file_path": excel_file_path,
                "file_name": file_name,
            }

        # 查看工程详情
        task_name = msg.removeprefix("task ").strip()
        return await self._handle_task_query(task_name)

    async def _handle_task_query(self, task_name: str) -> TaskResponse:
        """处理任务查询"""

        # 校验是否存在
        task_res = self.task_utils.get_task_by_name(task_name)
        success = task_res.get("success")
        task = task_res.get("data")
        if not success:
            return {
                "type": "text",
                "msg": f"没找到{task_name}喵~\n可以用 /task 查看帮助喵~",
            }

        # 获取材料列表
        materia = self.task_utils.get_material_list_by_task_id(task[0][0])
        material_list = materia["msg"]
        material_count = len(material_list)

        # 根据配置决定生成方式
        if self.config_utils.enable_big_task_image:
            # 生成一张大图，所有列并列显示
            url = await self.task_utils.render(task, material_list, use_big_image=True)
            return {"type": "image", "msg": url}
        else:
            # 生成多张图片，每200种材料一张
            if material_count <= 200:
                # 200种材料或更少，返回单张图片
                url = await self.task_utils.render(
                    task, material_list, use_big_image=False
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
                        task, chunk, filename=filename, use_big_image=False
                    )
                    image_urls.append(url)

                # 返回图片列表
                return {"type": "image_list", "msg": image_urls}

    async def material(self, event: AstrMessageEvent) -> str | None:
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
        logger.info("开始执行投影处理任务")
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
        return self.task_utils.handle_task_material(ret["url"], filename, session_id)

    def get_image(self) -> str:
        """获取最后生成的图片路径"""
        return self.image_utils.get_last_image()

    def get_random_image(self):
        """获取一张随机图"""
        return self.image_utils.get_random_background_image()

    async def zz(self, msg: str) -> McResponse:
        """处理计算珍珠方法"""
        # 校验命令
        position = msg.split()
        if len(position) != 3:
            return {"type": "text", "msg": "是 /zz <X目标坐标> <Z目标坐标> 喵~"}

        # 校验目标坐标
        try:
            x = int(position[1])
            z = int(position[2])
        except ValueError:
            logger.warning(f"目标坐标格式错误: x: {position[1]}, z: {position[2]}")
            return {"type": "text", "msg": "是 /zz <X目标坐标> <Z目标坐标> 喵~"}

        # 计算
        success, data = await self.pearl_calculator_util.pearl_calculator(x, z)
        if not success:
            logger.warning(f"珍珠炮计算失败: {data}")
            return {"type": "text", "msg": data}
        image_path = await self.image_utils.generate_zz_image(data)
        return {"type": "image", "msg": image_path}

    async def wiki(self, question: str) -> McResponse:
        """处理 Wiki 查询命令"""
        if not self.wiki_utils:
            return {"type": "text", "msg": "Wiki 功能未初始化喵~"}
        answer = await self.wiki_utils.query_wiki(question)
        return {"type": "text", "msg": answer}
