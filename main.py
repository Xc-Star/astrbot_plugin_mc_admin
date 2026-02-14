import asyncio
import sys
from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
from astrbot.core import AstrBotConfig
from .utils.command.main import CommandUtils
from .utils.decorators import in_enabled_groups, requires_enabled
from .utils.db import DbUtils
from cachetools import TTLCache

@register(
    "astrbot_plugin_mc_admin",
    "Xc_Star",
    "这是 MC服务器 的管理插件，支持list，珍珠炮落点计算，服务器工程坐标，备货清单，白名单管理等功能",
    "0.4.12",
    "https://github.com/Xc-Star/astrbot_plugin_mc_admin"
)
class McAdminPlugin(Star):
    # TODO: 珍珠炮落点计算
    # TODO: 帮助信息做张图来返回
    # TODO: mc wl list做张图返回
    def __init__(self, context: Context, config: AstrBotConfig):

        super().__init__(context)
        self.config = config
        # 连接数据库
        self.db_util = DbUtils()
        self.command_utils = CommandUtils(config, self.db_util.get_conn())
        self.task_temp = TTLCache(maxsize=50, ttl=300)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        # 检查并安装 Playwright Chromium
        await self._ensure_playwright_installed()
    
    async def _ensure_playwright_installed(self):
        """确保 Playwright Chromium 已安装
        
        该方法会检查并自动安装 Playwright Chromium 浏览器。
        如果已安装，会快速跳过；如果未安装，会自动执行安装命令。
        """
        logger.info("检查 Playwright Chromium 是否已安装...")
        
        # 直接执行 playwright install chromium 命令
        # Playwright 会检查是否已安装，如果已安装会立即返回
        logger.warning("正在检查并安装 Playwright Chromium...")
        logger.warning("注意：如果未安装，首次安装可能需要几分钟时间，请耐心等待...")
        
        try:
            # 执行 playwright install chromium 命令
            process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "playwright", "install", "chromium",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            
            assert process.stdout is not None
            installed = False
            async for line in process.stdout:
                output = line.decode().strip()
                logger.info(output)
                # 检查是否显示已安装的消息
                if "is already installed" in output.lower() or "已经安装" in output:
                    installed = True
            
            await process.wait()
            
            if process.returncode != 0:
                logger.error(f"安装 Playwright Chromium 失败，错误码: {process.returncode}")
                logger.error("请手动执行: playwright install chromium")
            else:
                if installed:
                    logger.info("Playwright Chromium 已安装")
                else:
                    logger.info("Playwright Chromium 安装成功")
        except FileNotFoundError:
            logger.error("未找到 playwright 命令，请先安装: pip install playwright")
        except Exception as install_error:
            logger.error(f"安装 Playwright Chromium 时出错: {install_error}")
            logger.error("请手动执行: playwright install chromium")

    # @filter.command("test")
    async def test(self, event: AstrMessageEvent):
        logger.info(self.config)
        msg = f"keys：{str(list(self.task_temp.keys()))},values：{str(list(self.task_temp.values()))}"
        yield event.plain_result(msg)
        
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
    @requires_enabled("enable_get_last_background_image", "获取原图功能暂未启用", allow_admin_bypass=True)
    async def get_background_image(self, event: AstrMessageEvent):
        yield event.image_result(self.command_utils.get_image())

    @filter.command("抽卡")
    @in_enabled_groups()
    @requires_enabled("enable_background_image_random", "抽卡功能暂未启用", allow_admin_bypass=True)
    async def get_random_image(self, event: AstrMessageEvent):
        yield event.image_result(self.command_utils.get_random_image())

    @filter.event_message_type(filter.EventMessageType.ALL)
    @in_enabled_groups()
    async def on_all_message(self, event: AstrMessageEvent):
        if f'{event.get_group_id()}_{event.get_sender_id()}' not in list(self.task_temp.keys()):
            return
        res = await self.command_utils.material(self.task_temp, event)
        if res is not None:
            yield event.plain_result(res)

    @filter.command("task")
    @in_enabled_groups()
    async def task(self, event: AstrMessageEvent):
        msg = event.message_str
        result = await self.command_utils.task(msg, event, self.task_temp)
        if result['type'] == "text":
            yield event.plain_result(result['msg'])
        elif result['type'] == "image":
            yield event.image_result(result['msg'])
        elif result['type'] == "image_list":
            for img in result['msg']:
                yield event.image_result(img)

    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
        # 关闭 browser 实例（使用 ImageUtils 的，TaskUtils 只是转发）
        await self.command_utils.image_utils.close_browser()
        # 关闭数据库连接
        self.db_util.close()
