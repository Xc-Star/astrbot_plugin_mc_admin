import re
from typing import Dict, List, Optional, Tuple

import httpx
from astrbot.api import logger
from rcon.exceptions import EmptyResponse

from ..rcon import rcon_send


PERMISSION_DENIED = "我才不听你的呢"

LOC_ADD_RE = re.compile(
    r"^loc add\s+([\w\\s]+?)\s+([012])\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)$"
)
LOC_SET_RE = re.compile(
    r"^loc set\s+([\w\\s]+?)\s+([012])\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)$"
)
MC_COMMAND_RE = re.compile(r"^mc command \w+ (.*)$")
MCDR_COMMAND_RE = re.compile(r"^(?:mcdr|dr)\s+(\S+)\s+(.+)$")
MC_FORMAT_CODE_RE = re.compile(r"§.")


def find_server_by_name(servers: List[Dict], name: str) -> Optional[Dict]:
    """根据服务器名字查找服务器。"""
    for server in servers:
        if server.get("name") == name:
            return server
    return None


async def send_command(server: Dict, command: str) -> str:
    """发送 RCON 命令。"""
    return await rcon_send(
        host=server["host"],
        passwd=server["password"],
        port=int(server["port"]),
        command=command,
    )


async def send_mcdr_command(cca_url: str, server_name: str, command: str) -> str:
    """通过 MCDR console_command_api 执行命令并返回输出。"""
    if not cca_url or not isinstance(cca_url, str):
        return "CCA Client 还没有配置喵~"
    if not cca_url.startswith(('http://', 'https://')):
        return "CCA Client 配置的地址不对喵~"

    command = normalize_mcdr_command(command)

    try:
        url = f"{cca_url.split(",")[0]}/api/command"
        token = cca_url.split(",")[1].strip()
    except IndexError:
        return "CCA 配置格式不对喵~"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.post(url, headers=headers, json={"command": command, "server_name": server_name})
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        logger.error(
            f"服务器 {server_name} 的 MCDR 接口返回异常状态码: "
            f"command={command}, status={e.response.status_code}, url={url}"
        )
        raise
    except httpx.HTTPError as e:
        logger.error(
            f"服务器 {server_name} 的 MCDR 接口请求失败: command={command}, url={url}, error={e}"
        )
        raise

    try:
        payload = response.json()
    except ValueError as e:
        logger.error(
            f"服务器 {server_name} 的 MCDR 接口返回了非法 JSON: "
            f"command={command}, url={url}, body={response.text[:200]!r}, error={e}"
        )
        raise ValueError("MCDR 接口返回了无法解析的数据喵~") from e

    if payload.get("code") == 404:
        return f"\"{server_name}\"没有与 CCA Client 连接喵~"
    if payload.get("code") != 200:
        logger.error(
            f"服务器 {server_name} 的 MCDR 接口返回失败: "
            f"command={command}, code={payload.get('code')}, msg={payload.get('msg')}"
        )
        raise ValueError(payload.get("msg") or "MCDR 接口返回失败喵~")

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


def normalize_mcdr_command(command: str) -> str:
    """将常见的全角 MCDR 命令前缀归一化为半角。"""
    return command.replace("！！", "!!")


def parse_list_players(res: str) -> List[str]:
    """解析玩家列表。"""
    if not res or ":" not in res:
        return []
    try:
        players_str = res.split(":", 1)[1]
        if not players_str.strip():
            return []
        return [p.strip() for p in players_str.split(",") if p.strip()]
    except Exception:
        return []


async def get_whitelist(servers: List[Dict]) -> List[str]:
    """获取白名单。"""
    wl = None
    for server in servers:
        try:
            wl = await send_command(server, "whitelist list")
            break
        except EmptyResponse:
            logger.error(
                f"服务器 {server['name']} 连接失败，请检查配置是否正确，并且检查服务器是否已开启RCON服务"
            )
            continue
        except Exception as e:
            logger.error(f"服务器 {server['name']} 白名单查询失败: {e}")
            continue
    if wl == "There are no whitelisted players" or wl is None:
        return []
    players_start = wl.find(":") + 1
    players_str = wl[players_start:].strip()
    return [player.strip() for player in players_str.split(",") if player.strip()]


def split_players_by_whitelist(
    players: List[str], whitelist_list: List[str]
) -> Tuple[List[str], List[str]]:
    """根据白名单分割玩家列表。"""
    whitelist_set = set(whitelist_list)
    bot_players = [p for p in players if p not in whitelist_set]
    real_players = [p for p in players if p in whitelist_set]
    return bot_players, real_players


def is_bot_player(player_name: str, bot_prefix: str) -> bool:
    """判断是否是 bot，同时忽略过短 ID。"""
    if not player_name or len(player_name) < 3:
        return False
    return player_name.lower().startswith(bot_prefix.lower())


def split_players_by_prefix(
    players: List[str], bot_prefix: str
) -> Tuple[List[str], List[str]]:
    """根据假人前缀分割玩家列表。"""
    bot_players = [p for p in players if is_bot_player(p, bot_prefix)]
    real_players = [p for p in players if not is_bot_player(p, bot_prefix)]
    return bot_players, real_players
