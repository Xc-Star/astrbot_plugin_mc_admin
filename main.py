from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core import AstrBotConfig
from .utils import *
import time

from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

@register(
    "astrbot_plugin_mc_admin",
    "Xc_Star",
    "这是 MC服务器 的管理插件，支持list，珍珠炮落点计算，服务器工程坐标，备货清单，白名单管理等功能",
    "0.3.2",
    "https://github.com/Xc-Star/astrbot_plugin_mc_admin"
)
class McAdminPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        self.command_utils = CommandUtils(config)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""


    # @filter.command("test")
    async def test(self, event: AstrMessageEvent):
        logger.info(self.config)
        yield event.plain_result(self.config.__str__())
        
    @filter.command("mc")
    async def mc(self, event: AstrMessageEvent):
        if event.get_group_id() not in self.config.get('enabled_groups'):
            return
        msg = event.message_str
        result = await self.command_utils.mc(msg, event)
        yield event.plain_result(result)

    @filter.command("loc")
    async def loc(self, event: AstrMessageEvent):
        if event.get_group_id() not in self.config.get('enabled_groups'):
            return
        msg = event.message_str
        result = await self.command_utils.loc(msg, event)
        yield event.plain_result(result)

    @filter.command("list")
    async def list(self, event: AstrMessageEvent):
        if event.get_group_id() not in self.config.get('enabled_groups'):
            return
        result = await self.command_utils.list_players()
        yield event.image_result(result)

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
