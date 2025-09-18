from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from .utils import *

from astrbot.core.platform.sources.aiocqhttp.aiocqhttp_message_event import (
    AiocqhttpMessageEvent,
)

@register(
    "astrbot_plugin_mc_admin",
    "Xc_Star",
    "这是 MC服务器 的管理插件，支持list，珍珠炮落点计算，服务器工程坐标，备货清单，白名单管理等功能",
    "0.1",
    "https://github.com/Xc-Star/astrbot_plugin_mc_admin"
)
class McAdminPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
    
    # 注册指令的装饰器。指令名为 helloworld。注册成功后，发送 `/helloworld` 就会触发这个指令，并回复 `你好, {user_name}!`
    @filter.command("helloword")
    async def helloworld(self, event: AstrMessageEvent):
        """这是一个 hello world 指令""" # 这是 handler 的描述，将会被解析方便用户了解插件内容。建议填写。
        user_name = event.get_sender_name()
        message_str = event.message_str # 用户发的纯文本消息字符串
        message_chain = event.get_messages() # 用户所发的消息的消息链 # from astrbot.api.message_components import *
        logger.info(message_chain)
        yield event.plain_result(f"Hello, {user_name}, 你发了 {message_str}!") # 发送一条纯文本消息

    @filter.command("test")
    async def test(self, event: AstrMessageEvent, e1: MessageEventResult):
        image_utils = ImageUtils()
        path = image_utils.generate_list_image()
        yield event.image_result(path)
        
    @filter.command("mc")
    async def mc(self, event: AstrMessageEvent):
        msg = event.message_str
        command_utils = CommandUtils()
        yield event.plain_result(command_utils.mc(msg, event))

    @filter.command("loc")
    async def loc(self, event: AstrMessageEvent):
        msg = event.message_str
        command_utils = CommandUtils()
        yield event.plain_result(command_utils.loc(msg, event))

    @filter.command("list")
    async def list(self, event: AstrMessageEvent):
        command_utils = CommandUtils()
        yield event.image_result(command_utils.list())

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
