import os
from pathlib import Path
from urllib.request import pathname2url

from astrbot.core import AstrBotConfig


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
        """获取服务器列表"""
        return self.server_list

    def get_bot_prefix(self):
        """获取假人前缀"""
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
        """获取字体URL（跨平台支持 Windows/Linux/Mac）
        
        Returns:
            str: 字体文件的 file:// URL
            
        支持平台：
            - Windows: 转换为 file:///C:/path/to/font.ttf
            - Linux/Mac: 转换为 file:///path/to/font.ttf
        """
        plugin_path = self.get_plugin_path()
        font_path = os.path.join(plugin_path, 'template', 'font', 'jiyinghuipianheyuan.ttf')
        
        # 转换为绝对路径
        abs_path = os.path.abspath(font_path)
        # 使用 Path 对象确保跨平台兼容
        path_obj = Path(abs_path)
        # 转换为 POSIX 风格路径（使用正斜杠）
        posix_path = path_obj.as_posix()
        # 使用 pathname2url 进行 URL 编码（处理特殊字符和空格）
        url_path = pathname2url(posix_path)
        # 构建 file:// URL
        file_url = f"file:///{url_path}"
        
        return file_url