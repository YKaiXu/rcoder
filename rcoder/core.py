#!/usr/bin/env python3
"""
Rcoder核心模块
实现远程代码执行与管理的核心功能
"""
import ssl
import socket
import json
import time
import asyncio
import hashlib
import threading
import queue
from typing import Dict, Any, Optional, List, Tuple, Callable
from dataclasses import dataclass

@dataclass
class CommandResult:
    """命令执行结果"""
    stdout: str
    stderr: str
    returncode: int
    execution_time: float

@dataclass
class BatchResult:
    """批量命令执行结果"""
    command: str
    results: Dict[str, CommandResult]
    success_count: int
    failure_count: int
    total_time: float

class RcoderCore:
    """
    Rcoder核心类
    实现远程代码执行与管理的核心功能
    """
    
    def __init__(self, host: str = '192.168.1.8', port: int = 443, use_https_disguise: bool = True, proxy_server: Optional[Tuple[str, int]] = None):
        """
        初始化Rcoder核心
        
        Args:
            host: 服务器主机
            port: 服务器端口 (默认443，支持HTTPS伪装)
            use_https_disguise: 是否使用HTTPS伪装
            proxy_server: 中转服务器 (host, port)，如 ('1.2.3.4', 443)
        """
        # 参数验证
        if not host or not isinstance(host, str):
            raise ValueError("主机名不能为空且必须是字符串")
        
        if not isinstance(port, int) or port <= 0 or port > 65535:
            raise ValueError("端口号必须是1-65535之间的整数")
        
        if proxy_server and (not isinstance(proxy_server, tuple) or len(proxy_server) != 2):
            raise ValueError("代理服务器必须是(host, port)格式的元组")
        
        if proxy_server and (not proxy_server[0] or not isinstance(proxy_server[0], str)):
            raise ValueError("代理服务器主机名不能为空且必须是字符串")
        
        if proxy_server and (not isinstance(proxy_server[1], int) or proxy_server[1] <= 0 or proxy_server[1] > 65535):
            raise ValueError("代理服务器端口号必须是1-65535之间的整数")
        
        self.host = host
        self.port = port
        self.use_https_disguise = use_https_disguise
        self.proxy_server = proxy_server
        self.ssl_context = self._create_ssl_context()
        self.token = None
        self.public_key = None
        self.private_key = None
        self._monitoring_enabled = False
        self._monitoring_thread = None
        self._alert_queue = queue.Queue()
        self._command_queue = queue.Queue()
        self._results = {}
        self._lock = threading.Lock()
        self._session_id = hashlib.sha256(str(time.time()).encode()).hexdigest()
        
        config_info = f"{host}:{port} (HTTPS伪装: {'启用' if use_https_disguise else '禁用'})"
        if proxy_server:
            config_info += f" (中转服务器: {proxy_server[0]}:{proxy_server[1]})"
        
        print(f"✅ Rcoder初始化完成 (会话ID: {self._session_id[:8]})")
        print(f"📡 连接配置: {config_info}")
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """创建SSL上下文，增强HTTPS伪装"""
        context = ssl.create_default_context()
        
        # 增强HTTPS伪装
        if self.use_https_disguise:
            # 模拟标准HTTPS客户端行为
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            context.maximum_version = ssl.TLSVersion.TLSv1_3
            
            # 禁用主机名检查以支持自定义端口
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # 模拟常见浏览器的密码套件偏好
            context.set_ciphers('ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-AES128-SHA256:ECDHE-RSA-AES256-SHA384:AES128-GCM-SHA256:AES256-GCM-SHA384')
        else:
            # 标准模式
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        
        return context
    
    def _call(self, method: str, params: Dict[str, Any] = None, 
              retry_on_failure: bool = True, max_retries: int = 5) -> Dict[str, Any]:
        """执行JSON-RPC调用，增强HTTPS伪装
        
        Args:
            method: RPC方法名
            params: RPC参数
            retry_on_failure: 是否在失败时重试
            max_retries: 最大重试次数
        """
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # 建立TCP连接（支持中转服务器）
                if self.proxy_server:
                    print(f"  🔄 通过中转服务器连接: {self.proxy_server[0]}:{self.proxy_server[1]}")
                    sock = socket.create_connection((self.proxy_server[0], self.proxy_server[1]), timeout=30)
                    
                    # 发送代理连接请求
                    proxy_connect = f"CONNECT {self.host}:{self.port} HTTP/1.1\r\n"
                    proxy_connect += f"Host: {self.host}:{self.port}\r\n"
                    proxy_connect += "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36\r\n"
                    proxy_connect += "Connection: Keep-Alive\r\n"
                    proxy_connect += "\r\n"
                    
                    sock.send(proxy_connect.encode())
                    # 读取代理响应
                    proxy_response = sock.recv(4096)
                    if b"200 Connection established" not in proxy_response:
                        raise Exception(f"Proxy connection failed: {proxy_response.decode()}")
                    print(f"  ✅ 中转服务器连接成功")
                else:
                    # 直接连接
                    sock = socket.create_connection((self.host, self.port), timeout=30)
                
                # 增强HTTPS伪装：添加HTTP请求头模拟
                if self.use_https_disguise:
                    # 模拟HTTP请求头
                    http_headers = {
                        "Host": f"{self.host}:{self.port}",
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                        "Accept-Encoding": "gzip, deflate, br",
                        "Connection": "keep-alive",
                        "Upgrade-Insecure-Requests": "1",
                        "Sec-Fetch-Dest": "document",
                        "Sec-Fetch-Mode": "navigate",
                        "Sec-Fetch-Site": "none",
                        "Sec-Fetch-User": "?1",
                        "Cache-Control": "max-age=0"
                    }
                    
                    # 构建HTTP请求
                    http_request = "GET / HTTP/1.1\r\n"
                    for key, value in http_headers.items():
                        http_request += f"{key}: {value}\r\n"
                    http_request += "\r\n"
                    
                    # 发送HTTP请求作为伪装
                    sock.send(http_request.encode())
                    # 读取HTTP响应（丢弃）
                    sock.recv(4096)
                
                # 包装为TLS连接
                server_hostname = f"{self.host}" if self.use_https_disguise else "rcoder"
                tls_sock = self.ssl_context.wrap_socket(sock, server_hostname=server_hostname)
                
                # 构建请求，增强安全性
                request = {
                    "jsonrpc": "2.0",
                    "id": int(time.time() * 1000),
                    "method": method,
                    "params": params or {},
                    "session_id": self._session_id[:16],
                    "timestamp": int(time.time()),
                    "version": "1.0"
                }
                
                # 发送请求
                request_data = json.dumps(request).encode() + b"\n"
                tls_sock.send(request_data)
                
                # 接收响应
                response = tls_sock.recv(65536)
                tls_sock.close()
                
                if not response:
                    if retry_on_failure and retry_count < max_retries:
                        retry_count += 1
                        time.sleep(1)
                        continue
                    raise Exception("Empty response from server")
                
                # 解析响应
                return json.loads(response)
                
            except (socket.error, ConnectionResetError, ConnectionRefusedError) as e:
                if retry_on_failure and retry_count < max_retries:
                    retry_count += 1
                    time.sleep(1)
                    continue
                raise
            except json.JSONDecodeError as e:
                if retry_on_failure and retry_count < max_retries:
                    retry_count += 1
                    time.sleep(1)
                    continue
                raise
            except Exception as e:
                if retry_on_failure and retry_count < max_retries:
                    retry_count += 1
                    time.sleep(1)
                    continue
                raise
    
    def execute(self, server: str, command: str, timeout: int = 60, 
                wait_for_restart: bool = False, restart_check_interval: int = 2, 
                restart_max_wait: int = 60) -> str:
        """执行命令
        
        Args:
            server: 服务器名称
            command: 命令
            timeout: 超时时间
            wait_for_restart: 是否等待重启完成
            restart_check_interval: 重启检查间隔
            restart_max_wait: 最大重启等待时间
        """
        # 检查是否为重启命令
        is_restart_command = any(keyword in command.lower() for keyword in [
            'restart', 'systemctl restart', 'service restart', 'reboot'
        ])
        
        if is_restart_command and wait_for_restart:
            print(f"执行重启命令并等待完成...")
            print(f"命令: {command}")
            print(f"最大等待时间: {restart_max_wait}秒")
            
            try:
                # 执行重启命令
                result = self._call("tools/call", {
                    "name": "ssh_exec",
                    "arguments": {"name": server, "command": command, "timeout": timeout}
                })
                
                if "result" in result:
                    data = json.loads(result["result"]["content"][0]["text"])
                    print(f"重启命令执行结果: {data.get('stdout', '').strip() or data.get('stderr', '').strip()}")
            except Exception as e:
                print(f"重启命令执行异常: {e}")
                # 继续等待，因为重启命令可能已经开始执行
            
            # 等待重启完成
            start_time = time.time()
            elapsed = 0
            
            print("等待服务重启...")
            while elapsed < restart_max_wait:
                time.sleep(restart_check_interval)
                elapsed = time.time() - start_time
                
                try:
                    # 尝试重新连接并检查服务是否可用
                    test_result = self._call(
                        "tools/call", 
                        {
                            "name": "ssh_exec",
                            "arguments": {"name": server, "command": "echo 'Rcoder service available'", "timeout": 10}
                        },
                        retry_on_failure=True,
                        max_retries=2
                    )
                    
                    if "result" in test_result:
                        test_data = json.loads(test_result["result"]["content"][0]["text"])
                        if "Rcoder service available" in test_data.get("stdout", ""):
                            print(f"✅ 服务已重启完成 (耗时: {elapsed:.1f}秒)")
                            return f"重启完成 (耗时: {elapsed:.1f}秒)"
                            
                except (socket.error, ConnectionResetError, ConnectionRefusedError) as e:
                    # 重启过程中的连接错误是预期的
                    print(f"  ⏳ 服务正在重启中... ({elapsed:.1f}秒)")
                except json.JSONDecodeError as e:
                    # 重启过程中可能会出现响应不完整的情况
                    print(f"  ⏳ 服务响应不完整，继续等待... ({elapsed:.1f}秒)")
                except Exception as e:
                    # 其他错误
                    print(f"  ⏳ 等待服务恢复... ({elapsed:.1f}秒)")
                
                print(f"⏳ 等待中... ({elapsed:.1f}/{restart_max_wait}秒)")
            
            print(f"❌ 重启等待超时 ({restart_max_wait}秒)")
            return f"重启命令已执行，但等待超时 ({restart_max_wait}秒)"
        else:
            # 正常命令执行
            start_time = time.time()
            result = self._call("tools/call", {
                "name": "ssh_exec",
                "arguments": {"name": server, "command": command, "timeout": timeout}
            })
            execution_time = time.time() - start_time
            
            if "result" in result:
                data = json.loads(result["result"]["content"][0]["text"])
                return data.get("stdout", "") or data.get("stderr", "") or data.get("error", "")
            return str(result)
    
    async def execute_async(self, server: str, command: str, timeout: int = 60) -> str:
        """异步执行命令"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.execute, 
            server, 
            command, 
            timeout
        )
    
    def execute_batch(self, server: str, commands: List[str], timeout: int = 60) -> Dict[str, str]:
        """批量执行命令
        
        Args:
            server: 服务器名称
            commands: 命令列表
            timeout: 超时时间
        """
        results = {}
        for command in commands:
            try:
                result = self.execute(server, command, timeout=timeout)
                results[command] = result
            except Exception as e:
                results[command] = f"Error: {e}"
        return results
    
    async def execute_batch_async(self, server: str, commands: List[str], timeout: int = 60) -> Dict[str, str]:
        """异步批量执行命令"""
        tasks = []
        for command in commands:
            task = self.execute_async(server, command, timeout)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return dict(zip(commands, results))
    
    def list_connections(self) -> Dict[str, Any]:
        """列出SSH连接"""
        result = self._call("tools/call", {"name": "ssh_list", "arguments": {}})
        if "result" in result:
            return json.loads(result["result"]["content"][0]["text"])
        return result
    
    def connect(self, server: str) -> Dict[str, Any]:
        """连接到SSH服务器"""
        result = self._call("tools/call", {
            "name": "ssh_connect",
            "arguments": {"name": server}
        })
        if "result" in result:
            return json.loads(result["result"]["content"][0]["text"])
        return result
    
    def disconnect(self, server: str) -> Dict[str, Any]:
        """断开SSH连接"""
        result = self._call("tools/call", {
            "name": "ssh_disconnect",
            "arguments": {"name": server}
        })
        if "result" in result:
            return json.loads(result["result"]["content"][0]["text"])
        return result
    
    def start_monitoring(self, interval: int = 30):
        """启动监控
        
        Args:
            interval: 监控间隔（秒）
        """
        def monitor():
            while self._monitoring_enabled:
                try:
                    # 检查服务器状态
                    status = self.execute('local', 'uptime')
                    print(f"[监控] 服务器状态: {status.strip()}")
                    
                    # 检查内存使用
                    memory = self.execute('local', 'free -h')
                    print(f"[监控] 内存使用:\n{memory.strip()}")
                    
                    # 检查磁盘使用
                    disk = self.execute('local', 'df -h')
                    print(f"[监控] 磁盘使用:\n{disk.strip()}")
                    
                except Exception as e:
                    print(f"[监控] 错误: {e}")
                
                time.sleep(interval)
        
        self._monitoring_enabled = True
        self._monitoring_thread = threading.Thread(target=monitor, daemon=True)
        self._monitoring_thread.start()
        print("✅ 监控已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self._monitoring_enabled = False
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5)
        print("✅ 监控已停止")
    
    def add_alert(self, condition: Callable[[], bool], message: str):
        """添加告警
        
        Args:
            condition: 告警条件
            message: 告警消息
        """
        if condition():
            self._alert_queue.put(message)
            print(f"⚠️  告警: {message}")
    
    def get_alerts(self) -> List[str]:
        """获取告警列表"""
        alerts = []
        while not self._alert_queue.empty():
            alerts.append(self._alert_queue.get())
        return alerts
    
    def get_server_info(self) -> Dict[str, Any]:
        """获取服务器信息"""
        result = self._call("initialize")
        if "result" in result:
            return result["result"]
        return result
    
    def get_available_tools(self) -> Dict[str, Any]:
        """获取可用工具"""
        result = self._call("tools/list")
        if "result" in result:
            return result["result"]
        return result
    
    def setup_key_auth(self, public_key: str, private_key: str):
        """设置密钥认证
        
        Args:
            public_key: 公钥
            private_key: 私钥
        """
        self.public_key = public_key
        self.private_key = private_key
        print("✅ 密钥认证已设置")
    
    def shutdown(self):
        """关闭资源"""
        self.stop_monitoring()
        print("✅ Rcoder已关闭")


class RemoteHost:
    """
    远程主机管理类
    提供类似本地主机的使用体验
    """
    
    def __init__(self, rcoder: RcoderCore, server: str = 'local'):
        """
        初始化远程主机管理
        
        Args:
            rcoder: Rcoder核心实例
            server: 服务器名称
        """
        self.rcoder = rcoder
        self.server = server
    
    def run(self, command: str, timeout: int = 60, wait_for_restart: bool = False) -> str:
        """运行命令
        
        Args:
            command: 命令
            timeout: 超时时间
            wait_for_restart: 是否等待重启完成
        """
        return self.rcoder.execute(
            self.server, 
            command, 
            timeout=timeout, 
            wait_for_restart=wait_for_restart
        )
    
    async def run_async(self, command: str, timeout: int = 60) -> str:
        """异步运行命令"""
        return await self.rcoder.execute_async(self.server, command, timeout)
    
    def run_batch(self, commands: List[str], timeout: int = 60) -> Dict[str, str]:
        """批量运行命令"""
        return self.rcoder.execute_batch(self.server, commands, timeout)
    
    async def run_batch_async(self, commands: List[str], timeout: int = 60) -> Dict[str, str]:
        """异步批量运行命令"""
        return await self.rcoder.execute_batch_async(self.server, commands, timeout)
    
    def ls(self, path: str = '.') -> str:
        """列出目录内容"""
        return self.run(f'ls -la {path}')
    
    def cat(self, file: str) -> str:
        """查看文件内容"""
        return self.run(f'cat {file}')
    
    def mkdir(self, path: str) -> str:
        """创建目录"""
        return self.run(f'mkdir -p {path}')
    
    def rm(self, path: str, recursive: bool = False) -> str:
        """删除文件或目录"""
        if recursive:
            return self.run(f'rm -rf {path}')
        return self.run(f'rm {path}')
    
    def cp(self, source: str, destination: str) -> str:
        """复制文件或目录"""
        return self.run(f'cp -r {source} {destination}')
    
    def mv(self, source: str, destination: str) -> str:
        """移动文件或目录"""
        return self.run(f'mv {source} {destination}')
    
    def systemctl(self, action: str, service: str) -> str:
        """管理系统服务
        
        Args:
            action: 动作 (start, stop, restart, status)
            service: 服务名称
        """
        wait_for_restart = action == 'restart'
        return self.run(
            f'sudo systemctl {action} {service}',
            wait_for_restart=wait_for_restart
        )
    
    def ps(self) -> str:
        """查看进程"""
        return self.run('ps aux')
    
    def top(self) -> str:
        """查看系统负载"""
        return self.run('top -b -n 1')
    
    def free(self) -> str:
        """查看内存使用"""
        return self.run('free -h')
    
    def df(self) -> str:
        """查看磁盘使用"""
        return self.run('df -h')
    
    def uptime(self) -> str:
        """查看系统运行时间"""
        return self.run('uptime')
    
    def hostname(self) -> str:
        """查看主机名"""
        return self.run('hostname')
    
    def ip(self) -> str:
        """查看IP地址"""
        return self.run('ip addr')
    
    def ping(self, host: str, count: int = 4) -> str:
        """ping主机"""
        return self.run(f'ping -c {count} {host}')


def get_remote_host(host: str = '192.168.1.8', port: int = 443, server: str = 'local', use_https_disguise: bool = True, proxy_server: Optional[Tuple[str, int]] = None) -> RemoteHost:
    """获取远程主机管理实例
    
    Args:
        host: Rcoder服务器主机
        port: Rcoder服务器端口 (默认443，支持HTTPS伪装)
        server: 服务器名称
        use_https_disguise: 是否使用HTTPS伪装
        proxy_server: 中转服务器 (host, port)，如 ('1.2.3.4', 443)
    """
    rcoder = RcoderCore(host=host, port=port, use_https_disguise=use_https_disguise, proxy_server=proxy_server)
    return RemoteHost(rcoder, server=server)
