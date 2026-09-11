from typing import TypeVar

import wireup
from cachetools import TTLCache

from astrbot.api.star import Context
from astrbot.core import AstrBotConfig

T = TypeVar("T")


@wireup.injectable
class TaskTempCache(TTLCache):
    def __init__(self):
        super().__init__(maxsize=50, ttl=300)


_container = None


def init_container(astrbot_config: AstrBotConfig, context: Context):
    """初始化容器"""
    global _container

    if _container is not None:
        return _container

    from ..command.main import CommandUtils
    from ..db.main import DbUtils
    from ..http.main import AsyncHttpClient
    from ..loc.main import LocUtils
    from ..media.image import ImageUtils
    from ..message.main import MessageUtils
    from ..task.main import TaskUtils
    from ..whitelist.main import WhitelistUtils
    from ..wiki.main import WikiUtils
    from .main import ConfigUtils

    # 创建同步容器
    _container = wireup.create_sync_container(
        injectables=[
            TaskTempCache,
            ConfigUtils,
            CommandUtils,
            DbUtils,
            MessageUtils,
            ImageUtils,
            LocUtils,
            TaskUtils,
            WikiUtils,
            WhitelistUtils,
            AsyncHttpClient,
        ],
        # 参数注入
        config={
            "astrbot_config": astrbot_config,
            "context": context,
        },
    )

    return _container

def get_container():
    """获取全局容器实例"""
    if _container is None:
        raise RuntimeError("Container not initialized.")
    return _container

def get_service(service_type: type[T]) -> T:
    """直接从容器获取服务"""
    if _container is None:
        raise RuntimeError("Container not initialized.")
    return _container.get(service_type)
