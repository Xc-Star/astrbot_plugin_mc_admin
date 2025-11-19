HELP_MESSAGE = """
欢迎使用Xc_Star的Minecraft服务器管理插件
/list 获取在线玩家列表
/原图 可以获取上一次list的背景图
/loc 查看服务器坐标
/zz <X坐标> <Z坐标> 珍珠炮计算 (开发中)
/task 查看当前工程
/mc wl add/remove <ID> 给玩家添加/移除白名单(管理员)
/mc command <服务器名字> <command> 向指定服务器发送命令(管理员)
/mc reset wldb 重载数据库的白名单数据
"""

LOC_HELP_MESSAGE = """
loc命令格式:
/loc add <项目名字> <0-主世界 1-地狱 2-末地> <x y z> 添加服务器项目
/loc remove <项目名字> 删除服务器项目
/loc list 服务器项目坐标列表
/loc <项目名字> 查看项目地址
/loc set <项目名字> <0-主世界 1-地狱 2-末地> <x y z> 修改项目坐标
"""

TASK_HELP_MESSAGE = """
task命令格式:
/task add <工程名字> <0-主世界 1-地狱 2-末地> <坐标> 添加服务器工程
/task remove <工程名字> 删除服务器工程
/task list 服务器工程坐标列表
/task <工程名字> 查看服务器工程详细信息
/task set <工程名字> <新工程名称> <0-主世界 1-地狱 2-末地> <坐标> 修改服务器工程
/task claim <工程名字> <材料编号> 领取一个材料
/task commit <工程名称> <材料序号> <n 个/组/盒> <材料所在位置/假人> 提交材料的备货情况
"""

class MessageUtils:
    def __init__(self):
        pass

    def get_help_message(self):
        return HELP_MESSAGE

    def get_loc_help_message(self):
        return LOC_HELP_MESSAGE

    def get_task_help_message(self):
        return TASK_HELP_MESSAGE
