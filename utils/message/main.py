HELP_TITLE = "欢迎使用 Xc_Star 的 Minecraft 服务器管理插件"

HELP_ITEMS = [
    ("/list", "获取在线玩家列表"),
    ("/loc", "查看服务器坐标"),
    ("/zz &lt;X坐标&gt; &lt;Z坐标&gt;", "珍珠炮计算"),
    ("/task", "查看当前工程"),
    ("/mc wl add/remove &lt;游戏ID&gt;", "给玩家添加/移除白名单(管理员)"),
    ("/mc command &lt;服务器名&gt; &lt;命令&gt;", "向指定服务器发送 MC 命令(管理员)"),
    ("/mcdr &lt;服务器名&gt; &lt;命令&gt;", "向指定服务器发送 MCDR 命令(管理员)"),
    ("/say &lt;信息&gt;", "向服务器发送信息"),
    ("/mc reset wldb", "重载数据库中的白名单数据"),
    ("/wiki &lt;问题&gt;", "通过大模型查 wiki 获取答案"),
    ("/原图", "获取上一张 list 图片的背景图"),
    ("/抽卡", "随机获取一张 list 图片背景图"),
]

HELP_MESSAGE = "\n".join(
    [HELP_TITLE] + [f"{command} {description}" for command, description in HELP_ITEMS]
)

LOC_HELP_TITLE = "loc 命令格式"
LOC_HELP_ITEMS = [
    ("/loc add &lt;项目名字&gt; &lt;0-主世界 1-地狱 2-末地&gt; &lt;x y z&gt;", "添加服务器项目"),
    ("/loc remove &lt;项目名字&gt;", "删除服务器项目"),
    ("/loc list", "服务器项目坐标列表"),
    ("/loc &lt;项目名字&gt;", "查看项目地址"),
    ("/loc set &lt;项目名字&gt; &lt;0-主世界 1-地狱 2-末地&gt; &lt;x y z&gt;", "修改项目坐标"),
]
LOC_HELP_MESSAGE = "\n".join(
    [f"{LOC_HELP_TITLE}:"] + [f"{command} {description}" for command, description in LOC_HELP_ITEMS]
)

TASK_HELP_TITLE = "task 命令格式"
TASK_HELP_ITEMS = [
    ("/task add &lt;工程名字&gt; &lt;0-主世界 1-地狱 2-末地&gt; &lt;坐标&gt;", "添加服务器工程"),
    ("/task remove &lt;工程名字&gt;", "删除服务器工程"),
    ("/task list", "服务器工程坐标列表"),
    ("/task &lt;工程名字&gt;", "查看服务器工程详细信息"),
    ("/task set &lt;工程名字&gt; &lt;新工程名字&gt; &lt;0-主世界 1-地狱 2-末地&gt; &lt;坐标&gt;", "修改服务器工程"),
    ("/task claim &lt;工程名字&gt; &lt;材料编号&gt;", "领取一个材料"),
    ("/task commit &lt;工程名称&gt; &lt;材料序号&gt; &lt;n 个/组/盒&gt; &lt;材料所在位置/假人&gt;", "提交材料的备货情况"),
]
TASK_HELP_MESSAGE = "\n".join(
    [f"{TASK_HELP_TITLE}:"] + [f"{command} {description}" for command, description in TASK_HELP_ITEMS]
)


class MessageUtils:
    def get_help_message(self):
        return HELP_MESSAGE

    def get_help_data(self):
        return {
            "title": HELP_TITLE,
            "items": [
                {"command": command, "description": description}
                for command, description in HELP_ITEMS
            ],
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
            ],
        }

    def get_task_help_data(self):
        return {
            "title": TASK_HELP_TITLE,
            "items": [
                {"command": command, "description": description}
                for command, description in TASK_HELP_ITEMS
            ],
        }
