from functools import wraps


def in_enabled_groups():
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
            async for result in func(self, event, *args, **kwargs):
                yield result

        return wrapper

    return decorator


def requires_enabled(field_name: str, message: str, allow_admin_bypass: bool = False):
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
                    yield event.plain_result(message)
                    return
                return
            async for result in func(self, event, *args, **kwargs):
                yield result

        return wrapper

    return decorator
