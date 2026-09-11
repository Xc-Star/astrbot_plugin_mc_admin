import re

import httpx
from rcon.exceptions import EmptyResponse

from astrbot.api import logger

from ..config_utils import ConfigUtils
from ..rcon import rcon_send

MC_FORMAT_CODE_RE = re.compile(r"§.")


def find_server_by_name(servers: list[dict], name: str) -> dict | None:
    """根据服务器名字查找服务器。"""
    for server in servers:
        if server.get("name") == name:
            return server
    return None


async def send_command(config: ConfigUtils, server_name: str, command: str) -> str:
    """发送 RCON 命令。"""
    # 获取 CCA 配置
    cca_config = config.get_cca_client_config()

    # 如果有 CCA
    cca_servers = []
    if cca_config and cca_config != "":
        if not cca_config.startswith(("http://", "https://")):
            return "CCA Client 配置的地址不对喵~"
        # 获取 CCA 的服务器列表
        try:
            cca_url = cca_config.split(",")[0].strip()
            cca_token = cca_config.split(",")[1].strip()
            headers = {"Authorization": f"Bearer {cca_token}"}
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{cca_url}/api/servers", headers=headers)
                cca_servers = response.json().get("data", [])
        except Exception as e:
            logger.error(f"获取 CCA 服务器列表失败: {e}")
            cca_servers = []

    # 如果是 CCA 的服务器，走 send_cca_command 方法
    if cca_config and cca_config != "" and server_name in cca_servers:
        if not command.startswith("/"):
            command = "/" + command
        res = await send_cca_command(cca_config, server_name, command)
        # 接去掉 MCDR 的日志部分 “[00:00:00] [Server thread/INFO]: ”
        res = re.sub(
            r"^\[\d{2}:\d{2}:\d{2}\] \[Server thread/INFO\]: ",
            "",
            res,
            flags=re.MULTILINE,
        )
        return res

    # 不是的话走 rcon
    # 获取配置的服务器列表
    configured_servers = config.get_server_list()
    server = find_server_by_name(configured_servers, server_name)
    if server:
        return await rcon_send(
            host=server["host"],
            passwd=server["password"],
            port=int(server["port"]),
            command=command,
        )

    return f"没找到服务器 {server_name} 喵~"


async def send_cca_command(cca_config: str, server_name: str, command: str) -> str:
    """通过 MCDR console_command_api 执行命令并返回输出。"""
    if not cca_config:
        return "CCA Client 还没有配置喵~"
    if not cca_config.startswith(("http://", "https://")):
        return "CCA Client 配置的地址不对喵~"

    # 处理中文"！"
    command = command.replace("！！", "!!")

    # 准备参数
    try:
        url = cca_config.split(",")[0].strip()
        token = cca_config.split(",")[1].strip()
    except IndexError:
        return "CCA 配置格式不对喵~"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    # 发送请求
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.post(
                f"{url}/api/command",
                headers=headers,
                json={"command": command, "server_name": server_name},
            )
            response.raise_for_status()
        payload = response.json()
    except Exception as e:
        logger.error(
            f"服务器 {server_name} 的 MCDR 接口发生了错误: "
            f"command={command}, url={url}, body={response.text[:200]!r}, error={e}"
        )
        raise Exception("MCDR 接口报错了喵~") from e

    # 处理请求结果
    if payload.get("code") == 404:
        return f'"{server_name}"没有与 CCA Client 连接喵~"'
    if payload.get("code") != 200:
        logger.error(
            f"服务器 {server_name} 的 MCDR 接口返回失败: "
            f"command={command}, code={payload.get('code')}, msg={payload.get('msg')}"
        )
        raise Exception(payload.get("msg") or "MCDR 接口返回失败喵~")

    # 处理控制台响应结果
    data = payload.get("data") or {}
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return strip_mc_format_codes(output_text).strip()
    output = data.get("output")
    if isinstance(output, list):
        lines = []
        for line in output:
            cleaned_line = strip_mc_format_codes(str(line)).rstrip()
            if cleaned_line.strip():
                lines.append(cleaned_line)
        if lines:
            return "\n".join(lines)

    if data.get("timed_out"):
        return "MCDR 接口执行超时了喵~"

    return "没有返回结果喵~"


def strip_mc_format_codes(text: str) -> str:
    """移除 Minecraft 文本中的 § 样式代码。"""
    return MC_FORMAT_CODE_RE.sub("", text)


def parse_list_players(res: str) -> list[str]:
    """解析玩家列表"""
    if not res or ":" not in res:
        return []
    try:
        players_str = res.rsplit(":", 1)[1]
        if not players_str.strip():
            return []
        # 转为玩家list
        return [p.strip() for p in players_str.split(",") if p.strip()]
    except Exception:
        return []


async def get_whitelist(config_utils: ConfigUtils) -> list[str]:
    """获取白名单。"""
    servers = await config_utils.get_online_servers_name()
    wl = []
    for server_name in servers:
        try:
            res = await send_command(config_utils, server_name, "whitelist list")
            if "There are no whitelisted players" in res or res is None:
                continue
            # 最后一个冒号往后是玩家列表
            players_start = res.rfind(":") + 1
            players_str = res[players_start:].strip()
            wl.extend(
                [player.strip() for player in players_str.split(",") if player.strip()]
            )
        except EmptyResponse:
            logger.warning(
                f"服务器 {server_name} 连接失败，请检查配置是否正确，并且检查服务器是否已开启RCON服务"
            )
            continue
        except Exception as e:
            logger.error(f"服务器 {server_name} 白名单查询失败: {e}")
            continue
    return list(dict.fromkeys(wl))
