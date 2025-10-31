import json
import os
from typing import Dict, Optional
from astrbot.core import logger


class ItemMapping:
    """物品ID与名字映射工具类"""
    
    def __init__(self, mapping_file_path: str = None):
        """初始化物品映射"""
        if mapping_file_path is None:
            # 计算插件根目录下的 data/item_mapping.json
            # 当前文件位于: <plugin_root>/utils/fileparse/item_mapping.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            utils_dir = os.path.dirname(current_dir)
            plugin_root = os.path.dirname(utils_dir)
            self.mapping_file_path = os.path.join(plugin_root, 'data', 'item_mapping.json')
        else:
            self.mapping_file_path = mapping_file_path
            
        self._mapping_data = None
        self._reverse_mapping = None
        self._load_mapping()
    
    def _load_mapping(self):
        """加载映射数据"""
        try:
            if os.path.exists(self.mapping_file_path):
                with open(self.mapping_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._mapping_data = data.get('items', {})
                    # 创建反向映射（名字 -> ID）
                    self._reverse_mapping = {v: k for k, v in self._mapping_data.items()}
                logger.info(f"成功加载物品映射数据，共 {len(self._mapping_data)} 个物品")
            else:
                logger.warning(f"物品映射文件不存在: {self.mapping_file_path}")
                self._mapping_data = {}
                self._reverse_mapping = {}
        except Exception as e:
            logger.error(f"加载物品映射文件失败: {e}")
            self._mapping_data = {}
            self._reverse_mapping = {}
    
    def reload_mapping(self):
        """重新加载映射数据"""
        self._load_mapping()
    
    def get_item_name(self, item_id: str) -> Optional[str]:
        """根据物品ID获取物品名字"""
        return self._mapping_data.get(item_id)
    
    def get_item_id(self, item_name: str) -> Optional[str]:
        """根据物品名字获取物品ID"""
        return self._reverse_mapping.get(item_name)
    
    def get_all_items(self) -> Dict[str, str]:
        """获取所有物品映射"""
        return self._mapping_data.copy()
    
    def get_all_item_names(self) -> list:
        """获取所有物品名字列表"""
        return list(self._reverse_mapping.keys())
    
    def get_all_item_ids(self) -> list:
        """获取所有物品ID列表"""
        return list(self._mapping_data.keys())
    
    def search_items(self, keyword: str) -> Dict[str, str]:
        """搜索包含关键词的物品"""
        keyword = keyword.lower()
        results = {}
        
        # 搜索ID中包含关键词的物品
        for item_id, item_name in self._mapping_data.items():
            if keyword in item_id.lower() or keyword in item_name.lower():
                results[item_id] = item_name
                
        return results
    
    def add_item(self, item_id: str, item_name: str) -> bool:
        """添加新的物品映射"""
        try:
            self._mapping_data[item_id] = item_name
            self._reverse_mapping[item_name] = item_id
            self._save_mapping()
            logger.info(f"成功添加物品映射: {item_id} -> {item_name}")
            return True
        except Exception as e:
            logger.error(f"添加物品映射失败: {e}")
            return False
    
    def remove_item(self, item_id: str = None, item_name: str = None) -> bool:
        """删除物品映射"""
        try:
            if item_id and item_id in self._mapping_data:
                item_name = self._mapping_data[item_id]
                del self._mapping_data[item_id]
                del self._reverse_mapping[item_name]
                self._save_mapping()
                logger.info(f"成功删除物品映射: {item_id} -> {item_name}")
                return True
            elif item_name and item_name in self._reverse_mapping:
                item_id = self._reverse_mapping[item_name]
                del self._reverse_mapping[item_name]
                del self._mapping_data[item_id]
                self._save_mapping()
                logger.info(f"成功删除物品映射: {item_id} -> {item_name}")
                return True
            else:
                logger.warning(f"未找到要删除的物品映射")
                return False
        except Exception as e:
            logger.error(f"删除物品映射失败: {e}")
            return False
    
    def _save_mapping(self):
        """保存映射数据到文件"""
        try:
            data = {
                "version": "1.0",
                "description": "Minecraft物品ID与名字映射表",
                "items": self._mapping_data
            }
            
            # 确保目录存在
            os.makedirs(os.path.dirname(self.mapping_file_path), exist_ok=True)
            
            with open(self.mapping_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"保存物品映射文件失败: {e}")
    
    def get_mapping_info(self) -> Dict[str, any]:
        """获取映射信息统计"""
        return {
            "total_items": len(self._mapping_data),
            "file_path": self.mapping_file_path,
            "file_exists": os.path.exists(self.mapping_file_path),
            "last_modified": os.path.getmtime(self.mapping_file_path) if os.path.exists(self.mapping_file_path) else None
        }


# 全局实例，方便在插件中使用
item_mapping = ItemMapping()
