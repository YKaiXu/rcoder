#!/usr/bin/env python3
"""
Rcoder核心模块（优化版本）
针对低带宽场景和异步操作进行了优化
"""

import ssl
import socket
import json
import time
import asyncio
import hashlib
import threading
import queue
import gzip
import zlib
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
    Rcoder核心类（优化版本）
    针对低带宽场景和异步操作进行了优化
    """
    
    def __init__(self, host: str = '192.168.1.8', port: int = 443, use_https_disguise: bool = True, 
                 proxy_server: Optional[Tuple[str, int]] = None, enable_compression: bool = True,
                 enable_connection_pool: bool = True, connection_pool_size: int = 5, password: Optional[str] = None):
        """
        初始化Rcoder核心
        
        Args:
            host: 服务器主机
            port: 服务器端口 (默认443，支持HTTPS伪装)
            use_https_disguise: 是否使用HTTPS伪装
            proxy_server: 中转服务器 (host, port)，如 ('1.2.3.4', 443)
            enable_compression: 是否启用数据压缩
            enable_connection_pool: 是否启用连接池
            connection_pool_size: 连接池大小
            password: 认证密码
        """
        self.host = host
        self.port = port
        self.use_https_disguise = use_https_disguise
        self.proxy_server = proxy_server
        self.enable_compression = enable_compression
        self.enable_connection_pool = enable_connection_pool
        self.connection_pool_size = connection_pool_size
        self.password = password
        self.ssl_context = self._create_ssl_context()
        self.token = None
        self._monitoring_enabled = False
        self._monitoring_thread = None
        self._alert_queue = queue.Queue()
        self._command_queue = queue.Queue()
        self._results = {}
        self._lock = threading.Lock()
        self._session_id = hashlib.sha256(str(time.time()).encode()).hexdigest()
        
        # 连接池相关
        self._connection_pool = queue.Queue(maxsize=connection_pool_size)
        self._pool_lock = threading.Lock()
        self._connection_expiry = 300  # 连接过期时间（秒）
        self._connection_times = {}
        
        # 缓存相关
        self._command_cache = {}
        self._cache_expiry = 60  # 缓存过期时间（秒）
        
        # 网络优化参数
        self._timeout = 60
        self._retry_delay = 0.5  # 初始重试延迟
        self._max_retry_delay = 5  # 最大重试延迟
        
        # 新增策略参数
        self.enable_minimal_payload = False  # 是否启用最小化负载
        self.enable_exponential_backoff = False  # 是否启用指数退避
        self.enable_breakpoint_resume = False  # 是否启用断点续传
        
        config_info = f"{host}:{port} (HTTPS伪装: {'启用' if use_https_disguise else '禁用'})"
        if proxy_server:
            config_info += f" (中转服务器: {proxy_server[0]}:{proxy_server[1]})"
        
        # 优化功能提示
        optimizations = []
        if enable_compression:
            optimizations.append("数据压缩")
        if enable_connection_pool:
            optimizations.append("连接池")
        if optimizations:
            config_info += f" (优化: {', '.join(optimizations)})"
        
        print(f"✅ Rcoder初始化完成 (会话ID: {self._session_id[:8]})]")
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
    
    def _get_connection(self):
        """从连接池获取连接"""
        if not self.enable_connection_pool:
            return self._create_connection()
        
        with self._pool_lock:
            # 清理过期连接
            current_time = time.time()
            valid_connections = []
            while not self._connection_pool.empty():
                conn = self._connection_pool.get()
                conn_id = id(conn)
                if current_time - self._connection_times.get(conn_id, 0) < self._connection_expiry:
                    try:
                        # 测试连接是否有效
                        conn.send(b'')
                        valid_connections.append(conn)
                    except:
                        pass
            
            # 将有效连接放回池
            for conn in valid_connections:
                if not self._connection_pool.full():
                    self._connection_pool.put(conn)
            
            # 获取连接
            if not self._connection_pool.empty():
                conn = self._connection_pool.get()
                self._connection_times[id(conn)] = current_time
                return conn
        
        # 没有可用连接，创建新连接
        return self._create_connection()
    
    def _create_connection(self):
        """创建新连接"""
        # 建立TCP连接（支持中转服务器）
        if self.proxy_server:
            sock = socket.create_connection((self.proxy_server[0], self.proxy_server[1]), timeout=self._timeout)
            
            # 发送代理连接请求（简化版，减少数据传输）
            proxy_connect = f"CONNECT {self.host}:{self.port} HTTP/1.1\r\n"
            proxy_connect += f"Host: {self.host}:{self.port}\r\n"
            proxy_connect += "Connection: Keep-Alive\r\n"
            proxy_connect += "\r\n"
            
            sock.send(proxy_connect.encode())
            # 读取代理响应（丢弃）
            sock.recv(4096)
        else:
            # 直接连接
            sock = socket.create_connection((self.host, self.port), timeout=self._timeout)
        
        # 增强HTTPS伪装：添加HTTP请求头模拟（简化版）
        if self.use_https_disguise:
            # 简化的HTTP伪装，减少数据传输
            http_request = "GET / HTTP/1.1\r\n"
            http_request += f"Host: {self.host}:{self.port}\r\n"
            http_request += "User-Agent: Mozilla/5.0\r\n"
            http_request += "Connection: keep-alive\r\n"
            http_request += "\r\n"
            
            sock.send(http_request.encode())
            # 读取HTTP响应（丢弃）
            sock.recv(4096)
        
        # 包装为TLS连接
        server_hostname = f"{self.host}" if self.use_https_disguise else "rcoder"
        tls_sock = self.ssl_context.wrap_socket(sock, server_hostname=server_hostname)
        
        return tls_sock
    
    def _return_connection(self, conn):
        """将连接放回连接池"""
        if self.enable_connection_pool:
            with self._pool_lock:
                if not self._connection_pool.full():
                    try:
                        self._connection_pool.put(conn)
                        self._connection_times[id(conn)] = time.time()
                        return True
                    except:
                        pass
        
        # 无法放回池，关闭连接
        try:
            conn.close()
        except:
            pass
        return False
    
    def _compress_data(self, data):
        """压缩数据"""
        if not self.enable_compression:
            return data
        
        try:
            compressed = gzip.compress(data)
            # 只有当压缩后数据更小时才使用压缩
            if len(compressed) < len(data):
                return compressed
        except:
            pass
        return data
    
    def _decompress_data(self, data):
        """解压数据"""
        if not self.enable_compression:
            return data
        
        try:
            return gzip.decompress(data)
        except:
            return data
    
    def _call(self, method: str, params: Dict[str, Any] = None, 
              retry_on_failure: bool = True, max_retries: int = 3) -> Dict[str, Any]:
        """执行JSON-RPC调用，优化低带宽场景
        
        Args:
            method: RPC方法名
            params: RPC参数
            retry_on_failure: 是否在失败时重试
            max_retries: 最大重试次数
        """
        retry_count = 0
        current_delay = self._retry_delay
        
        while retry_count <= max_retries:
            conn = None
            try:
                # 获取连接
                conn = self._get_connection()
                
                # 构建请求
                request = {
                    "jsonrpc": "2.0",
                    "id": int(time.time() * 1000),
                    "method": method,
                    "params": params or {},
                    "sid": self._session_id[:8],  # 简化的session_id
                    "ts": int(time.time())
                }
                
                # 添加认证信息
                if self.password:
                    request['auth'] = {
                        'type': 'password',
                        'password': self.password
                    }
                
                # 最小化负载
                if self.enable_minimal_payload:
                    # 移除可选字段
                    if "params" in request and not request["params"]:
                        del request["params"]
                
                # 序列化请求
                request_data = json.dumps(request, separators=(',', ':')).encode()
                
                # 压缩数据
                if self.enable_compression:
                    compressed_data = self._compress_data(request_data)
                    # 添加压缩标记
                    if len(compressed_data) < len(request_data):
                        request_data = b'COMPRESSED:' + compressed_data
                
                # 发送请求
                conn.send(request_data + b"\n")
                
                # 接收响应（优化：使用循环接收，处理大数据）
                response_data = b''
                while True:
                    chunk = conn.recv(8192)  # 增大接收缓冲区
                    if not chunk:
                        break
                    response_data += chunk
                    # 如果收到完整的JSON响应，提前结束
                    if b'\n' in response_data:
                        break
                
                # 处理压缩响应
                if response_data.startswith(b'COMPRESSED:'):
                    response_data = self._decompress_data(response_data[10:])
                
                if not response_data:
                    if retry_on_failure and retry_count < max_retries:
                        retry_count += 1
                        # 指数退避
                        if self.enable_exponential_backoff:
                            current_delay = min(current_delay * (2 ** retry_count), self._max_retry_delay * 2)
                        else:
                            current_delay = min(current_delay * 1.5, self._max_retry_delay)
                        time.sleep(current_delay)
                        continue
                    raise Exception("Empty response from server")
                
                # 解析响应
                response = json.loads(response_data)
                
                # 检查认证错误
                if 'error' in response:
                    error_msg = response['error'].get('message', str(response['error']))
                    if 'auth' in error_msg.lower() or 'password' in error_msg.lower() or 'login' in error_msg.lower():
                        raise Exception(f"认证失败: {error_msg}. 请检查用户名和密码是否正确。")
                    raise Exception(f"服务器错误: {error_msg}")
                
                return response
                
            except (socket.error, ConnectionResetError, ConnectionRefusedError) as e:
                error_msg = str(e)
                if 'Connection refused' in error_msg or '10061' in error_msg:
                    if self.password:
                        raise Exception(f"连接失败: {error_msg}. 可能的原因: 服务器未运行、端口错误或认证失败。")
                    else:
                        raise Exception(f"连接失败: {error_msg}. 可能的原因: 服务器未运行或端口错误。")
                
                if retry_on_failure and retry_count < max_retries:
                    retry_count += 1
                    # 指数退避
                    if self.enable_exponential_backoff:
                        current_delay = min(current_delay * (2 ** retry_count), self._max_retry_delay * 2)
                    else:
                        current_delay = min(current_delay * 1.5, self._max_retry_delay)
                    time.sleep(current_delay)
                    continue
                raise
            except json.JSONDecodeError as e:
                if retry_on_failure and retry_count < max_retries:
                    retry_count += 1
                    # 指数退避
                    if self.enable_exponential_backoff:
                        current_delay = min(current_delay * (2 ** retry_count), self._max_retry_delay * 2)
                    else:
                        current_delay = min(current_delay * 1.5, self._max_retry_delay)
                    time.sleep(current_delay)
                    continue
                raise
            except Exception as e:
                if retry_on_failure and retry_count < max_retries:
                    # 跳过认证错误的重试
                    if '认证失败' in str(e):
                        raise
                    
                    retry_count += 1
                    # 指数退避
                    if self.enable_exponential_backoff:
                        current_delay = min(current_delay * (2 ** retry_count), self._max_retry_delay * 2)
                    else:
                        current_delay = min(current_delay * 1.5, self._max_retry_delay)
                    time.sleep(current_delay)
                    continue
                raise
            finally:
                if conn:
                    self._return_connection(conn)
    
    def _get_cache_key(self, method, params):
        """生成缓存键"""
        return hashlib.md5(f"{method}:{json.dumps(params, sort_keys=True)}".encode()).hexdigest()
    
    def _get_cached_result(self, method, params):
        """获取缓存的结果"""
        cache_key = self._get_cache_key(method, params)
        if cache_key in self._command_cache:
            cached = self._command_cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_expiry:
                return cached['result']
            # 缓存过期，删除
            del self._command_cache[cache_key]
        return None
    
    def _set_cached_result(self, method, params, result):
        """设置缓存的结果"""
        cache_key = self._get_cache_key(method, params)
        self._command_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        # 清理过期缓存
        current_time = time.time()
        expired_keys = [k for k, v in self._command_cache.items() 
                       if current_time - v['timestamp'] >= self._cache_expiry]
        for key in expired_keys:
            del self._command_cache[key]
    
    def execute(self, server: str, command: str, timeout: int = 60, 
                wait_for_restart: bool = False, restart_check_interval: int = 2, 
                restart_max_wait: int = 60, use_cache: bool = True) -> str:
        """执行命令，优化低带宽场景
        
        Args:
            server: 服务器名称
            command: 命令
            timeout: 超时时间
            wait_for_restart: 是否等待重启完成
            restart_check_interval: 重启检查间隔
            restart_max_wait: 最大重启等待时间
            use_cache: 是否使用缓存
        """
        # 检查缓存
        if use_cache:
            cache_key = f"execute:{server}:{command}"
            if cache_key in self._command_cache:
                cached = self._command_cache[cache_key]
                if time.time() - cached['timestamp'] < self._cache_expiry:
                    return cached['result']
        
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
                    # 尝试重新连接并检查服务是否可用（使用更简单的命令）
                    test_result = self._call(
                        "tools/call", 
                        {
                            "name": "ssh_exec",
                            "arguments": {"name": server, "command": "echo 1", "timeout": 5}
                        },
                        retry_on_failure=True,
                        max_retries=1  # 减少重试次数，加快检测
                    )
                    
                    if "result" in test_result:
                        print(f"✅ 服务已重启完成 (耗时: {elapsed:.1f}秒)")
                        result = f"重启完成 (耗时: {elapsed:.1f}秒)"
                        # 缓存结果
                        if use_cache:
                            self._command_cache[cache_key] = {
                                'result': result,
                                'timestamp': time.time()
                            }
                        return result
                        
                except (socket.error, ConnectionResetError, ConnectionRefusedError):
                    # 重启过程中的连接错误是预期的
                    print(f"  ⏳ 服务正在重启中... ({elapsed:.1f}秒)")
                except Exception:
                    # 其他错误
                    print(f"  ⏳ 等待服务恢复... ({elapsed:.1f}秒)")
                
                print(f"⏳ 等待中... ({elapsed:.1f}/{restart_max_wait}秒)")
            
            print(f"❌ 重启等待超时 ({restart_max_wait}秒)")
            result = f"重启命令已执行，但等待超时 ({restart_max_wait}秒)"
            # 缓存结果
            if use_cache:
                self._command_cache[cache_key] = {
                    'result': result,
                    'timestamp': time.time()
                }
            return result
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
                output = data.get("stdout", "") or data.get("stderr", "") or data.get("error", "")
                # 缓存结果
                if use_cache:
                    self._command_cache[cache_key] = {
                        'result': output,
                        'timestamp': time.time()
                    }
                return output
            
            result_str = str(result)
            # 缓存结果
            if use_cache:
                self._command_cache[cache_key] = {
                    'result': result_str,
                    'timestamp': time.time()
                }
            return result_str
    
    async def execute_async(self, server: str, command: str, timeout: int = 60, use_cache: bool = True) -> str:
        """异步执行命令，优化低带宽场景"""
        # 使用asyncio的事件循环，优化异步性能
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.execute, 
            server, 
            command, 
            timeout,
            False,
            2,
            60,
            use_cache
        )
    
    def execute_batch(self, server: str, commands: List[str], timeout: int = 60, 
                     use_cache: bool = True, parallel: bool = False) -> Dict[str, str]:
        """批量执行命令，优化低带宽场景
        
        Args:
            server: 服务器名称
            commands: 命令列表
            timeout: 超时时间
            use_cache: 是否使用缓存
            parallel: 是否并行执行
        """
        results = {}
        
        # 检查缓存
        cached_commands = []
        for command in commands:
            cache_key = f"execute:{server}:{command}"
            if use_cache and cache_key in self._command_cache:
                cached = self._command_cache[cache_key]
                if time.time() - cached['timestamp'] < self._cache_expiry:
                    results[command] = cached['result']
                    cached_commands.append(command)
        
        # 执行未缓存的命令
        uncached_commands = [cmd for cmd in commands if cmd not in cached_commands]
        
        if parallel and uncached_commands:
            # 并行执行
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(5, len(uncached_commands))) as executor:
                future_to_command = {
                    executor.submit(self.execute, server, cmd, timeout, False, 2, 60, use_cache): cmd
                    for cmd in uncached_commands
                }
                for future in concurrent.futures.as_completed(future_to_command):
                    cmd = future_to_command[future]
                    try:
                        results[cmd] = future.result()
                    except Exception as e:
                        results[cmd] = f"Error: {e}"
        else:
            # 串行执行
            for command in uncached_commands:
                try:
                    result = self.execute(server, command, timeout=timeout, use_cache=use_cache)
                    results[command] = result
                except Exception as e:
                    results[command] = f"Error: {e}"
        
        return results
    
    async def execute_batch_async(self, server: str, commands: List[str], timeout: int = 60, 
                                 use_cache: bool = True) -> Dict[str, str]:
        """异步批量执行命令，优化低带宽场景"""
        # 优化：先检查缓存
        cached_results = {}
        uncached_commands = []
        
        for command in commands:
            cache_key = f"execute:{server}:{command}"
            if use_cache and cache_key in self._command_cache:
                cached = self._command_cache[cache_key]
                if time.time() - cached['timestamp'] < self._cache_expiry:
                    cached_results[command] = cached['result']
                    continue
            uncached_commands.append(command)
        
        # 只对未缓存的命令执行异步操作
        if not uncached_commands:
            return cached_results
        
        # 异步执行
        tasks = []
        for command in uncached_commands:
            task = self.execute_async(server, command, timeout, use_cache)
            tasks.append(task)
        
        uncached_results = await asyncio.gather(*tasks)
        uncached_dict = dict(zip(uncached_commands, uncached_results))
        
        # 合并结果
        cached_results.update(uncached_dict)
        return cached_results
    
    def list_connections(self) -> Dict[str, Any]:
        """列出SSH连接"""
        # 检查缓存
        cache_key = "list_connections"
        if cache_key in self._command_cache:
            cached = self._command_cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_expiry:
                return cached['result']
        
        result = self._call("tools/list")
        
        # 缓存结果
        self._command_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        return result
    
    def connect(self, server: str) -> Dict[str, Any]:
        """连接到SSH服务器"""
        result = self._call("tools/call", {
            "name": "ssh_connect",
            "arguments": {"name": server}
        })
        return result
    
    def disconnect(self, server: str) -> Dict[str, Any]:
        """断开SSH连接"""
        result = self._call("tools/call", {
            "name": "ssh_disconnect",
            "arguments": {"name": server}
        })
        return result
    
    def start_monitoring(self, interval: int = 30, lightweight: bool = True):
        """启动监控，优化低带宽场景
        
        Args:
            interval: 监控间隔（秒）
            lightweight: 是否使用轻量级监控
        """
        def monitor():
            while self._monitoring_enabled:
                try:
                    if lightweight:
                        # 轻量级监控，减少网络请求
                        status = self.execute('local', 'uptime')
                        print(f"[监控] 服务器状态: {status.strip()}")
                    else:
                        # 完整监控
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
        """添加告警"""
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
        # 检查缓存
        cache_key = "server_info"
        if cache_key in self._command_cache:
            cached = self._command_cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_expiry * 5:  # 服务器信息缓存时间更长
                return cached['result']
        
        result = self._call("initialize")
        
        # 缓存结果
        self._command_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        return result
    
    def get_available_tools(self) -> Dict[str, Any]:
        """获取可用工具"""
        # 检查缓存
        cache_key = "available_tools"
        if cache_key in self._command_cache:
            cached = self._command_cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_expiry * 5:  # 工具列表缓存时间更长
                return cached['result']
        
        result = self._call("tools/list")
        
        # 缓存结果
        self._command_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        return result
    

    
    def shutdown(self):
        """关闭资源"""
        # 停止监控
        self.stop_monitoring()
        
        # 清理连接池
        if self.enable_connection_pool:
            with self._pool_lock:
                while not self._connection_pool.empty():
                    try:
                        conn = self._connection_pool.get()
                        conn.close()
                    except:
                        pass
        
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
    
    def run(self, command: str, timeout: int = 60, wait_for_restart: bool = False, 
             use_cache: bool = True) -> str:
        """运行命令，优化低带宽场景
        
        Args:
            command: 命令
            timeout: 超时时间
            wait_for_restart: 是否等待重启完成
            use_cache: 是否使用缓存
        """
        return self.rcoder.execute(
            self.server, 
            command, 
            timeout=timeout, 
            wait_for_restart=wait_for_restart,
            use_cache=use_cache
        )
    
    async def run_async(self, command: str, timeout: int = 60, use_cache: bool = True) -> str:
        """异步运行命令，优化低带宽场景"""
        return await self.rcoder.execute_async(self.server, command, timeout, use_cache)
    
    def run_batch(self, commands: List[str], timeout: int = 60, 
                  use_cache: bool = True, parallel: bool = False) -> Dict[str, str]:
        """批量运行命令，优化低带宽场景
        
        Args:
            commands: 命令列表
            timeout: 超时时间
            use_cache: 是否使用缓存
            parallel: 是否并行执行
        """
        return self.rcoder.execute_batch(
            self.server, 
            commands, 
            timeout=timeout,
            use_cache=use_cache,
            parallel=parallel
        )
    
    async def run_batch_async(self, commands: List[str], timeout: int = 60, 
                             use_cache: bool = True) -> Dict[str, str]:
        """异步批量运行命令，优化低带宽场景"""
        return await self.rcoder.execute_batch_async(
            self.server, 
            commands, 
            timeout=timeout,
            use_cache=use_cache
        )
    
    def ls(self, path: str = '.', use_cache: bool = True) -> str:
        """列出目录内容，优化低带宽场景"""
        return self.run(f'ls -la {path}', use_cache=use_cache)
    
    def cat(self, file: str, use_cache: bool = True) -> str:
        """查看文件内容，优化低带宽场景"""
        return self.run(f'cat {file}', use_cache=use_cache)
    
    def mkdir(self, path: str) -> str:
        """创建目录"""
        return self.run(f'mkdir -p {path}', use_cache=False)  # 不使用缓存，因为是修改操作
    
    def rm(self, path: str, recursive: bool = False) -> str:
        """删除文件或目录"""
        cmd = f'rm -rf {path}' if recursive else f'rm {path}'
        return self.run(cmd, use_cache=False)  # 不使用缓存，因为是修改操作
    
    def cp(self, source: str, destination: str) -> str:
        """复制文件或目录"""
        return self.run(f'cp -r {source} {destination}', use_cache=False)  # 不使用缓存，因为是修改操作
    
    def mv(self, source: str, destination: str) -> str:
        """移动文件或目录"""
        return self.run(f'mv {source} {destination}', use_cache=False)  # 不使用缓存，因为是修改操作
    
    def systemctl(self, action: str, service: str) -> str:
        """管理系统服务"""
        wait_for_restart = action == 'restart'
        return self.run(
            f'sudo systemctl {action} {service}',
            wait_for_restart=wait_for_restart,
            use_cache=False  # 不使用缓存，因为是服务操作
        )
    
    def ps(self, use_cache: bool = True) -> str:
        """查看进程，优化低带宽场景"""
        return self.run('ps aux', use_cache=use_cache)
    
    def top(self, use_cache: bool = True) -> str:
        """查看系统负载，优化低带宽场景"""
        return self.run('top -b -n 1', use_cache=use_cache)
    
    def free(self, use_cache: bool = True) -> str:
        """查看内存使用，优化低带宽场景"""
        return self.run('free -h', use_cache=use_cache)
    
    def df(self, use_cache: bool = True) -> str:
        """查看磁盘使用，优化低带宽场景"""
        return self.run('df -h', use_cache=use_cache)
    
    def uptime(self, use_cache: bool = True) -> str:
        """查看系统运行时间，优化低带宽场景"""
        return self.run('uptime', use_cache=use_cache)
    
    def hostname(self, use_cache: bool = True) -> str:
        """查看主机名，优化低带宽场景"""
        return self.run('hostname', use_cache=use_cache)
    
    def ip(self, use_cache: bool = True) -> str:
        """查看IP地址，优化低带宽场景"""
        return self.run('ip addr', use_cache=use_cache)
    
    def ping(self, host: str, count: int = 2) -> str:
        """ping主机，优化低带宽场景（减少ping次数）"""
        return self.run(f'ping -c {count} {host}', use_cache=False)


def get_remote_host(host: str = '192.168.1.8', port: int = 443, server: str = 'local', 
                   use_https_disguise: bool = True, proxy_server: Optional[Tuple[str, int]] = None,
                   enable_compression: bool = True, enable_connection_pool: bool = True, 
                   password: Optional[str] = None) -> RemoteHost:
    """获取远程主机管理实例，优化低带宽场景
    
    Args:
        host: Rcoder服务器主机
        port: Rcoder服务器端口 (默认443，支持HTTPS伪装)
        server: 服务器名称
        use_https_disguise: 是否使用HTTPS伪装
        proxy_server: 中转服务器 (host, port)，如 ('1.2.3.4', 443)
        enable_compression: 是否启用数据压缩
        enable_connection_pool: 是否启用连接池
        password: 认证密码
    """
    rcoder = RcoderCore(
        host=host, 
        port=port, 
        use_https_disguise=use_https_disguise, 
        proxy_server=proxy_server,
        enable_compression=enable_compression,
        enable_connection_pool=enable_connection_pool,
        password=password
    )
    return RemoteHost(rcoder, server=server)
