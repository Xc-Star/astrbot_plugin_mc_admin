import os
import json

class ConfigUtils:

    def get_server_list(self):
        """
        获取服务器列表
        """
        path = os.path.join(self.get_plugin_path(), 'config', 'config.json')
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)['servers']
        
    def get_bot_prefix(self):
        """
        获取机器人前缀
        """
        path = os.path.join(self.get_plugin_path(), 'config', 'config.json')
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)['bot_prefix']

    def get_plugin_path(self):
        """获取当前插件的路径

        Returns:
            str: 当前插件的绝对路径
        """
        # 获取当前文件的绝对路径
        current_file_path = os.path.abspath(__file__)
        # 获取插件的根目录（向上两级目录：utils目录 -> 插件根目录）
        plugin_path = os.path.dirname(os.path.dirname(current_file_path))
        return plugin_path