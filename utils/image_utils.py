from html2image import Html2Image
from pathlib import Path
import os
import json
from PIL import Image

class ImageUtils:
    def __init__(self):
        self.hti = Html2Image()
        current_file_path = os.path.abspath(__file__)
        plugin_path = os.path.dirname(os.path.dirname(current_file_path))
        self.template_dir = os.path.join(plugin_path, 'template')

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

        return html_content

    def generate_list_image(self, servers_data=None):
        """生成图片"""
        output_path = Path(os.path.join(self.template_dir, 'img.png'))
        output_path.parent.mkdir(exist_ok=True)

        # 根据实际内容动态调整图片高度
        height = 200  # 基础高度（标题 + 容器边距）
        
        if servers_data:
            for server_name, data in servers_data.items():
                # 每个服务器的基础高度：服务器名称 + 边距
                height += 60
                
                # 真实玩家部分
                if data.get('real_players'):
                    height += 30  # 标题高度
                    player_count = len(data['real_players'])
                    # 重新设计的高度计算算法
                    # 考虑flex布局特性，不假设每行固定数量
                    # 估算平均每个玩家名长度(字符数)
                    if player_count > 0:
                        avg_name_length = sum(len(p) for p in data['real_players']) / player_count
                        # 基于名称长度估算每行能容纳的玩家数
                        # 名字越长，每行容纳的越少
                        if avg_name_length <= 8:
                            cards_per_row = 5  # 短名字可以多放一些
                        elif avg_name_length <= 12:
                            cards_per_row = 4  # 中等长度名字
                        elif avg_name_length <= 16:
                            cards_per_row = 3  # 较长名字
                        else:
                            cards_per_row = 2  # 很长的名字
                    else:
                        cards_per_row = 4
                        
                    # 计算所需行数
                    rows = (player_count + cards_per_row - 1) // cards_per_row
                    height += rows * 35  # 增加每行高度估计
                else:
                    height += 50  # 没有玩家时的提示高度
                
                # 机器人玩家部分
                if data.get('bot_players'):
                    height += 30  # 标题高度
                    player_count = len(data['bot_players'])
                    # 重新设计的高度计算算法
                    if player_count > 0:
                        avg_name_length = sum(len(p) for p in data['bot_players']) / player_count
                        # 基于名称长度估算每行能容纳的玩家数
                        if avg_name_length <= 8:
                            cards_per_row = 5
                        elif avg_name_length <= 12:
                            cards_per_row = 4
                        elif avg_name_length <= 16:
                            cards_per_row = 3
                        else:
                            cards_per_row = 2
                    else:
                        cards_per_row = 4
                        
                    # 计算所需行数
                    rows = (player_count + cards_per_row - 1) // cards_per_row
                    height += rows * 35  # 增加每行高度估计
                else:
                    height += 50  # 没有玩家时的提示高度
                
                # 服务器之间的间距
                height += 20
        
        # 确保最小高度
        height = max(400, height)
        # 添加一些额外的边距防止裁切
        height += 50

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
