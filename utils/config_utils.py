import base64
import os
import json
import pathlib

from astrbot.core import AstrBotConfig
from astrbot.api import logger


class ConfigUtils:

    def __init__(self, config: AstrBotConfig):
        servers = config.get('servers')

        # 回复的群聊
        self.enable_groups = config.get('enabled_groups')

        # bot前缀
        self.bot_prefix = config.get('bot_prefix')

        # 服务器列表数据
        self.server_list = list()
        for server in servers:
            server_info = str(server).split(':')
            self.server_list.append({
                "name": server_info[0],
                "host": server_info[1],
                "port": server_info[2],
                "password": server_info[3]
            })

        # 是否开启白名单比对
        self.enable_whitelist_compare = config.get('enable_whitelist_compare')

        # 是否开启自定义背景图
        self.enable_background_image = config.get('enable_background_image')

        # 背景图文件夹路径
        self.background_image_path = None
        if config.get('background_image_path') == '' or config.get('background_image_path') is None:
            # 获取插件路径
            current_file_path = os.path.abspath(__file__)
            plugin_path = os.path.dirname(os.path.dirname(current_file_path))
            # 默认背景图路径
            self.background_image_path = os.path.join(plugin_path, 'data', 'background_image')
        else:
            self.background_image_path = config.get('background_image_path')

    def get_server_list(self):
        """
        获取服务器列表
        """
        return self.server_list

    def get_bot_prefix(self):
        """
        获取机器人前缀
        """
        return self.bot_prefix

    def get_plugin_path(self):
        """获取当前插件的路径

        Returns:
            str: 当前插件的绝对路径
        """
        # 获取当前文件的绝对路径
        current_file_path = os.path.abspath(__file__)
        # 获取插件的根目录（向上两级目录：utils目录 -> 插件根目录）
        return os.path.dirname(os.path.dirname(current_file_path))


    def get_font(self):
        plugin_path = self.get_plugin_path()
        font_path = os.path.join(plugin_path, 'template', 'font', 'jiyinghuipianheyuan.ttf')
        b64 = base64.b64encode(pathlib.Path(font_path).read_bytes()).decode()
        font = f"data:font/ttf;base64,{b64}"
        return font