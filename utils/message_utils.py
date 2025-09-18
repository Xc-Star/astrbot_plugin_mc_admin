HELP_MESSAGE = """
欢迎使用Xc_Star的Minecraft服务器管理插件
/list 获取在线玩家列表
/loc 查看服务器坐标
/zz <X坐标> <Z坐标> 珍珠炮计算 (开发中)
/task 查看当前工程 (开发中)
/mc wl add/remove <ID> 给玩家添加/移除白名单(管理员)
/mc command <服务器名字> <command> 向指定服务器发送命令(管理员)
"""

LOC_HELP_MESSAGE = """
/loc add <项目名字> <0-主世界 1-地狱 2-末地> <x y z> 添加服务器项目
/loc remove <项目名字> 删除服务器项目
/loc list 服务器项目坐标列表
/loc <项目名字> 查看项目地址
/loc set <项目名字> <0-主世界 1-地狱 2-末地> <x y z> 修改项目坐标
"""

TASK_HELP_MESSAGE = """
/task add 添加工程 (开发中)
    (发送命令后发材料列表的Excel文件，Excel文件可以通过v4.sctserver.top:81生成)
/task list 服务器工程列表 (开发中)
/task <工程名字> 查询工程的材料列表 (开发中)
/task commit <工程名字> <提交材料的编号> <完成进度> <材料所在位置/假人> (开发中)
"""

class MessageUtils:
    def __init__(self):
        pass

    def get_help_message(self):
        return HELP_MESSAGE

    def get_loc_help_message(self):
        return LOC_HELP_MESSAGE
