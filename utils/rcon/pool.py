import asyncio
import threading
import time
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from mcrcon import MCRcon
from astrbot.api import logger


class RconConnection:
    """单个Rcon连接包装器"""
    
    def __init__(self, host: str, password: str, port: int, timeout: int = 10):
        self.host = host
        self.port = port
        self.password = password
        self.timeout = timeout
        self._rcon: Optional[MCRcon] = None
        self._lock = threading.Lock()
        self._last_used = time.time()  # 使用time.time()而不是asyncio.get_event_loop().time()
        self._is_connected = False
    
    def _connect(self):
        """建立连接"""
        if self._is_connected and self._rcon is not None:
            return
        
        try:
            self._rcon = MCRcon(self.host, self.password, self.port, timeout=self.timeout)
            self._rcon.connect()
            self._is_connected = True
            logger.debug(f"Rcon连接已建立: {self.host}:{self.port}")
        except Exception as e:
            # logger.error(f"Rcon连接失败 {self.host}:{self.port}: {e}")
            self._is_connected = False
            raise
    
    def _disconnect(self):
        """断开连接"""
        if self._rcon is not None:
            try:
                self._rcon.disconnect()
                logger.debug(f"Rcon连接已断开: {self.host}:{self.port}")
            except Exception as e:
                logger.warning(f"断开Rcon连接时出错 {self.host}:{self.port}: {e}")
            finally:
                self._rcon = None
                self._is_connected = False
    
    def send_command(self, command: str) -> str:
        """发送命令（同步方法，在线程池中执行）"""
        with self._lock:
            try:
                if not self._is_connected:
                    self._connect()
                
                self._last_used = time.time()  # 使用time.time()而不是asyncio.get_event_loop().time()
                result = self._rcon.command(command)
                return result
            except Exception as e:
                logger.error(f"发送Rcon命令失败 {self.host}:{self.port}: {e}")
                # 连接出错时断开连接，下次使用时重新连接
                self._disconnect()
                raise
    
    def is_healthy(self) -> bool:
        """检查连接是否健康"""
        return self._is_connected and self._rcon is not None
    
    def get_idle_time(self) -> float:
        """获取空闲时间（秒）"""
        return time.time() - self._last_used


class RconPool:
    """Rcon连接池管理器"""
    
    def __init__(self, max_connections_per_server: int = 3, idle_timeout: int = 300):
        self.max_connections_per_server = max_connections_per_server
        self.idle_timeout = idle_timeout  # 5分钟空闲超时
        self._connections: Dict[str, list] = {}  # server_key -> [RconConnection]
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=20, thread_name_prefix="rcon")
        self._cleanup_task = None
        self._start_cleanup_task()
    
    def _get_server_key(self, host: str, port: int) -> str:
        """生成服务器唯一标识"""
        return f"{host}:{port}"
    
    def _get_connection(self, host: str, password: str, port: int) -> RconConnection:
        """获取或创建连接"""
        server_key = self._get_server_key(host, port)
        
        with self._lock:
            if server_key not in self._connections:
                self._connections[server_key] = []
            
            connections = self._connections[server_key]
            
            # 查找可用的连接
            for conn in connections:
                if conn.is_healthy():
                    return conn
            
            # 如果没有可用连接且未达到最大连接数，创建新连接
            if len(connections) < self.max_connections_per_server:
                new_conn = RconConnection(host, password, port)
                connections.append(new_conn)
                return new_conn
            
            # 如果达到最大连接数，返回第一个连接（即使可能不健康）
            if connections:
                return connections[0]
            
            # 如果列表为空，创建新连接
            new_conn = RconConnection(host, password, port)
            connections.append(new_conn)
            return new_conn
    
    async def send_command(self, host: str, password: str, port: int, command: str) -> str:
        """异步发送命令"""
        connection = self._get_connection(host, password, port)
        
        # 在线程池中执行同步的Rcon操作
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                self._executor, 
                connection.send_command, 
                command
            )
            return result
        except Exception as e:
            # logger.error(f"异步发送Rcon命令失败 {host}:{port}: {e}")
            raise
    
    def _start_cleanup_task(self):
        """启动清理任务"""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_idle_connections())
    
    async def _cleanup_idle_connections(self):
        """清理空闲连接"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                with self._lock:
                    current_time = time.time()
                    
                    for server_key, connections in list(self._connections.items()):
                        # 移除空闲时间过长的连接
                        connections_to_remove = []
                        for conn in connections:
                            if conn.get_idle_time() > self.idle_timeout:
                                connections_to_remove.append(conn)
                        
                        for conn in connections_to_remove:
                            conn._disconnect()
                            connections.remove(conn)
                            logger.debug(f"清理空闲连接: {server_key}")
                        
                        # 如果服务器没有连接了，移除服务器条目
                        if not connections:
                            del self._connections[server_key]
                            
            except Exception as e:
                logger.error(f"清理空闲连接时出错: {e}")
    
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            for connections in self._connections.values():
                for conn in connections:
                    conn._disconnect()
            self._connections.clear()
        
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
        
        self._executor.shutdown(wait=True)
        logger.info("Rcon连接池已关闭")


# 全局连接池实例
_rcon_pool: Optional[RconPool] = None


def get_rcon_pool() -> RconPool:
    """获取全局Rcon连接池实例"""
    global _rcon_pool
    if _rcon_pool is None:
        _rcon_pool = RconPool()
    return _rcon_pool


def close_rcon_pool():
    """关闭全局Rcon连接池"""
    global _rcon_pool
    if _rcon_pool is not None:
        _rcon_pool.close_all()
        _rcon_pool = None
