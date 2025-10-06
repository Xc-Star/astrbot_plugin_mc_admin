from functools import wraps


def in_enabled_groups():
    """
    装饰器：仅当事件所在群在配置的 enabled_groups 内时才继续执行。
    要求被修饰方法签名形如 (self, event, ...)，且 self.config 可用。
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(self, event, *args, **kwargs):
            config = getattr(self, "config", None)
            enabled_groups = None
            if config is not None:
                if hasattr(config, "get"):
                    enabled_groups = config.get("enabled_groups")
                else:
                    enabled_groups = getattr(config, "enabled_groups", None)
            try:
                group_id = event.get_group_id()
            except Exception:
                group_id = None
            if not enabled_groups or group_id not in enabled_groups:
                return
            # 透传异步生成器
            async for result in func(self, event, *args, **kwargs):
                yield result

        return wrapper

    return decorator


def requires_enabled(field_name: str, message: str, allow_admin_bypass: bool = False):
    """
    装饰器：检查配置中某开关字段是否启用；未启用则给出提示信息。
    - field_name: 配置中的布尔字段名
    - message: 未启用时给出的提示文案
    - allow_admin_bypass: 若为 True，管理员可绕过开关直接执行
    需配合 (self, event, ...) 签名，self.config 与 event.is_admin() 可用。
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(self, event, *args, **kwargs):
            config = getattr(self, "config", None)
            is_enabled = False
            if config is not None:
                if hasattr(config, "get"):
                    is_enabled = bool(config.get(field_name))
                else:
                    is_enabled = bool(getattr(config, field_name, False))
            if not is_enabled:
                if allow_admin_bypass and hasattr(event, "is_admin") and event.is_admin():
                    async for result in func(self, event, *args, **kwargs):
                        yield result
                    return
                if hasattr(event, "plain_result"):
                    # 返回提示信息
                    yield event.plain_result(message)
                    return
                return
            async for result in func(self, event, *args, **kwargs):
                yield result

        return wrapper

    return decorator


