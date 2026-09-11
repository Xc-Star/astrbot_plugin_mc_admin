import json
import os
import shutil
from typing import Any, TypedDict

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Side
from wireup import injectable

from astrbot.api import logger

from ..config_utils import ConfigUtils
from ..config_utils.container import TaskTempCache, get_service
from ..db.main import DbUtils
from ..file_parse.main import FileParser
from ..http import HttpUtils
from ..media.image import ImageUtils

# Minecraft 坐标边界
MC_COORD_X_MIN, MC_COORD_X_MAX = -30000000, 30000000
MC_COORD_Y_MIN, MC_COORD_Y_MAX = -64, 368
MC_COORD_Z_MIN, MC_COORD_Z_MAX = -30000000, 30000000

# 材料单位映射
MATERIAL_UNIT_MAP = {
    "个": (1, 0, 0),
    "组": (0, 1, 0),
    "盒": (0, 0, 1),
}

class MaterialConstants:
    ITEMS_PER_STACK = 64
    STACKS_PER_BOX = 27
    ITEMS_PER_BOX = 1728

class DBResponse(TypedDict):
    success: bool
    data: Any


@injectable
class TaskUtils:
    def __init__(
        self,
        config_utils: ConfigUtils,
        image_utils: ImageUtils,
    ):
        db_util = get_service(DbUtils)
        self.conn = db_util.get_conn()
        self.image_utils = (
            image_utils if image_utils is not None else ImageUtils(config_utils)
        )
        self.config_utils = config_utils
        self.file_parser = FileParser()
        self.output = os.path.join(self.config_utils.get_plugin_path(), "data")
        self.task_temp = get_service(TaskTempCache)

    async def close_browser(self):
        await self.image_utils.close_browser()

    def handle_task_add(
        self,
        name: str,
        dimension: str,
        location: str,
        create_group_id: str,
        create_user_id: str,
        create_user_name: str,
        is_admin: bool,
    ) -> str:
        """处理工程添加"""

        # 校验坐标
        is_valid, error_msg = self.validate_coordinates(location)
        if not is_valid:
            return error_msg

        # 校验是否重名
        task_res = self.get_task_by_name(name)
        if task_res.get("success"):
            return f"已经有{name}了喵~"

        # 校验是否已经在创建中
        for key in self.task_temp:
            if self.task_temp[key]["name"] == name:
                if not is_admin:
                    return f"{self.task_temp[key]['sender_name']}({self.task_temp[key]['sender_id']})已经申请创建{name}了喵~"
                # 管理员强制创建
                self.task_temp.pop(key)
                break

        # 创建临时信息
        self.task_temp[f"{create_group_id}_{create_user_id}"] = {
            "name": name,
            "sender_name": create_user_name,
            "sender_id": create_user_id,
            "dimension": dimension,
            "location": location,
        }

        return "好的喵~快发我litematic、txt、csv吧"

    def validate_coordinates(self, coordinates: str) -> tuple[bool, str]:
        """验证 Minecraft 坐标的有效性"""
        try:
            coord_parts = coordinates.split()
            if len(coord_parts) != 3:
                return False, "是<x y z>喵~"

            x, y, z = int(coord_parts[0]), int(coord_parts[1]), int(coord_parts[2])

            # 验证坐标范围
            if not (
                MC_COORD_X_MIN <= x <= MC_COORD_X_MAX
                and MC_COORD_Z_MIN <= z <= MC_COORD_Z_MAX
                and MC_COORD_Y_MIN <= y <= MC_COORD_Y_MAX
            ):
                return False, "坐标不可以太大喵~"

            return True, ""
        except ValueError:
            return False, "坐标是整数喵~"

    def _check_task_permission(self, task_data, sender_id: str, is_admin: bool) -> str | None:
        task_create_user_id = task_data[0][5]
        task_name = task_data[0][2]

        if task_create_user_id != sender_id and not is_admin:
            return f"{task_name}才不是你的喵~"
        return None

    def _execute_sql_with_transaction(self, operations: list) -> tuple[bool, str | None]:
        try:
            for sql, params in operations:
                self.conn.execute(sql, params)
            self.conn.commit()
            return True, None
        except Exception as e:
            self.conn.rollback()
            logger.error(f"SQL 操作失败: {e}")
            return False, str(e)

    def handle_task_remove(self, name, sender_id: str, is_admin: bool) -> str:
        """处理工程删除"""

        # 校验是否存在
        task_res = self.get_task_by_name(name)
        success = task_res.get("success")
        task = task_res.get("data")
        if not success:
            return f"没找到{name}喵~"

        # 校验权限
        permission_error = self._check_task_permission(task, sender_id, is_admin)
        if permission_error:
            return permission_error

        # 数据库删除
        operations = [
            ("DELETE FROM task WHERE name = ?", (name,)),
            ("DELETE FROM material WHERE task_id = ?", (task[0][0],)),
        ]
        success, error = self._execute_sql_with_transaction(operations)

        if success:
            return f"把{name}删掉了喵~"
        return f"呜哇！报错了喵！\n{error}"

    def get_task_list_str(self):
        """获取工程名字列表字符串（一行一个）"""

        sql = "select name from task"
        sql_res = self.conn.execute(sql).fetchall()
        res = "服务器工程列表\n"
        for row in sql_res:
            res += f"\t-{row[0]}\n"
        return res

    def handle_task_set(self, original_name: str, name: str, dimension: str, location: str, sender_id: str, is_admin: bool) -> str:
        """处理任务修改"""

        # 校验坐标
        is_valid, error_msg = self.validate_coordinates(location)
        if not is_valid:
            logger.warning(f"坐标校验失败: {error_msg}")
            return error_msg

        task_res = self.get_task_by_name(original_name)
        success = task_res.get("success")
        task = task_res.get("data")

        # 校验是否存在
        if not success:
            return f"没有{original_name}喵~"

        # 校验权限
        permission_error = self._check_task_permission(task, sender_id, is_admin)
        if permission_error:
            return permission_error

        # 校验新名字是否存在
        new_task_res = self.get_task_by_name(name)
        if new_task_res.get("success"):
            return f"已经有{name}了喵~"

        # 修改数据库
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

    def handle_task_claim(self, task_name: str, material_number: str, recipient: str) -> str:
        """处理任务认领"""

        # 校验是否存在
        task_res = self.get_task_by_name(task_name)
        success = task_res.get("success")
        task = task_res.get("data")
        if not success:
            return f"没找到{task_name}喵~"

        # 查询材料是否存在
        sql = "SELECT * FROM material WHERE task_id = ? and number = ?"
        sql_res = self.conn.execute(sql, (task[0][0], material_number)).fetchall()
        if not sql_res:
            return f"没找到{task_name}里面的{material_number}号喵~"

        # 执行认领
        operations = [
            (
                "UPDATE material SET recipient = ? WHERE id = ?",
                (recipient, sql_res[0][0]),
            )
        ]

        success, error = self._execute_sql_with_transaction(operations)
        if success:
            return "领取成功喵~"
        return f"呜哇！出错了喵！\n{error}"

    def handle_task_commit(self, msg: str) -> str:
        """处理材料提交"""

        # 解析命令参数
        parts = msg.split(" ", 5)
        if len(parts) < 6:
            logger.warning(f"task commit命令格式错误: {msg}")
            return "是/task commit <工程名称> <材料序号> <n 个/组/盒> <材料所在位置/假人>喵~"

        # 解析参数
        task_name, material_number, quantity_str, location = (
            parts[2],
            parts[3],
            parts[4],
            parts[5],
        )

        # 解析数量与单位
        individual, stack, shulker = 0, 0, 0
        for unit, (i, s, sh) in MATERIAL_UNIT_MAP.items():
            if quantity_str.endswith(unit):
                try:
                    count = int(quantity_str[: -len(unit)])
                    individual, stack, shulker = count * i, count * s, count * sh
                    break
                except ValueError:
                    logger.warning(f"材料数量格式错误: {quantity_str}")
                    return "是/task commit <工程名称> <材料序号> <n 个/组/盒> <材料所在位置/假人>喵~"
            else:
                # 没有单位，尝试纯数字，默认按"个"处理
                if quantity_str.isdigit():
                    individual = int(quantity_str)
                else:
                    logger.warning(f"材料数量格式错误: {quantity_str}")
                    return "是/task commit <工程名称> <材料序号> <n 个/组/盒> <材料所在位置/假人>喵~"

        # 数据库提交材料
        return self.commit_material(
            task_name, material_number, location, individual, stack, shulker
        )

    def commit_material(self, task_name, material_number, location, count, group, box):
        """提交材料到数据库"""

        # 校验是否存在
        task_res = self.get_task_by_name(task_name)
        success = task_res.get("success")
        task = task_res.get("data")
        if not success:
            return f"没找到{task_name}喵~"

        # 校验材料是否存在
        sql = "SELECT * FROM material WHERE task_id = ? and number = ?"
        sql_res = self.conn.execute(sql, (task[0][0], material_number)).fetchall()
        if not sql_res:
            return f"没找到{task_name}里面的{material_number}号喵~"

        try:
            # 解析数据
            material = sql_res[0]
            commited_count = int(material[5])
            total = int(material[3])
            material_name = material[1]

            # 数据校验
            if commited_count >= total:
                return f"{material_name}已经完成了喵~"

            # 计算提交后的数量
            commit_count = (
                commited_count
                + count
                + (group * MaterialConstants.ITEMS_PER_STACK)
                + (box * MaterialConstants.ITEMS_PER_BOX)
            )

            # 处理材料所在位置
            sql_location = material[8]
            if sql_location is None:
                locations = [location]
            else:
                locations = json.loads(sql_location)
                locations.append(location)

            # 提交到数据库
            operations = [
                (
                    "UPDATE material SET commit_count = ?, location = ? WHERE id = ?",
                    (
                        commit_count,
                        json.dumps(locations, ensure_ascii=False),
                        material[0],
                    ),
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

    def export_task(self, name: str) -> tuple[str, str, bool]:
        """导出工程为 Excel 文件

        Returns:
            tuple: (file_path, file_name, success)
        """

        # 校验工程是否存在
        task_id_sql = "SELECT id FROM task WHERE name = ?"
        task_id_res = self.conn.execute(task_id_sql, (name,)).fetchone()
        if not task_id_res:
            return "", "", False

        # 校验材料列表是否存在
        task_id = task_id_res[0]
        material_list_sql = "SELECT * FROM material WHERE task_id = ?"
        material_list_res = self.conn.execute(material_list_sql, (task_id,)).fetchall()
        if not material_list_res:
            return "", "", False

        # 解析材料列表
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

        # 复制一份模板
        template_path = os.path.join(
            self.config_utils.get_plugin_path(), "template", "taskExportTemplate.xlsx"
        )
        output_dir = os.path.join(self.config_utils.get_plugin_path(), "data")
        os.makedirs(output_dir, exist_ok=True)
        file_name = f"{name}.xlsx"
        excel_file_path = os.path.join(output_dir, file_name)
        shutil.copy(template_path, excel_file_path)

        # 加载 Excel 模板
        wb = load_workbook(excel_file_path)
        ws = wb.active
        thin_border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # 写入材料
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

        return excel_file_path, file_name, True

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

    def download_file(self, url, file_path):
        try:
            HttpUtils.download_file(url, file_path, timeout=30)
            return True
        except Exception as e:
            logger.error(f"文件下载失败: {url}, 错误: {e}")
            return False

    def handle_task_material(self, url, file_name, session_id: str) -> str:
        try:

            # 工程添加到数据库
            task_temp_info = self.task_temp[session_id]
            task_id = self._create_task(task_temp_info)
            if task_id == 0:
                logger.error("创建任务记录失败")
                return "创建任务记录失败喵~"

            # 解析工程材料列表
            success, material_list = self._process_material_file(url, file_name, task_id)
            if not success:
                self.conn.rollback()
                return "处理材料文件失败喵~"

            # 将解析得到的材料列表插入数据库
            self._insert_material_data(material_list)
            self.conn.commit()
            self.task_temp.pop(session_id)
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
        if cursor.lastrowid:
            return cursor.lastrowid
        return 0

    def _process_material_file(
        self, url: str, file_name: str, task_id: int
    ) -> tuple[bool, Any]:

        # 获取文件的本地存储路径
        file_path = os.path.join(self.config_utils.get_plugin_path(), "data", file_name)
        if not self.download_file(url, file_path):
            return False, "文件下载失败"

        try:
            # 解析文件
            success, parse_result = self.file_parser.parse(file_path, int(task_id))
            if not success:
                return False, "文件解析失败"

            return True, parse_result
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    def _insert_material_data(self, material_list: list):
        sql = "INSERT INTO material(name,name_id,total, recipient,commit_count,number,task_id) VALUES (?, ?, ?, ?, ?, ?, ?)"
        self.conn.executemany(sql, material_list)

    def get_task_by_name(self, name) -> DBResponse:
        sql = "select * from task where name = ?"
        sql_res = self.conn.execute(sql, (name,)).fetchall()
        if sql_res:
            return {"success": True, "data": sql_res}
        return {"success": False, "data": f"没找到{name}喵~"}
