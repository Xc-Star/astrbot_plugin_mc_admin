import json
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

class TaslUtils:
    def __init__(self, config_utils: ConfigUtils, conn: sqlite3.Connection):
        self.image_utils = ImageUtils(config_utils)
        self.config_utils = config_utils
        self.conn = conn

    def remove_task(self, name):
        task = self.get_task_by_name(name)
        if task["code"] != 200:
            return f"工程{name}不存在"
        sql = "DELETE FROM task WHERE name = ?"
        self.conn.execute(sql, (name,))
        self.conn.commit()
        return "删除成功"

    def commit_task(self, parts, event: AstrMessageEvent):
        # name 2, materia 3,PersonInCharge 4, location 5
        task = self.get_task_by_name(parts[2])
        if task["code"] != 200:
            return f"工程{parts[2]}不存在"
        materia_list = json.loads(task['msg'][0][5])
        if len(materia_list) < int(parts[3]):
            return f"工程{parts[2]}中无序号为{parts[3]}材料"
        try:
            materia = materia_list[int(parts[3]) - 1]
            materia["progress"] = int(parts[4])
            materia["location"] = parts[5]
            materia["PersonInCharge"] = event.message_obj.sender.nickname
            materia_list[int(parts[3]) - 1] = materia
            sql = "UPDATE task SET MaterialList = ? WHERE name = ?"
            self.conn.execute(sql, (json.dumps(materia_list,ensure_ascii=False), parts[2],))
            self.conn.commit()
            return "提交材料成功"
        except Exception as e:
            return f"出现错误,请联系管理员进行处理"


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
            return {"code": 500, "msg": "工程不存在"}

    def render(self, task):
        _task = {
            "name": task[0][1],
            "location": task[0][2],
            "dimension": task[0][3],
            "CreateUser": task[0][4],
            "MaterialList": json.loads(task[0][5]),
        }
        templates = os.path.join(self.config_utils.get_plugin_path(), "template")
        output = os.path.join(self.config_utils.get_plugin_path(), "data")
        env = Environment(loader=FileSystemLoader(templates))
        template = env.get_template("MateriaList.html")
        background_image_style = self.image_utils.get_random_background_image()
        html_content = template.render({"data": _task, "background_image_style": background_image_style})
        hti = Html2Image(output_path=output, custom_flags=['--no-sandbox', '--disable-dev-shm-usage'])
        base_height = 134
        task_total = len(_task["MaterialList"])
        content_height = task_total * 47
        height = max(600, base_height + content_height)
        hti.screenshot(html_str=html_content, save_as="task.png", size=(650, height))
        path = os.path.join(output, "task.png")
        path = self.image_utils.image_fix(path)
        return path

    def set_task(self, parts, event):
        task = self.get_task_by_name(parts[2])
        if task["code"] != 200:
            return f"工程{parts[2]}不存在"
        if task["msg"][0][4] != event.message_obj.sender.nickname:
            return f"工程{parts[2]}不是你创建的，请联系{task[0][4]}进行修改"
        new_task = self.get_task_by_name(parts[3])
        if new_task["code"] == 200:
            return f"工程{parts[3]}存在，请重命名为其他名称"
        sql = "UPDATE task SET name = ?,location = ?,dimension = ? WHERE name = ?"
        # 5x 6y 7z
        dimension = f"{parts[5]} {parts[6]} {parts[7]}"
        self.conn.execute(sql, (parts[3], parts[4], dimension, parts[2]))
        return "修改成功"

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

    def task_material(self,url, file_name,session_id, task_temp):
        # url:文件链接 file_name:文件名称 session_id:会话ID task_temp:缓存的信息
        task_temp_info = task_temp[session_id]

        file_path = os.path.join(self.config_utils.get_plugin_path(), "data", file_name)
        if not self.download_file(url, file_path):
            return "文件下载失败"
        fp = FileParser(file_path).parse()
        os.remove(file_path)
        if fp["code"] != 200:
            return fp["msg"]
        try:
            task = {
                "name": task_temp_info["name"],
                "location": task_temp_info["location"],
                "dimension": task_temp_info["dimension"],
                "CreateUser": task_temp_info["CreateUser"],
                "MaterialList": fp["msg"],
            }
            sql = "insert into task(name,location,dimension,CreateUser,MaterialList) values (?, ?, ?, ?, ?);"
            MaterialList = json.dumps(task["MaterialList"], ensure_ascii=False)
            self.conn.execute(sql, (task["name"], task["location"], task["dimension"], task["CreateUser"], MaterialList))
            self.conn.commit()
            task_temp.pop(session_id)
            return "上传材料列表成功"
        except Exception as e:
            logger.error(e)
            return "出现错误，请联系管理员处理"