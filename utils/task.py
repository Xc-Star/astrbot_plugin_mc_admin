import json

from cachetools import TTLCache

from astrbot.api import logger
import os

import httpx
from astrbot.core.platform import AstrMessageEvent
from .config_utils import ConfigUtils
import sqlite3
from .media.image import ImageUtils
from .fileparse.main import FileParser


# 常量定义（兼容性保留）
class MaterialConstants:
    """材料计算相关常量
    
    注意：部分常量已迁移到 image_utils 中，这里保留以保持兼容性
    """
    # 物品数量常量
    ITEMS_PER_STACK = 64  # 每组物品数量
    STACKS_PER_BOX = 27  # 每组箱子（27组）
    ITEMS_PER_BOX = 1728  # 每箱物品数量 (64 * 27)


class TaskUtils:
    def __init__(self, config_utils: ConfigUtils, conn: sqlite3.Connection, image_utils: ImageUtils = None):
        self.image_utils = image_utils if image_utils is not None else ImageUtils(config_utils)
        self.config_utils = config_utils
        self.conn = conn
        self.file_parser = FileParser()
        self.output = os.path.join(self.config_utils.get_plugin_path(), "data")

    async def close_browser(self):
        """关闭 browser 实例"""
        await self.image_utils.close_browser()

    def _check_task_permission(self, task_data, event: AstrMessageEvent) -> str:
        """检查任务权限"""
        task_create_user_id = task_data[0][5]
        task_create_user_name = task_data[0][4]
        
        if task_create_user_id != event.get_sender_id() and not event.is_admin():
            return f"{task_create_user_name}才不是你的喵~"
        return None
    
    def _execute_sql_with_transaction(self, operations: list) -> tuple[bool, str]:
        """执行带事务的 SQL 操作
        
        Args:
            operations: [(sql, params), ...] 格式的操作列表
            
        Returns:
            (success, error_message)
        """
        try:
            for sql, params in operations:
                self.conn.execute(sql, params)
            self.conn.commit()
            return True, None
        except Exception as e:
            self.conn.rollback()
            logger.error(f"SQL 操作失败: {e}")
            return False, str(e)
    
    def remove_task(self, name, event: AstrMessageEvent):
        task = self.get_task_by_name(name)
        if task["code"] != 200:
            return f"没找到{name}喵~"

        permission_error = self._check_task_permission(task["msg"], event)
        if permission_error:
            return permission_error

        operations = [
            ("DELETE FROM task WHERE name = ?", (name,)),
            ("DELETE FROM material WHERE task_id = ?", (task["msg"][0][0],))
        ]
        
        success, error = self._execute_sql_with_transaction(operations)
        if success:
            return f"把{name}删掉了喵~"
        return f"呜哇！报错了喵！\n{error}"

    def commit_task(self, parts, event: AstrMessageEvent):
        """提交任务材料（旧版兼容方法）"""
        task_name = parts[2]
        material_index = int(parts[3]) - 1
        progress = int(parts[4])
        location = parts[5]
        
        task = self.get_task_by_name(task_name)
        if task["code"] != 200:
            return f"没找到{task_name}喵~"
            
        try:
            materia_list = json.loads(task['msg'][0][5])
            if len(materia_list) <= material_index:
                return f"没找到{task_name}的{parts[3]}号材料喵~"
                
            materia = materia_list[material_index]
            materia["progress"] = progress
            materia["location"] = location
            materia["PersonInCharge"] = event.message_obj.sender.nickname
            materia_list[material_index] = materia
            
            operations = [
                ("UPDATE task SET MaterialList = ? WHERE name = ?", 
                 (json.dumps(materia_list, ensure_ascii=False), task_name))
            ]
            
            success, error = self._execute_sql_with_transaction(operations)
            if success:
                return "收到啦！谢谢喵~"
            return f"呜哇！报错了喵！"
        except (json.JSONDecodeError, ValueError, IndexError) as e:
            logger.error(f"提交任务材料失败: {e}")
            return f"呜哇！报错了喵！"

    def get_task_list(self):
        sql = "select name from task"
        sql_res = self.conn.execute(sql).fetchall()
        res = "服务器工程列表\n"
        for row in sql_res:
            res += f"\t-{row[0]}\n"
        return res

    def export_task(self):
        pass

    def get_task_by_name(self, name) -> dict:
        sql = "select * from task where name = ?"
        sql_res = self.conn.execute(sql, (name,)).fetchall()
        if sql_res:
            return {"code": 200, "msg": sql_res}
        else:
            return {"code": 500, "msg": f"没找到{name}喵~"}

    def get_material_list_by_task_id(self, task_id) -> dict:
        sql = f"select * from material where task_id = {task_id}"
        sql_res = self.conn.execute(sql).fetchall()
        if sql_res:
            return {"code": 200, "msg": sql_res}
        else:
            return {"code": 500, "msg": f"没找到材料喵~"}

    async def render(self, task, materia_list):
        """渲染任务材料列表图片
        
        Args:
            task: 任务数据
            materia_list: 材料列表
            
        Returns:
            str: 生成的图片文件路径
        """
        # 准备任务数据
        task_data = {
            "id": task[0][0],
            "name": task[0][1],
            "location": task[0][2],
            "dimension": task[0][3],
            "create_user": task[0][4],
        }
        
        # 使用 image_utils 生成图片
        path = await self.image_utils.generate_materia_image(
            task_data=task_data,
            materia_list=materia_list,
            filename='task.png'
        )
        
        return path

    def set_task(self, location, dimension, original_name, name, event):
        """修改任务信息"""
        task = self.get_task_by_name(original_name)
        if task["code"] != 200:
            return f"没有{original_name}喵~"

        permission_error = self._check_task_permission(task["msg"], event)
        if permission_error:
            return permission_error

        # 校验新名字是否存在
        new_task = self.get_task_by_name(name)
        if new_task["code"] == 200:
            return f"已经有{name}了喵~"

        operations = [
            ("UPDATE task SET name = ?,location = ?,dimension = ? WHERE name = ?",
             (name, location, dimension, original_name))
        ]
        
        success, error = self._execute_sql_with_transaction(operations)
        if success:
            return "修改成功喵~"
        return f"呜哇！报错了喵！\n{error}"

    def download_file(self, url, file_path):
        """下载文件"""
        try:
            response = httpx.get(url, timeout=30)
            response.raise_for_status()
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'wb') as f:
                f.write(response.content)
            
            return True
        except (httpx.RequestError, httpx.HTTPStatusError, IOError) as e:
            logger.error(f"文件下载失败: {url}, 错误: {e}")
            return False

    def task_material(self, url, file_name, session_id: str, task_temp: TTLCache):
        """处理材料文件上传"""
        try:
            # 获取任务信息
            task_temp_info = task_temp[session_id]
            
            # 创建任务记录
            task_id = self._create_task(task_temp_info)
            if not task_id:
                return "创建任务记录失败喵~"
            
            # 处理材料文件
            material_list = self._process_material_file(url, file_name, task_id)
            if not material_list:
                self.conn.rollback()
                return "处理材料文件失败喵~"
            
            # 插入材料数据
            self._insert_material_data(material_list)
            
            # 提交事务并清理缓存
            self.conn.commit()
            task_temp.pop(session_id)
            return "上传材料列表成功喵~"
            
        except KeyError:
            return "会话已过期喵~"
        except Exception as e:
            self.conn.rollback()
            logger.error(f"task_material 处理失败: {e}")
            return f"报错了喵~ \n {e}"
    
    def _create_task(self, task_temp_info: dict) -> int:
        """创建任务记录"""
        task_data = (
            task_temp_info["name"],
            task_temp_info["location"], 
            task_temp_info["dimension"],
            task_temp_info["sender_name"],
            task_temp_info["sender_id"]
        )
        
        sql = "INSERT INTO task(name,location,dimension,create_user,create_user_id) VALUES (?, ?, ?, ?, ?)"
        cursor = self.conn.execute(sql, task_data)
        return cursor.lastrowid
    
    def _process_material_file(self, url: str, file_name: str, task_id: int) -> list:
        """处理材料文件"""
        file_path = os.path.join(self.config_utils.get_plugin_path(), "data", file_name)
        if not self.download_file(url, file_path):
            logger.error("文件下载失败")
            return None
        
        try:
            parse_result = self.file_parser.parse(file_path, int(task_id))
            if parse_result["code"] != 200:
                logger.error(parse_result['msg'])
                return None
            
            return parse_result["msg"]
        finally:
            # 确保临时文件被删除
            if os.path.exists(file_path):
                os.remove(file_path)
    
    def _insert_material_data(self, material_list: list):
        """插入材料数据"""
        sql = "INSERT INTO material(name,name_id,total, recipient,commit_count,number,task_id) VALUES (?, ?, ?, ?, ?, ?, ?)"
        self.conn.executemany(sql, material_list)

    def update_material(self, task_name, material_number, event: AstrMessageEvent):
        """领取材料"""
        task_res = self.get_task_by_name(task_name)
        if task_res['code'] != 200:
            return f"没找到{task_name}喵~"
            
        task = task_res["msg"]
        sql = "SELECT * FROM material WHERE task_id = ? and number = ?"
        sql_res = self.conn.execute(sql, (task[0][0], material_number)).fetchall()
        
        if not sql_res:
            return f"没找到{task_name}里面的{material_number}号喵~"
            
        operations = [
            ("UPDATE material SET recipient = ? WHERE id = ?",
             (event.get_sender_name(), sql_res[0][0]))
        ]
        
        success, error = self._execute_sql_with_transaction(operations)
        if success:
            return "领取成功喵~"
        return f"呜哇！出错了喵！\n{error}"

    def commit_material(self, task_name, material_number, location, count, group, box):
        """提交材料"""
        task_res = self.get_task_by_name(task_name)
        if task_res['code'] != 200:
            return f"没找到{task_name}喵~"
            
        task = task_res["msg"]
        sql = "SELECT * FROM material WHERE task_id = ? and number = ?"
        sql_res = self.conn.execute(sql, (task[0][0], material_number)).fetchall()
        
        if not sql_res:
            return f"没找到{task_name}里面的{material_number}号喵~"
            
        try:
            material = sql_res[0]
            commited_count = int(material[5])
            total = int(material[3])
            material_name = material[1]
            
            if commited_count >= total:
                return f"{material_name}已经完成了喵~"
                
            # 计算总提交数量
            commit_count = commited_count + count + (group * MaterialConstants.ITEMS_PER_STACK) + (box * MaterialConstants.ITEMS_PER_BOX)
            
            # 更新位置列表
            sql_location = material[8]
            if sql_location is None:
                locations = [location]
            else:
                locations = json.loads(sql_location)
                locations.append(location)
            
            operations = [
                ("UPDATE material SET commit_count = ?, location = ? WHERE id = ?",
                 (commit_count, json.dumps(locations, ensure_ascii=False), material[0]))
            ]
            
            success, error = self._execute_sql_with_transaction(operations)
            if success:
                return "提交成功！谢谢喵~"
            return f"呜哇！出错了喵！\n{error}"
            
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"提交材料失败: {e}")
            self.conn.rollback()
            return f"呜哇！出错了喵！\n{e}"
