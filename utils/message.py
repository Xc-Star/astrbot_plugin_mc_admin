HELP_TITLE = "欢迎使用Xc_Star的Minecraft服务器管理插件"

HELP_ITEMS = [
    ("/list", "获取在线玩家列表"),
    ("/loc", "查看服务器坐标"),
    ("/zz <X坐标> <Z坐标>", "珍珠炮计算"),
    ("/task", "查看当前工程"),
    ("/mc wl add/remove <ID>", "给玩家添加/移除白名单(管理员)"),
    ("/mc command <服务器名字> <command>", "向指定服务器发送命令(管理员)"),
    ("/mc reset wldb", "重载数据库的白名单数据"),
    ("/原图", "可以获取上一次list的背景图"),
    ("/抽卡", "可以随机获取一张list图库的图"),
]

HELP_MESSAGE = "\n".join(
    [HELP_TITLE] + [f"{command} {description}" for command, description in HELP_ITEMS]
)

LOC_HELP_TITLE = "loc 命令格式"
LOC_HELP_ITEMS = [
    ("/loc add <项目名字> <0-主世界 1-地狱 2-末地> <x y z>", "添加服务器项目"),
    ("/loc remove <项目名字>", "删除服务器项目"),
    ("/loc list", "服务器项目坐标列表"),
    ("/loc <项目名字>", "查看项目地址"),
    ("/loc set <项目名字> <0-主世界 1-地狱 2-末地> <x y z>", "修改项目坐标"),
]
LOC_HELP_MESSAGE = "\n".join(
    [f"{LOC_HELP_TITLE}:"] + [f"{command} {description}" for command, description in LOC_HELP_ITEMS]
)

TASK_HELP_TITLE = "task 命令格式"
TASK_HELP_ITEMS = [
    ("/task add <工程名字> <0-主世界 1-地狱 2-末地> <坐标>", "添加服务器工程"),
    ("/task remove <工程名字>", "删除服务器工程"),
    ("/task list", "服务器工程坐标列表"),
    ("/task <工程名字>", "查看服务器工程详细信息"),
    ("/task set <工程名字> <新工程名称> <0-主世界 1-地狱 2-末地> <坐标>", "修改服务器工程"),
    ("/task claim <工程名字> <材料编号>", "领取一个材料"),
    ("/task commit <工程名称> <材料序号> <n 个/组/盒> <材料所在位置/假人>", "提交材料的备货情况"),
]
TASK_HELP_MESSAGE = "\n".join(
    [f"{TASK_HELP_TITLE}:"] + [f"{command} {description}" for command, description in TASK_HELP_ITEMS]
)

class MessageUtils:
    def __init__(self):
        pass

    def get_help_message(self):
        return HELP_MESSAGE

    def get_help_data(self):
        return {
            "title": HELP_TITLE,
            "items": [
                {"command": command, "description": description}
                for command, description in HELP_ITEMS
            ]
        }

    def get_loc_help_message(self):
        return LOC_HELP_MESSAGE

    def get_task_help_message(self):
        return TASK_HELP_MESSAGE

    def get_loc_help_data(self):
        return {
            "title": LOC_HELP_TITLE,
            "items": [
                {"command": command, "description": description}
                for command, description in LOC_HELP_ITEMS
            ]
        }

    def get_task_help_data(self):
        return {
            "title": TASK_HELP_TITLE,
            "items": [
                {"command": command, "description": description}
                for command, description in TASK_HELP_ITEMS
            ]
        }
