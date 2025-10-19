import os.path

from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core import AstrBotConfig

from .utils import *
from .utils.rcon_pool import close_rcon_pool
from .utils import in_enabled_groups, requires_enabled

from html2image import Html2Image
from jinja2 import Environment, FileSystemLoader

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
        self.command_utils = CommandUtils(config)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""


    # @filter.command("test")
    # async def custom_t2i_tmpl(self, event: AstrMessageEvent):
    #     templates = os.path.join(ConfigUtils(self.config).get_plugin_path(),"template")
    #     output = os.path.join(ConfigUtils(self.config).get_plugin_path(), "data")
    #     env = Environment(loader=FileSystemLoader(templates))
    #     template = env.get_template("task.html")
    #     data = {'name': 'test5', 'location': '1 1 1', 'dimension': '1', 'CreateUser': 'rename', 'MaterialList': [[{'name': '3239', 'total': 3239, 'GroupTotal': 50.61, 'BoxTotal': 1.87, 'PersonInCharge': None, 'progress': '否'}, {'name': '1782', 'total': 1782, 'GroupTotal': 27.84, 'BoxTotal': 1.03, 'PersonInCharge': None, 'progress': '否'}, {'name': '1490', 'total': 1490, 'GroupTotal': 23.28, 'BoxTotal': 0.86, 'PersonInCharge': None, 'progress': '否'}, {'name': '1416', 'total': 1416, 'GroupTotal': 22.12, 'BoxTotal': 0.82, 'PersonInCharge': None, 'progress': '否'}, {'name': '1376', 'total': 1376, 'GroupTotal': 21.5, 'BoxTotal': 0.8, 'PersonInCharge': None, 'progress': '否'}, {'name': '1122', 'total': 1122, 'GroupTotal': 17.53, 'BoxTotal': 0.65, 'PersonInCharge': None, 'progress': '否'}, {'name': '725', 'total': 725, 'GroupTotal': 11.33, 'BoxTotal': 0.42, 'PersonInCharge': None, 'progress': '否'}, {'name': '705', 'total': 705, 'GroupTotal': 11.02, 'BoxTotal': 0.41, 'PersonInCharge': None, 'progress': '否'}, {'name': '555', 'total': 555, 'GroupTotal': 8.67, 'BoxTotal': 0.32, 'PersonInCharge': None, 'progress': '否'}, {'name': '245', 'total': 245, 'GroupTotal': 3.83, 'BoxTotal': 0.14, 'PersonInCharge': None, 'progress': '否'}, {'name': '180', 'total': 180, 'GroupTotal': 2.81, 'BoxTotal': 0.1, 'PersonInCharge': None, 'progress': '否'}, {'name': '134', 'total': 134, 'GroupTotal': 2.09, 'BoxTotal': 0.08, 'PersonInCharge': None, 'progress': '否'}, {'name': '131', 'total': 131, 'GroupTotal': 2.05, 'BoxTotal': 0.08, 'PersonInCharge': None, 'progress': '否'}, {'name': '120', 'total': 120, 'GroupTotal': 1.88, 'BoxTotal': 0.07, 'PersonInCharge': None, 'progress': '否'}, {'name': '51', 'total': 51, 'GroupTotal': 0.8, 'BoxTotal': 0.03, 'PersonInCharge': None, 'progress': '否'}, {'name': '48', 'total': 48, 'GroupTotal': 0.75, 'BoxTotal': 0.03, 'PersonInCharge': None, 'progress': '否'}, {'name': '5', 'total': 5, 'GroupTotal': 0.08, 'BoxTotal': 0.0, 'PersonInCharge': None, 'progress': '否'}, {'name': '5', 'total': 5, 'GroupTotal': 0.08, 'BoxTotal': 0.0, 'PersonInCharge': None, 'progress': '否'}, {'name': '5', 'total': 5, 'GroupTotal': 0.08, 'BoxTotal': 0.0, 'PersonInCharge': None, 'progress': '否'}, {'name': '3', 'total': 3, 'GroupTotal': 0.05, 'BoxTotal': 0.0, 'PersonInCharge': None, 'progress': '否'}, {'name': '2', 'total': 2, 'GroupTotal': 0.03, 'BoxTotal': 0.0, 'PersonInCharge': None, 'progress': '否'}, {'name': '2', 'total': 2, 'GroupTotal': 0.03, 'BoxTotal': 0.0, 'PersonInCharge': None, 'progress': '否'}]]}
    #     html_content = template.render({"data":data})
    #     hti = Html2Image(output_path=output,custom_flags=['--no-sandbox', '--disable-dev-shm-usage'])
    #     hti.screenshot(html_str=html_content, save_as="output.png",size=(650,600))
    #
    #     yield event.image_result(os.path.join(output, "output.png"))
        
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
        no_upload_file_list = ConfigUtils(self.config).get_task_no_upload_file_list()
        if event.session_id in no_upload_file_list.keys():
            result = await self.command_utils.set_materia(event, no_upload_file_list[event.session_id])
            if result['code'] == 200:
                no_upload_file_list.pop(event.session_id)
                ConfigUtils(self.config).set_task_no_upload_file_list(no_upload_file_list)
                yield event.plain_result(result['msg'])
            else:
                yield
        else:
            yield

    @filter.command("task")
    @in_enabled_groups()
    async def task(self, event: AstrMessageEvent):
        msg = event.message_str
        result = await self.command_utils.task(msg, event)
        if result['type'] == "text":
            yield event.plain_result(result['msg'])
        else:
            yield event.image_result(result['msg'])


    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        # 关闭Rcon连接池
        close_rcon_pool()
