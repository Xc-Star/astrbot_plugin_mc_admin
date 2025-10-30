import asyncio
from playwright.async_api import async_playwright
from astrbot.api import logger


class BrowserManager:
    """Browser 管理器，用于统一管理 Playwright browser 实例"""
    
    def __init__(self):
        # 懒加载的 browser 实例
        self._playwright = None
        self._browser = None
        self._browser_lock = None
    
    def _get_lock(self):
        """获取或创建浏览器锁"""
        if self._browser_lock is None:
            self._browser_lock = asyncio.Lock()
        return self._browser_lock
    
    async def ensure_browser(self):
        """确保 browser 已初始化（懒加载）"""
        lock = self._get_lock()
        async with lock:
            if self._browser is None or not self._browser.is_connected():
                try:
                    self._playwright = await async_playwright().start()
                    self._browser = await self._playwright.chromium.launch()
                except Exception as e:
                    logger.error(f"初始化 browser 失败: {e}")
                    raise
    
    async def close(self):
        """关闭 browser 实例"""
        lock = self._get_lock()
        async with lock:
            if self._browser and self._browser.is_connected():
                try:
                    await self._browser.close()
                except Exception as e:
                    logger.error(f"关闭 browser 失败: {e}")
                finally:
                    self._browser = None
                    self._playwright = None
    
    @property
    def browser(self):
        """获取 browser 实例（需先调用 ensure_browser）"""
        if self._browser is None:
            raise RuntimeError("Browser 未初始化，请先调用 ensure_browser()")
        return self._browser

