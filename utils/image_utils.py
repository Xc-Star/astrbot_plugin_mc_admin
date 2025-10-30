from pathlib import Path
import os
import json
import random
import base64
import math
from jinja2 import FileSystemLoader, Environment
from .config_utils import ConfigUtils
from .browser_manager import BrowserManager
from astrbot.api import logger


# ==================== 常量定义 ====================

# 截图相关常量
SCREENSHOT_WIDTH = 1200  # 截图宽度

# 高度计算常量（list.html）
LIST_BASE_HEIGHT = 450  # 基础高度
LIST_SERVER_HEIGHT = 360  # 每个服务器高度
LIST_PLAYER_INCREMENT = 72  # 每5个玩家增加的高度
LIST_MIN_HEIGHT = 900  # 最小高度

# 材料列表相关常量（MateriaList.html）
MATERIAL_BASE_HEIGHT = 197  # 基础高度
MATERIAL_ROW_HEIGHT = 71  # 单个材料行高度
MATERIAL_LOCATION_LINE_HEIGHT = 35  # 位置行高度
MATERIAL_MIN_HEIGHT = 960  # 最小截图高度

# 材料计算常量
ITEMS_PER_STACK = 64  # 每组物品数量
ITEMS_PER_BOX = 1728  # 每箱物品数量 (64 * 27)

# 支持的图片格式
SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

# 默认背景颜色
DEFAULT_BACKGROUND_COLOR = "#f0f0f0"


# ==================== 类定义 ====================

class ImageUtils:
    """图片生成工具类，负责生成服务器列表和材料列表图片"""
    
    def __init__(self, config_utils: ConfigUtils):
        self.output = os.path.join(config_utils.get_plugin_path(), "data")
        current_file_path = os.path.abspath(__file__)
        plugin_path = os.path.dirname(os.path.dirname(current_file_path))
        self.template_dir = os.path.join(plugin_path, 'template')
        self.enable_background_image = config_utils.enable_background_image
        self.background_image_dir = config_utils.background_image_path
        self.config_utils = config_utils
        
        # 使用 BrowserManager 管理 browser 实例
        self.browser_manager = BrowserManager()
        
        # 缓存模板内容和背景图片路径
        self._template_cache = None
        self._background_image = None
    
    # ==================== 公共方法 ====================
    
    def get_last_image(self):
        """获取最后一次使用的背景图片路径"""
        return self._background_image
    
    async def close_browser(self):
        """关闭 browser 实例"""
        await self.browser_manager.close()
    
    async def generate_list_image(self, servers_data=None):
        """生成服务器列表图片
        
        Args:
            servers_data: 服务器数据字典
            
        Returns:
            str: 生成的图片文件路径
        """
        output_path = Path(os.path.join(self.template_dir, 'img.png'))
        output_path.parent.mkdir(exist_ok=True)

        # 渲染 HTML 模板
        html_content = self.render_list_template(servers_data)
        
        # 计算截图高度
        height = self._calculate_list_screenshot_height(servers_data)
        
        # 截图
        path = await self._take_screenshot(html_content, height, 'list.png')
        
        return path
    
    async def generate_materia_image(self, task_data: dict, materia_list: list, filename: str = 'task.png') -> str:
        """生成材料列表图片
        
        Args:
            task_data: 任务数据字典
            materia_list: 处理后的材料列表
            filename: 保存的文件名
            
        Returns:
            str: 生成的图片文件路径
        """
        # 准备数据
        task_data_with_materia = task_data.copy()
        task_data_with_materia['materia_list'] = self._process_materia_list(materia_list)
        
        # 计算截图高度
        height = self._calculate_materia_screenshot_height(task_data_with_materia['materia_list'])
        
        # 渲染 HTML 模板
        html_content = self.render_materia_template(task_data_with_materia)
        
        # 截图
        path = await self._take_screenshot(html_content, height, filename)
        
        return path
    
    # ==================== 模板渲染方法 ====================
    
    def render_list_template(self, servers_data=None):
        """渲染HTML模板
        
        Args:
            servers_data: 服务器数据
            
        Returns:
            str: 渲染后的 HTML 内容
        """
        try:
            # 读取并缓存模板内容
            html_content = self._get_template_content()
            # 注入各种数据
            html_content = self._inject_servers_data(html_content, servers_data)
            html_content = self._inject_background_style(html_content)
            html_content = self._inject_font(html_content)
            return html_content
        except Exception as e:
            logger.error(f"渲染模板失败: {str(e)}")
            return f"<html><body><h1>模板渲染错误喵~</h1><p>{str(e)}</p></body></html>"
    
    def _get_template_content(self):
        """获取模板内容，带缓存机制"""
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
    
    def _inject_font(self, html_content: str) -> str:
        """注入字体到 HTML"""
        font = self.config_utils.get_font()
        return html_content.replace('{{ font }}', font)
    
    def _inject_servers_data(self, html_content: str, servers_data: dict) -> str:
        """将服务器数据注入到HTML中
        
        Args:
            html_content: HTML 内容
            servers_data: 服务器数据字典
            
        Returns:
            str: 注入后的 HTML 内容
        """
        # 参数验证和默认值处理
        if servers_data is not None and not isinstance(servers_data, dict):
            logger.warning("服务器数据格式不正确，应为字典类型")
            servers_data = {}
        
        servers_data = servers_data or {}
        
        try:
            servers_json = json.dumps(servers_data, ensure_ascii=False)
            # 转义JSON字符串中的引号，避免与HTML属性冲突
            servers_json_escaped = servers_json.replace('"', '\\"')
            return html_content.replace('{{ servers_data | safe }}', servers_json_escaped)
        except Exception as e:
            logger.error(f"注入服务器数据失败: {str(e)}")
            return html_content.replace('{{ servers_data | safe }}', '{}')
    
    def _inject_background_style(self, html_content: str) -> str:
        """将背景样式注入到HTML中（使用 Base64 编码）
        
        Args:
            html_content: HTML 内容
            
        Returns:
            str: 注入后的 HTML 内容
        """
        try:
            # 未启用背景图片或未找到图片时使用默认背景
            if not self.enable_background_image:
                return self._replace_background_style(html_content, self._get_default_background())
            
            background_image_path = self.get_random_background_image()
            
            if not background_image_path:
                logger.debug("未找到可用的背景图片，使用默认渐变背景")
                return self._replace_background_style(html_content, self._get_default_background())
            
            # 尝试生成 Base64 背景样式
            background_style = self._create_background_style_from_file(background_image_path)
            if background_style:
                return self._replace_background_style(html_content, background_style)
            
            return self._replace_background_style(html_content, self._get_default_background())
            
        except Exception as e:
            logger.error(f"注入背景样式失败: {str(e)}")
            return self._replace_background_style(html_content, self._get_default_background())
    
    def _get_default_background(self) -> str:
        """获取默认背景样式"""
        return f"background: {DEFAULT_BACKGROUND_COLOR};"
    
    def _replace_background_style(self, html_content: str, background_style: str) -> str:
        """替换 HTML 中的背景样式占位符"""
        return html_content.replace('{{ background_image_style }}', background_style)
    
    def _create_background_style_from_file(self, image_path: str) -> str:
        """从文件创建 Base64 背景样式
        
        Args:
            image_path: 图片文件路径
            
        Returns:
            str: CSS 背景样式字符串，失败返回空字符串
        """
        try:
            with open(image_path, 'rb') as img_file:
                img_data = img_file.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                
                # 确定 MIME 类型
                file_ext = os.path.splitext(image_path)[1].lower()
                mime_type = 'image/png' if file_ext == '.png' else 'image/jpeg'
                
                return (f"background-image: url('data:{mime_type};base64,{img_base64}'); "
                       "background-size: cover; background-position: center; background-repeat: no-repeat;")
        except Exception as e:
            logger.error(f"读取背景图片失败: {e}")
            return ""
    
    def get_random_background_image(self) -> str:
        """从背景图片目录中随机选择一张图片
        
        Returns:
            str: 图片文件路径，未找到返回空字符串
        """
        try:
            if not self.enable_background_image:
                logger.debug("已禁用背景图片，不获取随机背景图")
                return ''
            
            if not os.path.exists(self.background_image_dir):
                logger.warning(f"背景图片目录不存在: {self.background_image_dir}")
                return ''
            
            # 获取所有图片文件
            image_files = self._get_image_files(self.background_image_dir)
            
            if not image_files:
                logger.debug(f"背景图片目录中没有找到图片文件: {self.background_image_dir}")
                return ''
            
            # 随机选择并保存路径
            random_image = random.choice(image_files)
            logger.debug(f"选择的背景图片: {random_image}")
            
            image_path = os.path.join(self.background_image_dir, random_image)
            self._background_image = image_path
            return image_path
            
        except Exception as e:
            logger.error(f"获取随机背景图片失败: {str(e)}")
            return ''
    
    def _get_image_files(self, directory: str) -> list:
        """获取目录中的所有图片文件
        
        Args:
            directory: 目录路径
            
        Returns:
            list: 图片文件名列表
        """
        image_files = []
        for file in os.listdir(directory):
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in SUPPORTED_IMAGE_EXTENSIONS:
                image_files.append(file)
        return image_files
    
    # ==================== MateriaList 模板渲染方法 ====================
    
    def render_materia_template(self, task_data: dict) -> str:
        """渲染材料列表 HTML 模板
        
        Args:
            task_data: 任务数据字典
            
        Returns:
            str: 渲染后的 HTML 内容
        """
        templates_dir = os.path.join(self.config_utils.get_plugin_path(), "template")
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template("MateriaList.html")
        
        background_image_style = self._get_background_image_style_for_materia()
        font = self.config_utils.get_font()
        
        html_content = template.render({
            "data": task_data,
            "background_image_style": background_image_style,
            "font": font
        })
        
        return html_content
    
    def _get_background_image_style_for_materia(self) -> str:
        """获取材料列表背景图片样式（Base64编码）"""
        if not self.enable_background_image:
            return ""
            
        background_image_path = self.get_random_background_image()
        if not background_image_path:
            return ""
            
        try:
            with open(background_image_path, 'rb') as img_file:
                img_data = img_file.read()
                img_base64 = base64.b64encode(img_data).decode('utf-8')
                return f"background-image: url('data:image/jpeg;base64,{img_base64}');"
        except Exception as e:
            logger.error(f"读取背景图片失败: {e}")
            return ""
    
    def _process_materia_list(self, materia_list: list) -> list:
        """处理材料列表数据
        
        Args:
            materia_list: 原始材料列表
            
        Returns:
            list: 处理后的材料列表
        """
        def calculate_remaining_box(total, commit_count):
            """计算剩余箱数"""
            return math.floor((total - commit_count) / ITEMS_PER_BOX)
        
        def calculate_remaining_group(total, commit_count):
            """计算剩余组数（去除箱数后）"""
            remaining_items = (total - commit_count) % ITEMS_PER_BOX
            return round(remaining_items / ITEMS_PER_STACK, 2)
        
        res = []
        for materia in materia_list:
            total = int(materia[3])
            commit_count = int(materia[5])
            
            res.append({
                "number": materia[6],  # 编号
                "name": materia[1],  # 材料名字
                "total": total,  # 所需总数
                "remaining_box": calculate_remaining_box(total, commit_count),  # 还差 - 盒
                "remaining_group": calculate_remaining_group(total, commit_count),  # 还差 - 组
                "recipient": materia[4],  # 负责人
                "location": materia[8] if materia[8] is not None else '',  # 所在位置
            })
        return res

    # ==================== 高度计算方法 ====================
    
    def _calculate_list_screenshot_height(self, servers_data=None) -> int:
        """计算列表截图高度
        
        Args:
            servers_data: 服务器数据
            
        Returns:
            int: 截图高度（像素）
        """
        if not servers_data:
            return max(LIST_MIN_HEIGHT, LIST_BASE_HEIGHT)
        
        # 计算内容高度：每个服务器所需基础空间
        server_count = len(servers_data.items())
        content_height = server_count * LIST_SERVER_HEIGHT
        
        # 统计总玩家数
        total_players = self._count_total_players(servers_data)
        
        # 根据总玩家数增加额外高度
        content_height += (total_players // 5) * LIST_PLAYER_INCREMENT
        
        # 确保最小高度
        return max(LIST_MIN_HEIGHT, LIST_BASE_HEIGHT + content_height)
    
    def _count_total_players(self, servers_data: dict) -> int:
        """统计所有服务器的玩家总数
        
        Args:
            servers_data: 服务器数据
            
        Returns:
            int: 总玩家数
        """
        total = 0
        for _, data in servers_data.items():
            total += len(data.get('real_players', []))
            total += len(data.get('bot_players', []))
        return total
    
    def _calculate_materia_screenshot_height(self, materia_list: list) -> int:
        """计算材料列表截图高度
        
        Args:
            materia_list: 材料列表
            
        Returns:
            int: 截图高度（像素）
        """
        single_location_count = 0
        multi_location_height = 0
        
        for materia in materia_list:
            location = materia.get("location", "")
            if not location:
                single_location_count += 1
                continue
                
            try:
                location_json = json.loads(location)
                if len(location_json) == 1:
                    single_location_count += 1
                else:
                    # 计算多位置额外高度
                    multi_location_height += (len(location_json) + 1) * MATERIAL_LOCATION_LINE_HEIGHT
            except (json.JSONDecodeError, TypeError):
                single_location_count += 1
        
        base_height = MATERIAL_BASE_HEIGHT
        content_height = single_location_count * MATERIAL_ROW_HEIGHT
        
        # 加1是防止整数除法丢掉小数点导致截图不全
        total_height = base_height + content_height + multi_location_height + 1
        return max(MATERIAL_MIN_HEIGHT, int(total_height))
    
    # ==================== 截图方法 ====================
    
    async def _take_screenshot(self, html_content: str, height: int, filename: str) -> str:
        """使用 playwright 截图（统一截图方法）
        
        Args:
            html_content: HTML 内容
            height: 截图高度
            filename: 保存的文件名
            
        Returns:
            str: 截图文件路径
        """
        path = os.path.join(self.output, filename)
        
        await self.browser_manager.ensure_browser()
        page = await self.browser_manager.browser.new_page(viewport={
            'width': SCREENSHOT_WIDTH,
            'height': height
        })
        
        try:
            await page.set_content(html_content, wait_until='networkidle')
            await page.screenshot(path=path)
        finally:
            await page.close()
        
        return path
