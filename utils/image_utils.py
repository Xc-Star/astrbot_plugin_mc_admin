from html2image import Html2Image
from pathlib import Path
import os
import json
import random
from PIL import Image
from .config_utils import ConfigUtils
import asyncio
from astrbot.api import logger

class ImageUtils:
    def __init__(self, config_utils: ConfigUtils):
        output = os.path.join(config_utils.get_plugin_path(), "data")
        self.hti = Html2Image(output_path=output, custom_flags=['--no-sandbox', '--disable-dev-shm-usage'])
        current_file_path = os.path.abspath(__file__)
        plugin_path = os.path.dirname(os.path.dirname(current_file_path))
        self.template_dir = os.path.join(plugin_path, 'template')
        self.enable_background_image = config_utils.enable_background_image
        self.background_image_dir = config_utils.background_image_path
        self.config_utile = config_utils

    # 缓存模板内容
    _template_cache = None
    # list图片路径
    _background_image = None
    def get_last_image(self):
        return self._background_image
    
    def render_list_template(self, servers_data=None):
        """渲染HTML模板"""
        try:
            # 1. 读取并缓存模板内容
            html_content = self._get_template_content()
            # 2. 注入服务器数据
            html_content = self._inject_servers_data(html_content, servers_data)
            # 3. 注入背景样式
            html_content = self._inject_background_style(html_content)
            # TODO 4.注入字体
            # html_content = self._inject_font(html_content)
            return html_content
        except Exception as e:
            logger.error(f"渲染模板失败: {str(e)}")
            # 发生错误时返回一个简单的错误页面
            return f"<html><body><h1>模板渲染错误喵~</h1><p>{str(e)}</p></body></html>"

    # TODO 4.注入字体
    def _inject_font(self, html_content):
        font = self.config_utile
        html_content.replace('{{ font }}', font)
        return html_content

    def _get_template_content(self):
        """获取模板内容，带缓存机制"""
        # 检查缓存是否存在
        if self._template_cache is not None:
            return self._template_cache
        
        template_path = Path(os.path.join(self.template_dir, 'list.html'))
        if not template_path.exists():
            raise FileNotFoundError(f"模板文件不存在: {template_path}")
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                self._template_cache = f.read()
            return self._template_cache
        except Exception as e:
            raise IOError(f"读取模板文件失败: {str(e)}")
    
    def _inject_servers_data(self, html_content, servers_data):
        """将服务器数据注入到HTML中"""
        # 参数验证
        if servers_data is not None and not isinstance(servers_data, dict):
            logger.warning("服务器数据格式不正确，应为字典类型")
            servers_data = {}
        
        # 默认使用空字典
        servers_data = servers_data or {}
        
        try:
            # 转换为JSON并处理特殊字符
            servers_json = json.dumps(servers_data, ensure_ascii=False)
            # 转义JSON字符串中的引号，避免与HTML属性冲突
            servers_json_escaped = servers_json.replace('"', '\\"')
            return html_content.replace('{{ servers_data | safe }}', servers_json_escaped)
        except Exception as e:
            logger.error(f"注入服务器数据失败: {str(e)}")
            # 失败时使用空数据
            return html_content.replace('{{ servers_data | safe }}', '{}')
    
    def _inject_background_style(self, html_content):
        """将背景样式注入到HTML中"""
        try:
            # 检查是否启用背景图片
            if self.enable_background_image:
                # 从background_image_dir中随机选择一张图片作为背景
                background_image = self.get_random_background_image()
                
                if background_image:
                    # 将Windows路径转换为网页路径格式
                    web_background_path = background_image.replace('\\', '/')
                    # 生成背景图片的CSS样式
                    background_style = f"background-image: url('{web_background_path}'); background-size: cover; background-position: center; background-repeat: no-repeat;"
                else:
                    # 如果没有找到背景图片，使用默认渐变背景
                    logger.debug("未找到可用的背景图片，使用默认渐变背景")
                    background_style = "background: #f0f0f0;"  # 使用灰色背景
            else:
                # 已禁用背景图片，使用灰色背景
                background_style = "background: #f0f0f0;"  # 使用灰色背景
            
            return html_content.replace('{{ background_image_style }}', background_style)
        except Exception as e:
            logger.error(f"注入背景样式失败: {str(e)}")
            # 失败时使用灰色背景
            return html_content.replace('{{ background_image_style }}', "background: #f0f0f0;")

    def get_random_background_image(self):
        """
        从background_image_dir文件夹中随机选择一张图片
        """
        try:
            # 检查是否启用背景图片
            if not self.enable_background_image:
                logger.debug("已禁用背景图片，不获取随机背景图")
                return ''
            
            # 检查背景图片目录是否存在
            if not os.path.exists(self.background_image_dir):
                logger.warning(f"背景图片目录不存在: {self.background_image_dir}")
                return ''
            
            # 获取文件夹中的所有图片文件
            image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']
            image_files = []
            
            for file in os.listdir(self.background_image_dir):
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in image_extensions:
                    image_files.append(file)
            
            if not image_files:
                logger.debug(f"背景图片目录中没有找到图片文件: {self.background_image_dir}")
                return ''
            
            # 随机选择一张图片
            random_image = random.choice(image_files)
            logger.debug(f"选择的背景图片: {random_image}")
            # 返回完整的图片路径
            self._background_image = os.path.join(self.background_image_dir, random_image).__str__()
            return os.path.join(self.background_image_dir, random_image)
        except Exception as e:
            logger.error(f"获取随机背景图片失败: {str(e)}")
            return ''

    async def generate_list_image(self, servers_data=None):
        """生成图片"""
        output_path = Path(os.path.join(self.template_dir, 'img.png'))
        output_path.parent.mkdir(exist_ok=True)

        # 基于服务器数量和玩家数量的线性估计
        # 基础高度：标题栏和基本布局
        base_height = 250
        
        # 计算内容高度：每个服务器约需要200px的基础空间
        # 每10个玩家额外增加50px的高度
        content_height = 0
        if servers_data:
            server_count = len(servers_data.items())
            content_height = server_count * 200  # 每个服务器基础高度
            
            total_players = 0
            for _, data in servers_data.items():
                total_players += len(data.get('real_players', []))
                total_players += len(data.get('bot_players', []))
            
            # 根据总玩家数增加额外高度
            content_height += (total_players // 5) * 40
        
        # 确保最小高度为500px
        height = max(500, base_height + content_height)
        
        # 在异步环境中执行阻塞操作，避免阻塞事件循环
        # 使用asyncio.to_thread将CPU密集型操作放在线程池中执行
        url = await asyncio.to_thread(
            self._take_screenshot,
            self.render_list_template(servers_data),
            'list.png',
            (482, height)
        )
        # 将图片处理也放在线程池中执行
        return await asyncio.to_thread(self.image_fix, url[0])
        
    def _take_screenshot(self, html_str, save_as, size):
        """在线程池中执行的截图操作"""
        return self.hti.screenshot(
            html_str=html_str,
            save_as=save_as,
            size=size
        )

    def image_fix(self, url: str) -> str:
        """
        修复html2image生成出来的图片底下有白边的bug
        读取到图片，裁切图片后返回新的url
        """
        image = Image.open(url)
        image = image.crop((0, 0, image.width, image.height - 100))
        image.save(url)
        return url
