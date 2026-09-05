import json
import os
from pathlib import Path
from urllib.request import pathname2url
from astrbot.api import logger
import httpx

from astrbot.core import AstrBotConfig


class ConfigUtils:

    def __init__(self, config: AstrBotConfig):
        self.enable_groups = config.get("enabled_groups")
        self.bot_prefix = config.get("bot_prefix")
        self.server_list = self._parse_server_list(config.get("servers_config"))
        self.cca_client_url = config.get("cca_client_url")

        self.enable_whitelist_compare = config.get("enable_whitelist_compare")
        self.enable_background_image = config.get("enable_background_image")
        self.enable_big_task_image = config.get("enable_big_task_image")

        self.background_image_path = None
        if (
            config.get("background_image_path") == ""
            or config.get("background_image_path") is None
        ):
            current_file_path = os.path.abspath(__file__)
            plugin_path = os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))
            self.background_image_path = os.path.join(
                plugin_path, "data", "background_image"
            )
        else:
            self.background_image_path = config.get("background_image_path")

    def get_server_list(self) -> list[dict]:
        return self.server_list
    
    async def get_online_servers_name(self) -> list[str]:
        """获取在线的服务器名称列表"""
        configured_servers: list[str] = [
            str(server["name"]) for server in self.server_list if server.get("name")
        ]
        cca_servers = await get_cca_servers(self.cca_client_url)
        return list(dict.fromkeys(configured_servers + cca_servers))

    def get_cca_client_url(self) -> str:
        return str(self.cca_client_url).strip()

    def _parse_server_list(self, servers_config) -> list[dict]:
        raw_servers = self._load_servers_config(servers_config)
        server_list = []

        for server in raw_servers:
            if not isinstance(server, dict):
                continue

            name = str(server.get("name", "")).strip()
            host = str(server.get("rcon_ip", "")).strip()
            password = str(server.get("rcon_password", "")).strip()
            port = self._parse_int(server.get("rcon_port"))

            if not name or not host or port is None or not password:
                continue

            server_list.append(
                {
                    "name": name,
                    "host": host,
                    "port": port,
                    "password": password,
                }
            )

        return server_list

    def _load_servers_config(self, servers_config) -> list:
        if isinstance(servers_config, list):
            return servers_config

        if isinstance(servers_config, str):
            text = servers_config.strip()
            if not text:
                return []
            try:
                data = json.loads(text)
                return data if isinstance(data, list) else []
            except json.JSONDecodeError:
                return []

        return []

    def _parse_int(self, value):
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    def get_bot_prefix(self) -> str:
        return str(self.bot_prefix)

    def get_plugin_path(self):
        current_file_path = os.path.abspath(__file__)
        return os.path.dirname(os.path.dirname(os.path.dirname(current_file_path)))

    def get_font(self):
        plugin_path = self.get_plugin_path()
        font_path = os.path.join(
            plugin_path, "template", "font", "jiyinghuipianheyuan.ttf"
        )

        abs_path = os.path.abspath(font_path)
        path_obj = Path(abs_path)
        posix_path = path_obj.as_posix()
        url_path = pathname2url(posix_path)
        file_url = f"file:///{url_path}"

        return file_url

async def get_cca_servers(cca_url: str) -> list[str]:
    """获取 CCA 上的所有服务器名称。"""
    if not cca_url or not isinstance(cca_url, str):
        return []
    # 从 CCA URL 中解析出 API 地址和 Token
    try:
        url = f"{cca_url.split(',')[0]}/api/servers"
        token = cca_url.split(',')[1].strip()
    except IndexError:
        logger.error("CCA 配置格式不对")
        return []
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != 200:
                logger.error(f"获取 CCA 服务器列表失败: code={payload.get('code')}, msg={payload.get('msg')}")
                return []
            data = payload.get("data") or []
            return data
    except Exception as e:
        logger.error(f"获取 CCA 服务器列表失败: error={e}")
        return []