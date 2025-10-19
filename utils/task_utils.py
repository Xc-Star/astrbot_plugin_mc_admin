import httpx
import os
from .config_utils import ConfigUtils
from .fileparser import FileParser


class TaskUtils:
    def __init__(self, config_utils: ConfigUtils):
        self.config_utils = config_utils
        pass

    # TODO add task
    def add_task(self, uid, name, location, dimension, CreateUser) -> dict:
        task_list = self.config_utils.get_task_list()
        for task in task_list:
            if task['name'] == name:
                return {"type": "text", "msg":"项目存在"}

        task = {
            "name": name,
            "location": location,
            "dimension": dimension,
            "CreateUser": CreateUser,
            "MaterialList": []
        }
        task_list.append(task)
        self.config_utils.set_task_list(task_list)

        # 记录未上传材料文件的uid和项目名称
        noupload = self.config_utils.get_task_no_upload_file_list()
        noupload[uid] = name
        self.config_utils.set_task_no_upload_file_list(noupload)

        return {"type": "text", "msg":f"项目{name}添加成功，请发送投影导出的材料列表，支持txt和csv"}

    def remove_task(self, name: str) -> dict:
        task_list = self.config_utils.get_task_list()
        for i, task in enumerate(task_list):
            if task['name'] == name:
                task_list.pop(i)
                self.config_utils.set_task_list(task_list)
                return {"type": "text", "msg": f'已将"{name}"移除'}
        return {"type": "text", "msg": f'未找到"{name}"'}

    # TODO get task by name
    def get_task_by_name(self, name: str) -> dict | None:
        task_list = self.config_utils.get_task_list()
        for task in task_list:
            if task['name'] == name:
                return task
        return None

    def list_task(self)  -> dict:
        task_list = self.config_utils.get_task_list()
        result = "服务器工程列表列表:\n"
        for task in task_list:
            result += f"- {task['name']}\n"
        return {"type": "text", "msg": result}

    # todo task commit 数据验证
    def commit_task(self, task_dic: dict) :
        task_list = self.config_utils.get_task_list()
        if not task_list:
            return f"项目：{task_dic['name']}不存在"
        for task in task_list:
            if task['name'] == task_dic['name']:
                for materia in task["MaterialList"]:
                    if materia['name'] == task_dic['materia']:
                        materia["progress"] = task_dic['status']
                        materia["PersonInCharge"] = task_dic['PersonInCharge']
                        materia["location"] = task_dic['location']
        self.config_utils.set_task_list(task_list)
        return {"type":"text","msg":f"项目：{task_dic['name']}材料列表的：{task_dic['materia']}备货状态提交成功"}

    def download_file(self, url, file_path):
        try:
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
        except httpx.RequestError as e:
            pass
        except IOError as e:
            pass
        except Exception as e:
            pass
        return False

    def download_task_material(self,url, file_name,name):
        file_path = os.path.join(os.getcwd(), "data", "plugins", "astrbot_plugin_mc_admin","data", f"{file_name}")
        download_file = self.download_file(url, file_path)
        if download_file:
            fileparser = FileParser(file_path).parse()
            task_list = self.config_utils.get_task_list()
            for task in task_list:
                if task['name'] == name:
                    task["MaterialList"] = fileparser['msg']
                    self.config_utils.set_task_list(task_list)
                    if fileparser["code"] == 200:
                        return "上传材料列表成功"
            else:
                return fileparser['msg']
