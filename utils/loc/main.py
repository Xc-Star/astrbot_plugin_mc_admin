import sqlite3
from typing import Optional, List
from astrbot.api import logger

from ..loc.vo import Loc


class LocUtils:
    """位置管理工具类，使用数据库存储位置数据"""
    
    def __init__(self, conn: sqlite3.Connection):
        """初始化位置管理工具
        
        Args:
            conn: 数据库连接对象
        """
        self.conn = conn

    def add_loc(self, loc: Loc) -> str:
        """添加新位置
        
        Args:
            loc: 位置对象
            
        Returns:
            操作结果消息
        """
        try:
            # 检查是否已存在同名位置
            if self.get_loc_by_name(loc.name) is not None:
                return f'已经有"{loc.name}"了喵'
            
            # 插入新位置
            sql = """
            INSERT INTO location (name, overworld, nether, end) 
            VALUES (?, ?, ?, ?)
            """
            self.conn.execute(sql, (loc.name, loc.overworld, loc.nether, loc.end))
            self.conn.commit()
            
            return f'已添加"{loc.name}"喵~'
        except sqlite3.IntegrityError:
            return f'已经有"{loc.name}"了喵'
        except Exception as e:
            logger.error(f"添加位置失败: {e}")
            self.conn.rollback()
            return f"呜哇！添加失败了喵！\n{e}"

    def remove_loc(self, name: str) -> str:
        """删除位置
        
        Args:
            name: 位置名称
            
        Returns:
            操作结果消息
        """
        try:
            # 检查位置是否存在
            if self.get_loc_by_name(name) is None:
                return f'没找到"{name}"喵~'
            
            # 删除位置
            sql = "DELETE FROM location WHERE name = ?"
            self.conn.execute(sql, (name,))
            self.conn.commit()
            
            return f'已将"{name}"移除喵！'
        except Exception as e:
            logger.error(f"删除位置失败: {e}")
            self.conn.rollback()
            return f"呜哇！删除失败了喵！\n{e}"
    
    def get_loc_by_name(self, name: str) -> Optional[Loc]:
        """根据名称获取位置
        
        Args:
            name: 位置名称
            
        Returns:
            位置对象，如果不存在则返回 None
        """
        try:
            sql = "SELECT id, name, overworld, nether, end FROM location WHERE name = ?"
            result = self.conn.execute(sql, (name,)).fetchone()
            
            if result:
                # result = (id, name, overworld, nether, end)
                return Loc(
                    name=result[1],
                    overworld=result[2],
                    nether=result[3],
                    end=result[4]
                )
            return None
        except Exception as e:
            logger.error(f"查询位置失败: {e}")
            return None

    def get_all_locations(self) -> List[Loc]:
        """获取所有位置列表
        
        Returns:
            位置对象列表
        """
        try:
            sql = "SELECT id, name, overworld, nether, end FROM location ORDER BY name"
            results = self.conn.execute(sql).fetchall()
            
            locations = []
            for row in results:
                locations.append(Loc(
                    name=row[1],
                    overworld=row[2],
                    nether=row[3],
                    end=row[4]
                ))
            return locations
        except Exception as e:
            logger.error(f"查询位置列表失败: {e}")
            return []

    def list_loc(self) -> str:
        """列出所有位置名称
        
        Returns:
            格式化的位置列表字符串
        """
        locations = self.get_all_locations()
        
        if not locations:
            return "暂无位置记录喵~"
        
        result = "服务器位置列表:\n"
        for loc in locations:
            result += f"- {loc.name}\n"
        return result.strip()

    def set_loc(self, loc: Loc) -> str:
        """更新位置信息
        
        Args:
            loc: 位置对象
            
        Returns:
            操作结果消息
        """
        try:
            # 检查位置是否存在
            if self.get_loc_by_name(loc.name) is None:
                return f'没找到"{loc.name}"喵~'
            
            # 更新位置信息
            sql = """
            UPDATE location 
            SET overworld = ?, nether = ?, end = ?
            WHERE name = ?
            """
            self.conn.execute(sql, (loc.overworld, loc.nether, loc.end, loc.name))
            self.conn.commit()
            
            return f'已更新"{loc.name}"喵~'
        except Exception as e:
            logger.error(f"更新位置失败: {e}")
            self.conn.rollback()
            return f"呜哇！更新失败了喵！\n{e}"
