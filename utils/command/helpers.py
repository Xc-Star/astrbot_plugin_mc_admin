import re
from ..rcon import rcon_send
from typing import Optional, List, Dict, Tuple
from astrbot.api import logger
from rcon.exceptions import EmptyResponse


# 常量
PERMISSION_DENIED = '我才不听你的呢'

# 预编译正则
LOC_ADD_RE = re.compile(r'^loc add\s+([\w\\s]+?)\s+([012])\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)$')
LOC_SET_RE = re.compile(r'^loc set\s+([\w\\s]+?)\s+([012])\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)$')
MC_COMMAND_RE = re.compile(r'^mc command \w+ (.*)$')


def find_server_by_name(servers: List[Dict], name: str) -> Optional[Dict]:
    """根据服务器名字查找服务器"""
    for server in servers:
        if server.get('name') == name:
            return server
    return None


async def send_command(server: Dict, command: str) -> str:
    """发送命令"""
    return await rcon_send(
        host=server["host"],
        passwd=server["password"],
        port=int(server["port"]),
        command=command
    )


def parse_list_players(res: str) -> List[str]:
    """解析玩家列表"""
    if not res or ':' not in res:
        return []
    try:
        players_str = res.split(':', 1)[1]
        if not players_str.strip():
            return []
        return [p.strip() for p in players_str.split(',') if p.strip()]
    except Exception:
        return []


async def get_whitelist(servers: List[Dict]) -> List[str]:
    """获取白名单"""
    wl = None
    for server in servers:
        try:
            wl = await send_command(server, 'whitelist list')
            break
        except EmptyResponse:
            logger.error(f"服务器 {server['name']} 连接失败，请检查配置是否正确，并且检查服务器是否已开启RCON服务")
            continue
        except Exception as e:
            logger.error(f"服务器 {server['name']} 白名单查询失败: {e}")
            continue
    if wl == 'There are no whitelisted players' or wl is None:
        return []
    players_start = wl.find(':') + 1
    players_str = wl[players_start:].strip()
    return [player.strip() for player in players_str.split(',') if player.strip()]


def split_players_by_whitelist(players: List[str], whitelist_list: List[str]) -> Tuple[List[str], List[str]]:
    """根据白名单分割玩家列表"""
    whitelist_set = set(whitelist_list)
    bot_players = [p for p in players if p not in whitelist_set]
    real_players = [p for p in players if p in whitelist_set]
    return bot_players, real_players


def is_bot_player(player_name: str, bot_prefix: str) -> bool:
    """判断是否是bot（忽略大小写），同时忽略过短ID"""
    if not player_name or len(player_name) < 3:
        return False
    return player_name.lower().startswith(bot_prefix.lower())


def split_players_by_prefix(players: List[str], bot_prefix: str) -> Tuple[List[str], List[str]]:
    """根据假人前缀分割玩家列表"""
    bot_players = [p for p in players if is_bot_player(p, bot_prefix)]
    real_players = [p for p in players if not is_bot_player(p, bot_prefix)]
    return bot_players, real_players


