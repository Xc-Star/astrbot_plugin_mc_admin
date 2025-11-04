import json
import os
from typing import Dict, Tuple, Optional, Set
from astrbot.api import logger
from chardet import detect

from .item_mapping import ItemMapping
from .litematic import parse_litematic


# ==================== 常量定义 ====================
# 堆叠规则配置
STACK_SIZE_16 = 16  # 潜影盒、旗帜、盔甲架、告示牌
STACK_SIZE_1 = 1    # 桶（特定）、床
STACK_SIZE_64 = 64  # 默认堆叠数

# 每个潜影盒可存放的组数
SHULKER_BOX_SLOTS = 27

# 文件解析配置
class ParseConfig:
    """文件解析配置类"""
    def __init__(self, interval: str, head: int, tail: int, name_index: int, strip_quotes: bool):
        self.interval = interval          # 分隔符
        self.head = head                  # 从头部第几行开始读取
        self.tail = tail                  # 读取到尾部第几行
        self.name_index = name_index      # 名称所在列的索引
        self.strip_quotes = strip_quotes  # 是否去除引号

# 文件类型解析配置映射
FILE_PARSE_CONFIGS = {
    '.txt': ParseConfig(interval='|', head=5, tail=-4, name_index=1, strip_quotes=False),
    '.csv': ParseConfig(interval=',', head=2, tail=-1, name_index=0, strip_quotes=True),
}


class FileParser:
    """文件解析器 - 支持多种格式的材料清单文件"""
    
    def __init__(self):
        """初始化文件解析器"""
        # 使用 ItemMapping 的默认路径解析（插件根/data/item_mapping.json）
        self.item_mapping = ItemMapping()
        
        # 加载材料过滤和映射配置
        self.merge_blacklist: Set[str] = set()
        self.material_id_mapping: Dict[str, str] = {}
        self._load_material_filter_config()

    def parse(self, file_path: str, task_id: int) -> Dict:
        """解析文件并返回材料列表"""
        # 获取文件扩展名
        file_ext = self._get_file_extension(file_path)
        
        # 根据文件类型选择解析方法
        if file_ext == '.litematic':
            return self._parse_litematic(file_path, task_id)
        elif file_ext in FILE_PARSE_CONFIGS:
            return self._parse_text_file(file_path, task_id, FILE_PARSE_CONFIGS[file_ext])
        else:
            return {"code": 500, "msg": f"不支持的文件格式: {file_ext}"}

    def _get_file_extension(self, file_path: str) -> str:
        """获取文件扩展名（小写）"""
        return file_path[file_path.rfind('.'):].lower() if '.' in file_path else ''

    def _load_material_filter_config(self):
        """加载材料过滤和映射配置文件"""
        try:
            # 获取配置文件路径（插件根目录/data/material_filter_config.json）
            current_dir = os.path.dirname(os.path.abspath(__file__))  # utils/fileparse
            plugin_root = os.path.dirname(os.path.dirname(current_dir))  # 插件根目录
            config_path = os.path.join(plugin_root, 'data', 'material_filter_config.json')
            
            # 加载配置文件
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                # 加载黑名单
                self.merge_blacklist = set(config.get('merge_blacklist', []))
                
                # 加载映射表
                self.material_id_mapping = config.get('material_id_mapping', {})
                
                logger.info(f"材料过滤配置加载成功: 黑名单 {len(self.merge_blacklist)} 项, 映射 {len(self.material_id_mapping)} 项")
            else:
                logger.warning(f"材料过滤配置文件不存在: {config_path}，使用空配置")
                
        except Exception as e:
            logger.error(f"加载材料过滤配置失败: {e}，使用空配置")

    def _parse_litematic(self, file_path: str, task_id: int) -> Dict:
        """解析 Litematic 投影文件"""
        try:
            # 解析 litematic 源文件
            result = parse_litematic(file_path)

            if result is None or "error" in result:
                logger.error(f"错误: {result.get('error', '未知错误') if result else '未知错误'}")
                return {"code": 500, "msg": f"解析投影源文件报错喵~: {f"错误: {result.get('error', '未知错误') if result else '未知错误'}"}"}
            
            # 合并多区域的材料
            merged_blocks = self._merge_regions(result)

            # 合并同种类材料
            merged_blocks = self._merge_same_material(merged_blocks)
            
            # 构建材料列表
            result = []
            for number, (block_id, count) in enumerate(merged_blocks.items(), start=1):
                item_name = self.item_mapping.get_item_name(block_id)
                # (name, item_id, total, location, commit_count, number, task_id)
                result.append((item_name, block_id, count, '', 0, number, task_id))
            
            return {"code": 200, "msg": result}
            
        except Exception as e:
            logger.error(f"解析 Litematic 文件失败: {e}")
            return {"code": 500, "msg": f"解析投影源文件报错喵~: {str(e)}"}

    def _parse_text_file(self, file_path: str, task_id: int, config: ParseConfig) -> Dict:
        """解析文本文件（TXT/CSV）"""
        try:
            # 获取文件编码格式，防止因为各种各样编码导致的报错
            with open(file_path, 'rb') as fb:
                raw = fb.read(1 << 20)
            enc = detect(raw).get('encoding') or 'utf-8'  # 保底 utf-8

            # 以获取到的编码格式打开文件
            with open(file_path, 'r', encoding=enc) as file:
                lines = file.read().split('\n')
            
            # 校验文件行数
            if len(lines) < config.head - (config.tail + 1):
                return {"code": 500, "msg": "文件内容不足，无法解析喵~"}
            
            # 提取有效行
            valid_lines = lines[config.head:config.tail] if config.tail != -1 else lines[config.head:]
            
            # 解析每一行
            result = []
            for number, line in enumerate(valid_lines, start=1):
                material = self._parse_line(line, config, number, task_id)
                if material:
                    result.append(material)
            
            if not result:
                return {"code": 500, "msg": "未找到有效的材料数据喵~"}
            
            return {"code": 200, "msg": result}
            
        except FileNotFoundError:
            return {"code": 500, "msg": "文件不存在喵~"}
        except UnicodeDecodeError:
            return {"code": 500, "msg": "文件编码错误，请使用 UTF-8 编码喵~"}
        except Exception as e:
            logger.error(f"解析文本文件失败: {e}")
            return {"code": 500, "msg": "解析不了喵~"}

    def _parse_line(self, line: str, config: ParseConfig, number: int, task_id: int) -> Optional[Tuple]:
        """解析单行材料数据"""
        try:
            parts = line.split(config.interval)
            
            # 提取材料名称
            name = parts[config.name_index].strip()
            if config.strip_quotes and len(name) >= 2:
                name = name[1:-1]  # 去除首尾引号
            
            # 提取数量
            total = int(parts[config.name_index + 1].strip())
            
            # 获取物品ID
            item_id = self.item_mapping.get_item_id(name)
            
            # (name, item_id, total, location, commit_count, number, task_id)
            return (name, item_id, total, '', 0, number, task_id)
            
        except (IndexError, ValueError) as e:
            logger.warning(f"解析行数据失败: {line}, 错误: {e}")
            return None

    def _merge_regions(self, parse_result: Dict) -> Dict[str, int]:
        """合并所有区域的同种材料"""
        merged_blocks = {}
        
        if "regions" in parse_result:
            for region_name, region_data in parse_result["regions"].items():
                if "most_common_blocks" in region_data:
                    for block_id, count in region_data["most_common_blocks"].items():
                        # 累加相同 block_id 的数量
                        merged_blocks[block_id] = merged_blocks.get(block_id, 0) + count
        
        return merged_blocks

    def _merge_same_material(self, merged_blocks: Dict[str, int]) -> Dict[str, int]:
        """合并同种类材料"""
        result = {}
        
        for block_id, count in merged_blocks.items():
            # 1. 提取基础方块ID和状态标记
            base_block_id = block_id.split('[')[0] if '[' in block_id else block_id
            
            # 检查是否是 type=double 状态，如果是则数量x2
            actual_count = count
            if '[' in block_id and 'type=double' in block_id:
                actual_count = count * 2
            
            # 2. 检查是否在黑名单中
            if base_block_id in self.merge_blacklist:
                # 在黑名单中，直接跳过，移除该物品
                continue
            
            # 3. 检查是否在映射表中，应用ID映射
            final_block_id = self.material_id_mapping.get(base_block_id, base_block_id)
            
            # 4. 累加数量到最终的方块ID
            result[final_block_id] = result.get(final_block_id, 0) + actual_count
        
        # 5. 按数量降序排序
        sorted_result = dict(sorted(result.items(), key=lambda item: item[1], reverse=True))
        
        return sorted_result

    # ==================== 工具方法 ====================
    def get_stack_size(self, item_name: str) -> int:
        """获取物品的堆叠数量"""
        # 特殊堆叠规则
        if any(item_name.endswith(suffix) for suffix in ['潜影盒', '旗帜', '盔甲架', '告示牌']):
            return STACK_SIZE_16
        elif item_name.endswith('床'):
            return STACK_SIZE_1
        elif item_name.endswith('桶') and len(item_name) >= 2:
            return STACK_SIZE_1
        else:
            return STACK_SIZE_64

    def get_gb_total(self, name: str, total: int) -> Tuple[float, float]:
        """计算材料的组数和盒数"""
        stack_size = self.get_stack_size(name)
        
        # 计算组数（向上取整保留2位小数）
        group_total = round(total / stack_size, 2)
        
        # 计算盒数（向上取整保留2位小数）
        box_total = round(group_total / SHULKER_BOX_SLOTS, 2)
        
        return group_total, box_total
