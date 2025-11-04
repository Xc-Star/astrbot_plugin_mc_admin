import time
from pathlib import Path
import os
import json
import random
import math
import re
from urllib.parse import urljoin
from urllib.request import pathname2url
from jinja2 import FileSystemLoader, Environment
from ..config_utils import ConfigUtils
from .browser import BrowserManager
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
MATERIAL_ROW_HEIGHT = 72  # 单个材料行高度
MATERIAL_LOCATION_LINE_HEIGHT = 35  # 位置行高度
MATERIAL_MIN_HEIGHT = 960  # 最小截图高度

# 材料计算常量
ITEMS_PER_STACK = 64  # 每组物品数量
ITEMS_PER_BOX = 1728  # 每箱物品数量 (64 * 27)

# 支持的图片格式
SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

# 默认背景颜色
DEFAULT_BACKGROUND_COLOR = "#43454A"


# ==================== 工具函数 ====================

def path_to_file_url(file_path: str) -> str:
    """将文件路径转换为 file:// URL（跨平台支持）
        
    支持平台：
        - Windows: C:\\path\\to\\file -> file:///C:/path/to/file
        - Linux/Mac: /path/to/file -> file:///path/to/file
    """
    # 转换为绝对路径
    abs_path = os.path.abspath(file_path)
    # 使用 Path 对象确保跨平台兼容
    path_obj = Path(abs_path)
    # 转换为 POSIX 风格路径（使用正斜杠）
    posix_path = path_obj.as_posix()
    # 使用 pathname2url 进行 URL 编码（处理特殊字符和空格）
    url_path = pathname2url(posix_path)
    # 构建 file:// URL
    return f"file:///{url_path}"


# ==================== 类定义 ====================

class ImageUtils:
    """图片生成工具类，负责生成服务器列表和材料列表图片"""
    
    def __init__(self, config_utils: ConfigUtils):
        # 先保存配置工具供后续使用
        self.config_utils = config_utils
        self.output = os.path.join(self.config_utils.get_plugin_path(), "data")
        # 模板目录定位到插件根目录下的 template
        self.template_dir = os.path.join(self.config_utils.get_plugin_path(), 'template')
        self.enable_background_image = self.config_utils.enable_background_image
        self.background_image_dir = self.config_utils.background_image_path
        
        # 使用 BrowserManager 管理 browser 实例
        self.browser_manager = BrowserManager()
        
        # 记录最后使用的背景图片路径
        self._background_image = None
    
    # ==================== 公共方法 ====================
    
    def get_last_image(self):
        """获取最后一次使用的背景图片路径"""
        return self._background_image
    
    async def close_browser(self):
        """关闭 browser 实例"""
        await self.browser_manager.close()
    
    async def generate_list_image(self, servers_data=None):
        """生成在线玩家列表图片

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

        Returns:
            str: 生成的图片文件路径
        """
        # 准备数据
        task_data_with_materia = task_data.copy()
        task_data_with_materia['materia_list'] = self._process_materia_list(materia_list)

        # 计算截图高度
        height = self._calculate_materia_screenshot_height(task_data_with_materia['materia_list'])
        
        # 计算截图宽度（根据材料数量）
        material_count = len(task_data_with_materia['materia_list'])
        width = self._calculate_materia_screenshot_width(material_count)

        # 渲染 HTML 模板
        html_content = self.render_materia_template(task_data_with_materia)

        # 截图
        path = await self._take_screenshot(html_content, height, filename, width, full_page=True)

        return path
    
    # ==================== 模板渲染方法 ====================
    
    def render_list_template(self, servers_data=None):
        """渲染玩家列表 HTML 模板"""
        templates_dir = os.path.join(self.config_utils.get_plugin_path(), "template")
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template("list.html")
        
        # 准备背景样式
        background_image_style = self._get_background_image_style()
        # 获取字体
        font = self.config_utils.get_font()
        # 准备服务器数据（直接传递字典，不需要转 JSON）
        servers_data = servers_data or {}
        
        html_content = template.render({
            "servers_data": servers_data,
            "background_image_style": background_image_style,
            "font": font
        })
        
        return html_content
    
    def _get_background_image_style(self) -> str:
        """获取背景图片样式（跨平台支持）
        
        Returns:
            str: CSS 背景样式字符串
        """
        # 未启用背景图片时使用默认背景
        if not self.enable_background_image:
            return f"background: {DEFAULT_BACKGROUND_COLOR};"
        
        background_image_path = self.get_random_background_image()
        
        # 未找到图片时使用默认背景
        if not background_image_path:
            logger.debug("未找到可用的背景图片，使用默认背景")
            return f"background: {DEFAULT_BACKGROUND_COLOR};"
        
        try:
            # 使用跨平台路径转换函数
            file_url = path_to_file_url(background_image_path)
            return f"background-image: url('{file_url}');"
        except Exception as e:
            logger.error(f"创建背景样式失败: {e}")
            return f"background: {DEFAULT_BACKGROUND_COLOR};"
    
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
        """获取目录中的所有图片文件"""
        image_files = []
        for file in os.listdir(directory):
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in SUPPORTED_IMAGE_EXTENSIONS:
                image_files.append(file)
        return image_files
    
    # ==================== MateriaList 模板渲染方法 ====================
    
    def render_materia_template(self, task_data: dict) -> str:
        """渲染材料列表 HTML 模板"""
        templates_dir = os.path.join(self.config_utils.get_plugin_path(), "template")
        env = Environment(loader=FileSystemLoader(templates_dir))
        template = env.get_template("MateriaList.html")
        
        # 使用统一的背景样式获取方法
        background_image_style = self._get_background_image_style()
        font = self.config_utils.get_font()
        
        html_content = template.render({
            "data": task_data,
            "background_image_style": background_image_style,
            "font": font
        })
        
        return html_content
    
    def _get_material_image_url(self, material_name_id: str) -> str:
        """根据材料ID获取本地图片文件URL
        
        Args:
            material_name_id: 材料ID，格式如 minecraft:white_stained_glass
            
        Returns:
            str: 图片文件的 file:// URL，如果找不到则返回空字符串
        """
        if not material_name_id:
            return ''
        
        # 将 minecraft:white_stained_glass 转换为 minecraft_white_stained_glass
        file_name_base = material_name_id.lower().strip().replace(':', '_')
        
        # item_icon 目录路径
        item_icon_dir = os.path.join(self.output, "item_icon")
        
        # 支持的图片扩展名（按优先级排序）
        supported_extensions = ['.png', '.gif', '.jpg', '.jpeg']
        
        # 尝试查找文件
        for ext in supported_extensions:
            file_path = os.path.join(item_icon_dir, f"{file_name_base}{ext}")
            if os.path.exists(file_path):
                # 转换为 file:// URL
                try:
                    return path_to_file_url(file_path)
                except Exception as e:
                    logger.warning(f"转换图片路径失败 {file_path}: {e}")
                    return ''
        
        # 如果找不到文件，记录警告
        logger.debug(f"未找到材料图标文件: {material_name_id} (查找路径: {file_name_base})")
        return ''
    
    def _process_materia_list(self, materia_list: list) -> list:
        """处理材料列表数据"""
        def calculate_remaining_box(total, commit_count):
            """计算剩余盒数"""
            return max(0, math.floor((total - commit_count) / ITEMS_PER_BOX))
        
        def calculate_remaining_group(total, commit_count):
            """计算剩余组数（去除盒数后）"""
            remaining_items = max(0, (total - commit_count)) % ITEMS_PER_BOX
            return round(remaining_items / ITEMS_PER_STACK, 2)
        
        res = []
        for materia in materia_list:
            total = int(materia[3])
            commit_count = int(materia[5])
            material_name = materia[1]
            material_name_id = materia[2]
            
            res.append({
                "number": materia[6],  # 编号
                "name": material_name,  # 材料名字
                "image_url": self._get_material_image_url(material_name_id),  # 材料图片URL
                "total": total,  # 所需总数
                "remaining_box": calculate_remaining_box(total, commit_count),  # 还差 - 盒
                "remaining_group": calculate_remaining_group(total, commit_count),  # 还差 - 组
                "recipient": materia[4],  # 负责人
                "location": materia[8] if materia[8] is not None else '',  # 所在位置
            })
        return res

    # ==================== 高度计算方法 ====================
    
    def _calculate_list_screenshot_height(self, servers_data=None) -> int:
        """计算列表截图高度"""
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
        """统计所有服务器的玩家总数"""
        total = 0
        for _, data in servers_data.items():
            total += len(data.get('real_players', []))
            total += len(data.get('bot_players', []))
        return total
    
    def _calculate_materia_screenshot_height(self, materia_list: list) -> int:
        """计算材料列表截图高度
        
        注意：当材料很多且分成多列时，每列的材料数量会减少，
        所以高度应该基于单列最多的材料数量来计算
        """
        # 如果材料超过100个，按每列100个计算高度
        items_per_column = 100
        material_count = len(materia_list)
        
        # 计算每列最多的材料数量
        items_in_tallest_column = min(material_count, items_per_column)
        
        # 只统计单列材料的高度
        single_location_count = 0
        multi_location_height = 0
        
        # 只遍历第一列的材料来计算高度
        for materia in materia_list[:items_in_tallest_column]:
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
    
    def _calculate_materia_screenshot_width(self, material_count: int) -> int:
        """根据材料数量计算截图宽度
        
        Args:
            material_count: 材料总数
            
        Returns:
            int: 计算出的宽度
        """
        # 每100个材料一列，每列宽度约1200px
        items_per_column = 100
        column_width = 1200
        
        num_columns = (material_count + items_per_column - 1) // items_per_column
        
        # 单列时使用默认宽度，多列时增加宽度
        if num_columns <= 1:
            return SCREENSHOT_WIDTH
        else:
            # 多列时，宽度 = 列数 * 每列宽度 + 额外边距
            return num_columns * column_width + 100
    
    # ==================== 截图方法 ====================
    
    async def _take_screenshot(self, html_content: str, height: int, filename: str, width: int = SCREENSHOT_WIDTH, full_page: bool = False) -> str:
        """使用 playwright 截图（统一截图方法）"""
        path = os.path.join(self.output, filename)
        # 创建临时 HTML 文件以支持本地资源加载
        temp_html_path = os.path.join(self.output, f'temp_{filename}.html')

        await self.browser_manager.ensure_browser()
        # 设置 viewport
        viewport_height = 2000 if full_page else height
        page = await self.browser_manager.browser.new_page(viewport={
            'width': width,
            'height': viewport_height
        })
        
        # 根据图片大小动态计算超时时间（宽度越大，超时时间越长）
        # 基础超时30秒，每增加1200px宽度增加30秒
        timeout = 30000 + (width // 1200) * 30000
        # 设置页面超时
        page.set_default_timeout(timeout)
        
        try:
            # 将 HTML 写入临时文件
            with open(temp_html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 使用跨平台路径转换函数构建 file:// URL
            file_url = path_to_file_url(temp_html_path)
            
            await page.goto(file_url, wait_until='load', timeout=timeout)
            # 根据参数决定是否使用全页截图
            await page.screenshot(path=path, full_page=full_page, timeout=timeout)
        finally:
            await page.close()
            # 删除临时 HTML 文件
            try:
                if os.path.exists(temp_html_path):
                    os.remove(temp_html_path)
            except Exception as e:
                logger.warning(f'删除临时文件失败: {e}')
        
        return path
