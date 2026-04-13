# Minecraft 服务器管理插件

基于 AstrBot 的 Minecraft 管理插件，支持群组服管理、在线玩家列表制图、白名单管理、工程备货、坐标管理、珍珠炮落点计算等功能。

## 插件信息
- 插件名称：`astrbot_plugin_mc_admin`
- 作者：`Xc_Star`
- 当前版本：`1.0.3`
- 仓库地址：[https://github.com/Xc-Star/astrbot_plugin_mc_admin](https://github.com/Xc-Star/astrbot_plugin_mc_admin)

## 依赖与启动提醒
- 本插件会用 **Playwright Chromium** 生成图片（如 `/list`、`/task <工程名>`、`/zz`）。
- 插件初始化时会自动检查并安装 Chromium；首次安装可能较慢，取决于网络。
- 如果依赖安装完成后 AstrBot 插件页未立即显示插件，重启 AstrBot 一般可恢复。
- 若上传工程材料文件时提示 `packetBackend` 不可用，请检查 NapCatQQ 版本与 `packetBackend` 配置。

## 功能概览
- 在线玩家列表
- 白名单管理
- RCON 命令转发
- 工程任务与材料备货管理（支持 txt/csv/litematic）
- 珍珠炮落点计算
- 服务器坐标点管理
- 背景图抽卡与原图回看
- 按群启用（仅配置群可触发）

## 命令说明

### 通用命令
```text
/mc ｜ 查看帮助
/mc wl add/remove <ID> ｜ 给玩家添加/移除白名单(管理员)
/mc command <服务器名字> <command> ｜ 向指定服务器发送命令(管理员)
/mc reset wldb ｜ 重载数据库的白名单数据

/list ｜ 查看所有服务器在线玩家
/loc ｜ 查看 loc 命令帮助
/task ｜ 查看服务器施工工程
/zz <x> <z> ｜ 珍珠炮落点计算
/原图 ｜ 获取上一次list的背景图
/抽卡 ｜ 随机获取一张list图库的图
```

### 工程命令（`/task`）
```text
/task list ｜ 查看工程列表
/task add <工程名> <维度> <x y z> ｜ 添加一个工程，随后上传投影材料
/task remove <工程名> ｜ 删除一个工程
/task set <旧工程名> <新工程名> <维度> <x y z> ｜ 修改工程信息
/task <工程名> ｜ 查看工程信息
/task claim <工程名> <材料编号> ｜ 认领材料
/task commit <工程名> <材料编号> <n个/组/盒> <位置/假人> ｜ 备货完成后提交材料
```

`/task add` 后，机器人会提示你上传文件。支持上传 `txt`、`csv`、`litematic` 三种格式。

### 路径点命令（`/loc`）
```text
/loc add <项目名字> <0-主世界 1-地狱 2-末地> <x y z> ｜ 添加路径点
/loc remove <项目名字> ｜ 删除服务器项目
/loc list ｜ 服务器项目坐标列表
/loc <项目名字> ｜ 查看项目地址
/loc set <项目名字> <0-主世界 1-地狱 2-末地> <x y z> ｜ 修改项目坐标
```

## 配置说明

配置文件：`_conf_schema.json`

| 配置项 | 类型 | 默认值 | 说明                             |
|---|---|---|--------------------------------|
| `enabled_groups` | list | `[]` | 允许触发插件的群列表                     |
| `bot_prefix` | string | `bot_` | 假人前缀（白名单比对关闭时用于区分真玩家/假人）       |
| `servers` | list | `[]` | 服务器配置，格式：`名字:地址:端口:RCON密码`     |
| `enable_whitelist_compare` | bool | `false` | `/list` 是否使用白名单辅助识别真人玩家        |
| `enable_background_image` | bool | `true` | 是否启用列表背景图                      |
| `enable_background_image_random` | bool | `false` | 是否启用 `/抽卡`                     |
| `background_image_path` | string | `""` | 背景图目录，空时使用插件内置目录               |
| `enable_get_last_background_image` | bool | `false` | 是否启用 `/原图`                     |
| `enable_big_task_image` | bool | `false` | `/task <工程名>` 是否合并为单张大图        |
| `pearl_config` | string | `""` | 珍珠炮配置请使用`https://pearl.zxqblog.cn`生成或者解析后的配置文件           |
| `pearl_version` | string | `1212` | 珍珠炮计算版本（`Legacy`/`1205`/`1212`） |
| `real_red_color` | string | `红色` | 实际红色阵列名称                       |
| `real_blue_color` | string | `蓝色` | 实际蓝色阵列名称                       |
| `red_bit_count` | string | `""` | 红色阵列 TNT 位权配置（逗号分隔）            |
| `blue_bit_count` | string | `""` | 蓝色阵列 TNT 位权配置（逗号分隔）            |
| `direction_bit` | string | `""` | 方位编码映射（ESWN，逗号分隔）              |

## 注意事项
- `servers` 配置错误会导致相关命令无法连通 RCON。
- 详细的配置介绍：`BV`
