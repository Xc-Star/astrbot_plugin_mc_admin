import json
import math

from cachetools import TTLCache

from astrbot.api import logger
import os

import httpx
from astrbot.core.platform import AstrMessageEvent
from html2image import Html2Image
from jinja2 import FileSystemLoader, Environment
from .config_utils import ConfigUtils
import sqlite3
from .image_utils import ImageUtils
from .fileparser import FileParser

class TaskUtils:
    def __init__(self, config_utils: ConfigUtils, conn: sqlite3.Connection):
        self.image_utils = ImageUtils(config_utils)
        self.config_utils = config_utils
        self.conn = conn
        self.file_parser = FileParser()

    def remove_task(self, name, event: AstrMessageEvent):

        task = self.get_task_by_name(name)
        if task["code"] != 200:
            return f"没找到{name}喵~"

        if task["msg"][0][5] != event.get_sender_id() and not event.is_admin():
            return f"{name}才不是你的喵~"

        try:
            # 删除任务
            sql = "DELETE FROM task WHERE name = ?"
            self.conn.execute(sql, (name,))
            # 删除材料
            sql = "DELETE FROM material WHERE task_id = ?"
            self.conn.execute(sql, (task["msg"][0][0],))
            self.conn.commit()
            return f"把{name}删掉了喵~"
        except Exception as e:
            self.conn.rollback()
            return f"呜哇！报错了喵！\n{e}"

    def commit_task(self, parts, event: AstrMessageEvent):
        # name 2, materia 3,PersonInCharge 4, location 5
        task = self.get_task_by_name(parts[2])
        if task["code"] != 200:
            return f"没找到{parts[2]}喵~"
        materia_list = json.loads(task['msg'][0][5])
        if len(materia_list) < int(parts[3]):
            return f"没找到{parts[2]}的{parts[3]}号材料喵~"
        try:
            materia = materia_list[int(parts[3]) - 1]
            materia["progress"] = int(parts[4])
            materia["location"] = parts[5]
            materia["PersonInCharge"] = event.message_obj.sender.nickname
            materia_list[int(parts[3]) - 1] = materia
            sql = "UPDATE task SET MaterialList = ? WHERE name = ?"
            self.conn.execute(sql, (json.dumps(materia_list,ensure_ascii=False), parts[2],))
            self.conn.commit()
            return "收到啦！谢谢喵~"
        except Exception as e:
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

    def render(self, task, materia_list):
        _task = {
            "id": task[0][0],
            "name": task[0][1],
            "location": task[0][2],
            "dimension": task[0][3],
            "create_user": task[0][4],
            "materia_list": process_materia_list(materia_list),
        }
        templates = os.path.join(self.config_utils.get_plugin_path(), "template")
        output = os.path.join(self.config_utils.get_plugin_path(), "data")
        env = Environment(loader=FileSystemLoader(templates))
        template = env.get_template("MateriaList.html")
        if self.config_utils.enable_background_image:
            background_image_path = self.image_utils.get_random_background_image()
            if background_image_path:
                web_background_path = background_image_path.replace('\\', '/')
                background_image_style = f"background-image: url('{web_background_path}'); background-size: cover; background-position: center; background-repeat: no-repeat;"
            else:
                background_image_style = ""
        else:
            background_image_style = ""
        font = self.config_utils.get_font()
        html_content = template.render({"data": _task, "background_image_style": background_image_style, "font":font})
        materia_list = _task['materia_list']
        # bz为记录只有材料所在位置只有一个值或没有值的数量，lo_height为记录材料所在位置多于一个值所占的高度
        bz = lo_height = 0
        for materia in materia_list:
            location = materia["location"]
            if not location:
                bz+=1
                continue
            location_json = json.loads(location)
            if len(location_json) == 1:
                bz+=1
                continue
            lo_height = lo_height + (len(location_json)+1) * 21

        hti = Html2Image(output_path=output, custom_flags=['--no-sandbox', '--disable-dev-shm-usage'], browser='chrome')
        base_height = 134
        content_height = bz * 47
        # 加1是防止整入是丢掉小数点后面的数字导致截图不全
        height = max(600, int(base_height + content_height + lo_height)+1)
        hti.screenshot(html_str=html_content, save_as="task.png", size=(650, height))
        path = os.path.join(output, "task.png")
        path = self.image_utils.image_fix(path)
        return path

    def set_task(self, location, dimension, original_name, name, event):
        task = self.get_task_by_name(original_name)
        if task["code"] != 200:
            return f"没有{original_name}喵~"

        # 非创建者并且非管理员不可修改
        if task["msg"][0][4] != event.message_obj.sender.nickname and not event.is_admin():
            return f"{original_name}才不是你的喵~"

        # 校验新名字是否存在
        new_task = self.get_task_by_name(name)
        if new_task["code"] == 200:
            return f"已经有{name}了喵~"

        sql = "UPDATE task SET name = ?,location = ?,dimension = ? WHERE name = ?"
        self.conn.execute(sql, (name, location, dimension, original_name))
        return "修改成功喵~"

    def download_file(self, url, file_path):
        try:
            print(f"{url}\n{file_path}")
            # 发送GET请求
            response = httpx.get(url)
            # 检查请求是否成功
            response.raise_for_status()
            # 确保目标目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            # 将内容写入文件
            with open(file_path, 'wb') as f:
                f.write(response.content)
                return True
        except:
            return False

    def task_material(self, url, file_name, session_id: str, task_temp: TTLCache):
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
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"task_material 处理失败: {e}")
            return f"报错了喵~ \n {e}"
    
    def _create_task(self, task_temp_info: dict) -> int:
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
        # 下载文件
        file_path = os.path.join(self.config_utils.get_plugin_path(), "data", file_name)
        if not self.download_file(url, file_path):
            logger.error("文件下载失败")
            return None
        
        try:
            # 解析文件
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
        sql = "INSERT INTO material(name,name_id,total, recipient,commit_count,number,task_id) VALUES (?, ?, ?, ?, ?, ?, ?)"
        self.conn.executemany(sql, material_list)

    def update_material(self, task_name, material_number, event: AstrMessageEvent):
        # 获取任务id
        task_res = self.get_task_by_name(task_name)
        if (task_res['code'] != 200):
            return f"没找到{task_name}喵~"
        task = task_res["msg"]
        sql = "SELECT * FROM material WHERE task_id = ? and number = ?"
        sql_res = self.conn.execute(sql, (task[0][0], material_number)).fetchall()
        if sql_res:
            try:
                sql = "UPDATE material SET recipient = ? WHERE id = ?"
                self.conn.execute(sql, (event.get_sender_name(), sql_res[0][0]))
                self.conn.commit()
                return "领取成功喵~"
            except Exception as e:
                self.conn.rollback()
                return f"呜哇！出错了喵！\n{e}"
        else:
            return f"没找到{task_name}里面的{material_number}号喵~"

    def commit_material(self, task_name, material_number, location, count, group, box):
        # 获取任务id
        task_res = self.get_task_by_name(task_name)
        if (task_res['code'] != 200):
            return f"没找到{task_name}喵~"
        task = task_res["msg"]
        sql = "SELECT * FROM material WHERE task_id = ? and number = ?"
        sql_res = self.conn.execute(sql, (task[0][0], material_number)).fetchall()
        if sql_res:
            try:
                commited_count = int(sql_res[0][5])
                total = int(sql_res[0][3])
                if commited_count >= total:
                    return f"{sql_res[0][1]}已经完成了喵~"
                sql = "UPDATE material SET commit_count = ?, location = ? WHERE id = ?"
                commit_count = commited_count + count + (group * 64) + (box * 1728)
                sql_location = sql_res[0][8]
                if sql_location is None:
                    locations = [location]
                else:
                    locations = json.loads(sql_res[0][8])
                    locations.append(location)
                self.conn.execute(sql, (commit_count, json.dumps(locations), sql_res[0][0]))
                self.conn.commit()
                return "提交成功！谢谢喵~"
            except Exception as e:
                self.conn.rollback()
                return f"呜哇！出错了喵！\n{e}"
        else:
            return f"没找到{task_name}里面的{material_number}号喵~"


def process_materia_list(materia_list: list) -> list:
    def calculate_remaining_box(total, commit_count):
        return math.floor((total - commit_count) / 1728)
    def calculate_remaining_group(total, commit_count):
        return round(((total - commit_count) % 1728) / 64, 2)
    res = []
    for materia in materia_list:
        res.append({
            "number": materia[6], # 编号
            "name": materia[1], # 材料名字
            "total": materia[3], # 所需总数
            "remaining_box": calculate_remaining_box(int(materia[3]), int(materia[5])), # 还差 - 盒
            "remaining_group": calculate_remaining_group(int(materia[3]), int(materia[5])), # 还差 - 组
            "recipient": materia[4], # 负责人
            "location": materia[8] if materia[8] is not None else '', # 所在位置
        })
    return res
