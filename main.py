from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core import AstrBotConfig
from .utils import *
from .utils.rcon_pool import close_rcon_pool
from .utils import in_enabled_groups, requires_enabled
import sqlite3
from cachetools import TTLCache, cached

@register(
    "astrbot_plugin_mc_admin",
    "Xc_Star",
    "这是 MC服务器 的管理插件，支持list，珍珠炮落点计算，服务器工程坐标，备货清单，白名单管理等功能",
    "0.4.0",
    "https://github.com/Xc-Star/astrbot_plugin_mc_admin"
)
class McAdminPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):

        super().__init__(context)
        self.config = config
        # 连接数据库
        self.db_conn = sqlite3.connect(ConfigUtils(self.config).get_db_path(), check_same_thread=False)
        self.command_utils = CommandUtils(config, self.db_conn)
        self.task_temp = TTLCache(maxsize=50, ttl=300)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        
    @filter.command("mc")
    @in_enabled_groups()
    async def mc(self, event: AstrMessageEvent):
        msg = event.message_str
        result = await self.command_utils.mc(msg, event)
        yield event.plain_result(result)

    @filter.command("loc")
    @in_enabled_groups()
    async def loc(self, event: AstrMessageEvent):
        msg = event.message_str
        result = await self.command_utils.loc(msg, event)
        yield event.plain_result(result)

    @filter.command("list")
    @in_enabled_groups()
    async def list_players(self, event: AstrMessageEvent):
        result = await self.command_utils.list_players()
        yield event.image_result(result)

    @filter.command("原图")
    @in_enabled_groups()
    @requires_enabled("enable_get_image", "获取原图功能暂未启用", allow_admin_bypass=True)
    async def get_background_image(self, event: AstrMessageEvent):
        yield event.image_result(self.command_utils.get_image())

    @filter.event_message_type(filter.EventMessageType.ALL)
    @in_enabled_groups()
    async def on_all_message(self, event: AstrMessageEvent):
        if event.message_obj.sender.user_id not in list(self.task_temp.keys()):
            return
        yield event.plain_result(await self.command_utils.material(self.task_temp, event))

    @filter.command("task")
    @in_enabled_groups()
    async def task(self, event: AstrMessageEvent):
        msg = event.message_str
        result = await self.command_utils.task(msg, event, self.task_temp)
        if result['type'] == "text":
            yield event.plain_result(result['msg'])
        else:
            yield event.image_result(result['msg'])

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        # 关闭Rcon连接池
        close_rcon_pool()
        # 关闭数据库连接
        self.db_conn.close()
