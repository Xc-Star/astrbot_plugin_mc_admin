from html2image import Html2Image
from pathlib import Path
import os
import json
import random
from PIL import Image
import time
from astrbot.api import logger

class ImageUtils:
    def __init__(self):
        self.hti = Html2Image()
        current_file_path = os.path.abspath(__file__)
        plugin_path = os.path.dirname(os.path.dirname(current_file_path))
        self.template_dir = os.path.join(plugin_path, 'template')
        self.background_image_dir = os.path.join(plugin_path, 'data', 'background_image')

    def render_list_template(self, servers_data=None):
        """渲染HTML模板"""
        template_path = Path(os.path.join(self.template_dir, 'list.html'))
        if not template_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {template_path}")

        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        # 将玩家数据注入到HTML中
        if servers_data is not None:
            servers_json = json.dumps(servers_data, ensure_ascii=False)
            # 转义JSON字符串中的引号，避免与HTML属性冲突
            servers_json_escaped = servers_json.replace('"', '\\"')
            html_content = html_content.replace('{{ servers_data | safe }}', servers_json_escaped)
        else:
            html_content = html_content.replace('{{ servers_data | safe }}', '{}')

        # 从background_image_dir中随机选择一张图片作为背景
        background_image = self._get_random_background_image()
        if background_image:
            # 将Windows路径转换为网页路径格式（将反斜杠替换为正斜杠）
            web_background_path = background_image.replace('\\', '/')
            # 生成背景图片的CSS样式
            background_style = f"background-image: url('{web_background_path}'); background-size: cover; background-position: center; background-repeat: no-repeat;"
        else:
            # 如果没有背景图片，使用默认渐变背景
            background_style = "background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);"
        
        # 将背景样式注入到HTML中
        html_content = html_content.replace('{{ background_image_style }}', background_style)

        return html_content

    def _get_random_background_image(self):
        """
        从background_image_dir文件夹中随机选择一张图片
        """
        try:
            if not os.path.exists(self.background_image_dir):
                return ''
            
            # 获取文件夹中的所有图片文件
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
            image_files = []
            
            for file in os.listdir(self.background_image_dir):
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in image_extensions:
                    image_files.append(file)
            
            if not image_files:
                return ''
            
            # 随机选择一张图片
            random_image = random.choice(image_files)
            # 返回完整的图片路径
            return os.path.join(self.background_image_dir, random_image)
        except Exception as e:
            print(f"获取随机背景图片失败: {e}")
            return ''

    def generate_list_image(self, servers_data=None):
        """生成图片"""
        output_path = Path(os.path.join(self.template_dir, 'img.png'))
        output_path.parent.mkdir(exist_ok=True)

        # 根据实际内容动态调整图片高度
        # 新的高度计算方案，更加准确和保守
        height = 250  # 增加基础高度，确保标题和容器边距足够
        
        if servers_data:
            server_count = len(servers_data.items())
            
            for server_name, data in servers_data.items():
                # 每个服务器的基础高度：服务器名称 + 边距
                # 增加基础高度以适应不同长度的服务器名称
                height += 70
                
                # 真实玩家部分
                if data.get('real_players'):
                    height += 35  # 增加标题高度
                    player_count = len(data['real_players'])
                    
                    if player_count > 0:
                        # 计算玩家名称平均长度，用于估算每行可容纳的玩家数量
                        avg_name_length = sum(len(p) for p in data['real_players']) / player_count
                        
                        # 更精确的每行玩家数量估算
                        if avg_name_length <= 6:
                            cards_per_row = 6  # 非常短的名字
                        elif avg_name_length <= 9:
                            cards_per_row = 5  # 短名字
                        elif avg_name_length <= 13:
                            cards_per_row = 4  # 中等长度名字
                        elif avg_name_length <= 18:
                            cards_per_row = 3  # 较长名字
                        else:
                            cards_per_row = 2  # 很长的名字
                        
                        # 计算所需行数
                        rows = (player_count + cards_per_row - 1) // cards_per_row
                        # 增加每行高度，并添加额外的间距补偿
                        height += rows * 40  # 增加行高以避免拥挤
                    else:
                        height += 35  # 没有玩家时的提示高度
                else:
                    height += 55  # 没有玩家列表时的高度，增加一些余量
                
                # 机器人玩家部分
                if data.get('bot_players'):
                    height += 35  # 增加标题高度
                    player_count = len(data['bot_players'])
                    
                    if player_count > 0:
                        # 计算机器人名称平均长度
                        avg_name_length = sum(len(p) for p in data['bot_players']) / player_count
                        
                        # 更精确的每行玩家数量估算
                        if avg_name_length <= 6:
                            cards_per_row = 6
                        elif avg_name_length <= 9:
                            cards_per_row = 5
                        elif avg_name_length <= 13:
                            cards_per_row = 4
                        elif avg_name_length <= 18:
                            cards_per_row = 3
                        else:
                            cards_per_row = 2
                        
                        # 计算所需行数
                        rows = (player_count + cards_per_row - 1) // cards_per_row
                        # 增加每行高度，并添加额外的间距补偿
                        height += rows * 40
                    else:
                        height += 35  # 没有机器人时的提示高度
                else:
                    height += 55  # 没有机器人列表时的高度，增加一些余量
                
                # 服务器之间的间距，增加间距以更好地分隔服务器
                height += 25
        
        # 确保最小高度，增加最小高度值
        height = max(500, height)
        
        # 添加一些额外的边距防止裁切
        # 全新的边距计算方案，更准确地适应多服务器场景
        if servers_data:
            server_count = len(servers_data.items())
            # 基于服务器数量的非线性边距计算
            # 服务器越多，额外边距增长越快
            if server_count == 1:
                extra_margin = 80  # 单个服务器的额外边距
            elif server_count == 2:
                extra_margin = 100  # 两个服务器的额外边距
            elif server_count == 3:
                extra_margin = 140  # 三个服务器的额外边距
            elif server_count == 4:
                extra_margin = 180  # 四个服务器的额外边距
            else:
                # 五个及以上服务器，使用公式计算
                extra_margin = 180 + (server_count - 4) * 50
            
            height += extra_margin
        else:
            height += 80  # 无服务器数据时的额外边距

        url = self.hti.screenshot(
            html_str=self.render_list_template(servers_data),
            save_as='list.png',
            size=(482, height)
        )
        return self.image_fix(url[0])

    def image_fix(self, url: str) -> str:
        """
        修复html2image生成出来的图片底下有白边的bug
        读取到图片，裁切图片后返回新的url
        """
        image = Image.open(url)
        image = image.crop((0, 0, image.width, image.height - 100))
        image.save(url)
        return url
