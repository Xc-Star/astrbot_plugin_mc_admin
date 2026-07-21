import json
import os
import shutil
import sqlite3

from cachetools import TTLCache
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Side

from astrbot.api import logger
from astrbot.core.platform import AstrMessageEvent

from ..config_utils import ConfigUtils
from ..fileparse.main import FileParser
from ..http import HttpUtils
from ..media.image import ImageUtils


class MaterialConstants:
    ITEMS_PER_STACK = 64
    STACKS_PER_BOX = 27
    ITEMS_PER_BOX = 1728


class TaskUtils:
    def __init__(
        self,
        config_utils: ConfigUtils,
        conn: sqlite3.Connection,
        image_utils: ImageUtils = None,
    ):
        self.image_utils = image_utils if image_utils is not None else ImageUtils(config_utils)
        self.config_utils = config_utils
        self.conn = conn
        self.file_parser = FileParser()
        self.output = os.path.join(self.config_utils.get_plugin_path(), "data")

    async def close_browser(self):
        await self.image_utils.close_browser()

    def _check_task_permission(self, task_data, event: AstrMessageEvent) -> str:
        task_create_user_id = task_data[0][5]
        task_create_user_name = task_data[0][4]

        if task_create_user_id != event.get_sender_id() and not event.is_admin():
            return f"{task_create_user_name}才不是你的喵~"
        return None

    def _execute_sql_with_transaction(self, operations: list) -> tuple[bool, str]:
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
            logger.warning(f"{name}不存在")
            return f"没找到{name}喵~"

        permission_error = self._check_task_permission(task["msg"], event)
        if permission_error:
            logger.warning(f"{event.get_sender_name()}({event.get_sender_id()})没有权限删除{name}")
            return permission_error

        operations = [
            ("DELETE FROM task WHERE name = ?", (name,)),
            ("DELETE FROM material WHERE task_id = ?", (task["msg"][0][0],)),
        ]

        success, error = self._execute_sql_with_transaction(operations)
        if success:
            logger.info(f"{event.get_sender_name()}({event.get_sender_id()})成功删除{name}")
            return f"把{name}删掉了喵~"
        logger.error(f"{event.get_sender_name()}({event.get_sender_id()})删除{name}失败: {error}")
        return f"呜哇！报错了喵！\n{error}"

    def get_task_list(self):
        sql = "select name from task"
        sql_res = self.conn.execute(sql).fetchall()
        res = "服务器工程列表\n"
        for row in sql_res:
            res += f"\t-{row[0]}\n"
        return res

    def export_task(self, name: str) -> tuple[str, str, int]:
        """导出工程为 Excel 文件

        Returns:
            tuple: (file_path, file_name, code)
        """
        task_id_sql = "SELECT id FROM task WHERE name = ?"
        task_id_res = self.conn.execute(task_id_sql, (name,)).fetchone()
        if not task_id_res:
            return None, None, 404

        task_id = task_id_res[0]
        material_list_sql = "SELECT * FROM material WHERE task_id = ?"
        material_list_res = self.conn.execute(material_list_sql, (task_id,)).fetchall()
        if not material_list_res:
            return None, None, 404

        material_list = [
            {
                "name": row[1],
                "name_id": row[2],
                "total": row[3],
                "recipient": row[4],
                "commit_count": row[5],
                "number": row[6],
            }
            for row in material_list_res
        ]

        template_path = os.path.join(
            self.config_utils.get_plugin_path(), "template", "taskExportTemplate.xlsx"
        )
        output_dir = os.path.join(self.config_utils.get_plugin_path(), "data")
        os.makedirs(output_dir, exist_ok=True)
        file_name = f"{name}.xlsx"
        excel_file_path = os.path.join(output_dir, file_name)

        shutil.copy(template_path, excel_file_path)
        wb = load_workbook(excel_file_path)
        ws = wb.active

        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        for mat in material_list:
            total = mat["total"]
            required_chest_boxes = round(total / 1728 / 54, 2) if total > 0 else 0
            required_boxes = round(total / 1728, 2) if total > 0 else 0
            required_stacks = round(total / 64, 2) if total > 0 else 0
            is_complete = "是" if mat["commit_count"] >= total else "否"
            progress = round(mat["commit_count"] / total * 100, 1) if total > 0 else 0

            row_data = [
                mat["name"],
                is_complete,
                total,
                required_chest_boxes,
                required_boxes,
                required_stacks,
                total,
                mat["recipient"] or "",
                f"{progress}%",
                "",
            ]
            ws.append(row_data)

            for col_idx in range(1, 11):
                cell = ws.cell(row=ws.max_row, column=col_idx)
                cell.border = thin_border
                cell.alignment = Alignment(horizontal="center", vertical="center")

        wb.save(excel_file_path)

        return excel_file_path, file_name, 200

    def get_task_by_name(self, name) -> dict:
        sql = "select * from task where name = ?"
        sql_res = self.conn.execute(sql, (name,)).fetchall()
        if sql_res:
            return {"code": 200, "msg": sql_res}
        return {"code": 500, "msg": f"没找到{name}喵~"}

    def get_material_list_by_task_id(self, task_id) -> dict:
        sql = "SELECT * FROM material WHERE task_id = ?"
        sql_res = self.conn.execute(sql, (task_id,)).fetchall()
        if sql_res:
            return {"code": 200, "msg": sql_res}
        return {"code": 500, "msg": "没找到材料喵~"}

    async def render(self, task, materia_list, filename="task.png", use_big_image=True):
        task_data = {
            "id": task[0][0],
            "name": task[0][1],
            "location": task[0][2],
            "dimension": task[0][3],
            "create_user": task[0][4],
        }

        path = await self.image_utils.generate_materia_image(
            task_data=task_data,
            materia_list=materia_list,
            filename=filename,
            use_big_image=use_big_image,
        )

        return path

    def set_task(self, location, dimension, original_name, name, event):
        task = self.get_task_by_name(original_name)
        if task["code"] != 200:
            return f"没有{original_name}喵~"

        permission_error = self._check_task_permission(task["msg"], event)
        if permission_error:
            return permission_error

        new_task = self.get_task_by_name(name)
        if new_task["code"] == 200:
            return f"已经有{name}了喵~"

        operations = [
            (
                "UPDATE task SET name = ?,location = ?,dimension = ? WHERE name = ?",
                (name, location, dimension, original_name),
            )
        ]

        success, error = self._execute_sql_with_transaction(operations)
        if success:
            return "修改成功喵~"
        return f"呜哇！报错了喵！\n{error}"

    def download_file(self, url, file_path):
        try:
            HttpUtils.download_file(url, file_path, timeout=30)
            return True
        except Exception as e:
            logger.error(f"文件下载失败: {url}, 错误: {e}")
            return False

    def task_material(self, url, file_name, session_id: str, task_temp: TTLCache):
        try:
            task_temp_info = task_temp[session_id]

            task_id = self._create_task(task_temp_info)
            if not task_id:
                logger.error("创建任务记录失败")
                return "创建任务记录失败喵~"

            material_list = self._process_material_file(url, file_name, task_id)
            if not material_list:
                logger.error("处理材料文件失败 or 没有材料")
                self.conn.rollback()
                return "处理材料文件失败喵~"

            self._insert_material_data(material_list)

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
        task_data = (
            task_temp_info["name"],
            task_temp_info["location"],
            task_temp_info["dimension"],
            task_temp_info["sender_name"],
            task_temp_info["sender_id"],
        )

        sql = "INSERT INTO task(name,location,dimension,create_user,create_user_id) VALUES (?, ?, ?, ?, ?)"
        cursor = self.conn.execute(sql, task_data)
        return cursor.lastrowid

    def _process_material_file(self, url: str, file_name: str, task_id: int) -> list | None:
        file_path = os.path.join(self.config_utils.get_plugin_path(), "data", file_name)
        if not self.download_file(url, file_path):
            logger.error("文件下载失败")
            return None

        try:
            parse_result = self.file_parser.parse(file_path, int(task_id))
            if parse_result["code"] != 200:
                logger.error(f"文件解析失败: {parse_result['msg']}")
                return None

            return parse_result["msg"]
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    def _insert_material_data(self, material_list: list):
        sql = "INSERT INTO material(name,name_id,total, recipient,commit_count,number,task_id) VALUES (?, ?, ?, ?, ?, ?, ?)"
        self.conn.executemany(sql, material_list)

    def update_material(self, task_name, material_number, event: AstrMessageEvent):
        task_res = self.get_task_by_name(task_name)
        if task_res["code"] != 200:
            return f"没找到{task_name}喵~"

        task = task_res["msg"]
        sql = "SELECT * FROM material WHERE task_id = ? and number = ?"
        sql_res = self.conn.execute(sql, (task[0][0], material_number)).fetchall()

        if not sql_res:
            return f"没找到{task_name}里面的{material_number}号喵~"

        operations = [
            ("UPDATE material SET recipient = ? WHERE id = ?", (event.get_sender_name(), sql_res[0][0]))
        ]

        success, error = self._execute_sql_with_transaction(operations)
        if success:
            return "领取成功喵~"
        return f"呜哇！出错了喵！\n{error}"

    def commit_material(self, task_name, material_number, location, count, group, box):
        task_res = self.get_task_by_name(task_name)
        if task_res["code"] != 200:
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

            commit_count = (
                commited_count
                + count
                + (group * MaterialConstants.ITEMS_PER_STACK)
                + (box * MaterialConstants.ITEMS_PER_BOX)
            )

            sql_location = material[8]
            if sql_location is None:
                locations = [location]
            else:
                locations = json.loads(sql_location)
                locations.append(location)

            operations = [
                (
                    "UPDATE material SET commit_count = ?, location = ? WHERE id = ?",
                    (commit_count, json.dumps(locations, ensure_ascii=False), material[0]),
                )
            ]

            success, error = self._execute_sql_with_transaction(operations)
            if success:
                return "提交成功！谢谢喵~"
            return f"呜哇！出错了喵！\n{error}"

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"提交材料失败: {e}")
            self.conn.rollback()
            return f"呜哇！出错了喵！\n{e}"
