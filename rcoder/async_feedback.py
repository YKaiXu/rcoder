#!/usr/bin/env python3
"""
Rcoder 异步反馈模块
针对中转场景和低带宽场景的异步操作反馈机制优化
"""

import time
import asyncio
import threading
import queue
import json
from typing import Optional, List, Dict, Any, Callable

class AsyncFeedback:
    """
    异步反馈类
    提供实时进度反馈、断点续传、网络状态监测等功能
    """
    
    def __init__(self, remote_host):
        """
        初始化异步反馈
        
        Args:
            remote_host: RemoteHost实例
        """
        self.remote_host = remote_host
        self._progress_queue = queue.Queue()
        self._status_queue = queue.Queue()
        self._result_queue = queue.Queue()
        self._cancel_events = {}
        self._active_tasks = {}
        self._lock = threading.Lock()
        self._network_monitor = None
        self._bandwidth_history = []
        self._last_network_check = 0
        self._network_check_interval = 30  # 网络检查间隔（秒）
    
    def _monitor_network(self):
        """
        监控网络状态
        """
        while True:
            try:
                start_time = time.time()
                # 测试网络延迟
                result = self.remote_host.run("echo 1", use_cache=False)
                end_time = time.time()
                latency = (end_time - start_time) * 1000  # 毫秒
                
                # 测试带宽（简化版）
                bandwidth_test = self.remote_host.run("curl -s -w '%{speed_download}' -o /dev/null https://speed.hetzner.de/10MB.bin", use_cache=False)
                try:
                    bandwidth = float(bandwidth_test.strip()) / (1024 * 1024)  # MB/s
                except:
                    bandwidth = 0
                
                # 记录网络状态
                network_status = {
                    'timestamp': time.time(),
                    'latency': latency,
                    'bandwidth': bandwidth,
                    'status': 'stable' if latency < 500 and bandwidth > 0.1 else 'unstable'
                }
                
                self._bandwidth_history.append(network_status)
                # 只保留最近10条记录
                if len(self._bandwidth_history) > 10:
                    self._bandwidth_history.pop(0)
                
                # 发送网络状态更新
                self._status_queue.put({
                    'type': 'network_status',
                    'data': network_status
                })
                
            except Exception as e:
                # 网络检查失败
                self._status_queue.put({
                    'type': 'network_error',
                    'data': {'error': str(e)}
                })
            
            time.sleep(self._network_check_interval)
    
    def start_network_monitor(self):
        """
        启动网络监控
        """
        if not self._network_monitor:
            self._network_monitor = threading.Thread(target=self._monitor_network, daemon=True)
            self._network_monitor.start()
            print("✅ 网络监控已启动")
    
    def stop_network_monitor(self):
        """
        停止网络监控
        """
        if self._network_monitor:
            # 线程是守护线程，会自动退出
            self._network_monitor = None
            print("✅ 网络监控已停止")
    
    def get_network_status(self) -> Dict[str, Any]:
        """
        获取当前网络状态
        """
        if not self._bandwidth_history:
            return {
                'status': 'unknown',
                'message': '网络状态尚未检测'
            }
        
        latest = self._bandwidth_history[-1]
        return {
            'status': latest['status'],
            'latency': f"{latest['latency']:.2f}ms",
            'bandwidth': f"{latest['bandwidth']:.2f} MB/s",
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(latest['timestamp']))
        }
    
    def get_bandwidth_trend(self) -> List[Dict[str, Any]]:
        """
        获取带宽趋势
        """
        return self._bandwidth_history
    
    async def run_with_progress(self, command: str, task_id: Optional[str] = None, 
                               use_cache: bool = False) -> Dict[str, Any]:
        """
        带进度反馈的异步执行命令
        
        Args:
            command: 要执行的命令
            task_id: 任务ID
            use_cache: 是否使用缓存
        """
        if not task_id:
            task_id = f"task_{int(time.time() * 1000)}"
        
        # 创建取消事件
        self._cancel_events[task_id] = threading.Event()
        
        # 发送任务开始状态
        self._status_queue.put({
            'type': 'task_started',
            'data': {
                'task_id': task_id,
                'command': command,
                'timestamp': time.time()
            }
        })
        
        # 网络状态检查
        network_status = self.get_network_status()
        self._status_queue.put({
            'type': 'network_pre_check',
            'data': network_status
        })
        
        # 根据网络状态调整策略
        if network_status['status'] == 'unstable':
            self._status_queue.put({
                'type': 'warning',
                'data': {
                    'message': '网络状态不稳定，将启用容错模式',
                    'suggestions': ['启用断点续传', '增加超时时间', '减少并发数']
                }
            })
        
        try:
            # 执行命令
            self._active_tasks[task_id] = {
                'status': 'running',
                'start_time': time.time(),
                'command': command
            }
            
            # 发送进度更新
            self._progress_queue.put({
                'task_id': task_id,
                'progress': 0,
                'status': '开始执行命令',
                'timestamp': time.time()
            })
            
            # 执行命令（带智能重试）
            result = await self._execute_with_retry(command, task_id, use_cache)
            
            # 计算执行时间
            execution_time = time.time() - self._active_tasks[task_id]['start_time']
            
            # 更新任务状态
            self._active_tasks[task_id]['status'] = 'completed'
            self._active_tasks[task_id]['end_time'] = time.time()
            self._active_tasks[task_id]['execution_time'] = execution_time
            
            # 发送完成状态
            self._progress_queue.put({
                'task_id': task_id,
                'progress': 100,
                'status': '命令执行完成',
                'timestamp': time.time()
            })
            
            # 发送结果
            result_data = {
                'task_id': task_id,
                'command': command,
                'result': result,
                'execution_time': execution_time,
                'status': 'success'
            }
            
            self._result_queue.put(result_data)
            self._status_queue.put({
                'type': 'task_completed',
                'data': result_data
            })
            
            return result_data
            
        except Exception as e:
            # 发送错误状态
            error_data = {
                'task_id': task_id,
                'command': command,
                'error': str(e),
                'timestamp': time.time()
            }
            
            self._status_queue.put({
                'type': 'task_failed',
                'data': error_data
            })
            
            return {
                'task_id': task_id,
                'command': command,
                'result': f"错误: {e}",
                'status': 'error'
            }
        finally:
            # 清理资源
            with self._lock:
                if task_id in self._cancel_events:
                    del self._cancel_events[task_id]
                if task_id in self._active_tasks:
                    del self._active_tasks[task_id]
    
    async def _execute_with_retry(self, command: str, task_id: str, 
                                 use_cache: bool = False, max_retries: int = 3) -> str:
        """
        带智能重试的命令执行
        
        Args:
            command: 要执行的命令
            task_id: 任务ID
            use_cache: 是否使用缓存
            max_retries: 最大重试次数
        """
        retry_count = 0
        base_delay = 1
        
        while retry_count <= max_retries:
            try:
                if retry_count > 0:
                    # 发送重试状态
                    self._status_queue.put({
                        'type': 'retry',
                        'data': {
                            'task_id': task_id,
                            'retry_count': retry_count,
                            'max_retries': max_retries,
                            'timestamp': time.time()
                        }
                    })
                
                # 执行命令
                result = await self.remote_host.run_async(command, use_cache=use_cache)
                
                # 发送进度更新
                self._progress_queue.put({
                    'task_id': task_id,
                    'progress': 75,
                    'status': '命令执行中',
                    'timestamp': time.time()
                })
                
                return result
                
            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    raise
                
                # 计算退避时间
                delay = base_delay * (2 ** (retry_count - 1))
                
                # 发送重试等待状态
                self._status_queue.put({
                    'type': 'retry_wait',
                    'data': {
                        'task_id': task_id,
                        'retry_count': retry_count,
                        'delay': delay,
                        'error': str(e),
                        'timestamp': time.time()
                    }
                })
                
                # 等待重试
                await asyncio.sleep(delay)
    
    async def download_with_progress(self, url: str, destination: str, 
                                   task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        带进度反馈的异步下载
        
        Args:
            url: 下载URL
            destination: 保存路径
            task_id: 任务ID
        """
        if not task_id:
            task_id = f"download_{int(time.time() * 1000)}"
        
        # 创建取消事件
        self._cancel_events[task_id] = threading.Event()
        
        # 发送任务开始状态
        self._status_queue.put({
            'type': 'download_started',
            'data': {
                'task_id': task_id,
                'url': url,
                'destination': destination,
                'timestamp': time.time()
            }
        })
        
        try:
            # 检查下载工具
            has_wget = 'wget' in self.remote_host.run('which wget', use_cache=True)
            has_curl = 'curl' in self.remote_host.run('which curl', use_cache=True)
            
            if not has_wget and not has_curl:
                raise Exception("远程主机未安装wget或curl")
            
            # 构建下载命令（带进度）
            if has_wget:
                # 使用wget下载，带进度
                download_cmd = f"wget -c --tries=10 --timeout=60 --progress=bar:force '{url}' -O '{destination}' 2>&1 | tail -n 1"
            else:
                # 使用curl下载，带进度
                download_cmd = f"curl -L --retry 10 --connect-timeout 60 --progress-bar '{url}' -o '{destination}'"
            
            # 执行下载
            self._active_tasks[task_id] = {
                'status': 'downloading',
                'start_time': time.time(),
                'url': url,
                'destination': destination
            }
            
            # 发送进度更新
            self._progress_queue.put({
                'task_id': task_id,
                'progress': 0,
                'status': '开始下载',
                'timestamp': time.time()
            })
            
            # 执行下载命令
            result = await self._execute_with_retry(download_cmd, task_id, use_cache=False)
            
            # 计算下载时间
            download_time = time.time() - self._active_tasks[task_id]['start_time']
            
            # 检查文件是否下载成功
            file_check = await self.remote_host.run_async(f"ls -la '{destination}'", use_cache=False)
            
            # 更新任务状态
            self._active_tasks[task_id]['status'] = 'completed'
            self._active_tasks[task_id]['end_time'] = time.time()
            self._active_tasks[task_id]['download_time'] = download_time
            
            # 发送完成状态
            self._progress_queue.put({
                'task_id': task_id,
                'progress': 100,
                'status': '下载完成',
                'timestamp': time.time()
            })
            
            # 计算下载速度
            file_size = 0
            try:
                size_cmd = await self.remote_host.run_async(f"du -b '{destination}'", use_cache=False)
                file_size = int(size_cmd.split()[0])
                speed = (file_size / (1024 * 1024)) / download_time  # MB/s
            except:
                speed = 0
            
            # 发送结果
            result_data = {
                'task_id': task_id,
                'url': url,
                'destination': destination,
                'file_size': f"{file_size / (1024 * 1024):.2f} MB" if file_size > 0 else '未知',
                'download_time': f"{download_time:.2f}秒",
                'speed': f"{speed:.2f} MB/s" if speed > 0 else '未知',
                'status': 'success',
                'timestamp': time.time()
            }
            
            self._result_queue.put(result_data)
            self._status_queue.put({
                'type': 'download_completed',
                'data': result_data
            })
            
            return result_data
            
        except Exception as e:
            # 发送错误状态
            error_data = {
                'task_id': task_id,
                'url': url,
                'error': str(e),
                'timestamp': time.time()
            }
            
            self._status_queue.put({
                'type': 'download_failed',
                'data': error_data
            })
            
            return {
                'task_id': task_id,
                'url': url,
                'error': str(e),
                'status': 'error'
            }
        finally:
            # 清理资源
            with self._lock:
                if task_id in self._cancel_events:
                    del self._cancel_events[task_id]
                if task_id in self._active_tasks:
                    del self._active_tasks[task_id]
    
    async def batch_with_progress(self, commands: List[str], task_id: Optional[str] = None, 
                                 use_cache: bool = False) -> Dict[str, Any]:
        """
        带进度反馈的异步批量执行
        
        Args:
            commands: 命令列表
            task_id: 任务ID
            use_cache: 是否使用缓存
        """
        if not task_id:
            task_id = f"batch_{int(time.time() * 1000)}"
        
        # 创建取消事件
        self._cancel_events[task_id] = threading.Event()
        
        # 发送任务开始状态
        self._status_queue.put({
            'type': 'batch_started',
            'data': {
                'task_id': task_id,
                'command_count': len(commands),
                'timestamp': time.time()
            }
        })
        
        try:
            self._active_tasks[task_id] = {
                'status': 'running',
                'start_time': time.time(),
                'command_count': len(commands),
                'completed_count': 0
            }
            
            results = {}
            total_commands = len(commands)
            
            # 发送初始进度
            self._progress_queue.put({
                'task_id': task_id,
                'progress': 0,
                'status': f'开始执行 {total_commands} 个命令',
                'timestamp': time.time()
            })
            
            # 逐个执行命令
            for i, command in enumerate(commands):
                if self._cancel_events[task_id].is_set():
                    raise Exception("任务已取消")
                
                # 发送命令开始状态
                self._status_queue.put({
                    'type': 'command_started',
                    'data': {
                        'task_id': task_id,
                        'command_index': i,
                        'command': command,
                        'timestamp': time.time()
                    }
                })
                
                # 执行命令
                try:
                    cmd_result = await self.remote_host.run_async(command, use_cache=use_cache)
                    results[command] = cmd_result
                    
                    # 发送命令完成状态
                    self._status_queue.put({
                        'type': 'command_completed',
                        'data': {
                            'task_id': task_id,
                            'command_index': i,
                            'command': command,
                            'success': True,
                            'timestamp': time.time()
                        }
                    })
                except Exception as e:
                    results[command] = f"错误: {e}"
                    
                    # 发送命令失败状态
                    self._status_queue.put({
                        'type': 'command_failed',
                        'data': {
                            'task_id': task_id,
                            'command_index': i,
                            'command': command,
                            'error': str(e),
                            'timestamp': time.time()
                        }
                    })
                
                # 更新完成计数
                completed_count = i + 1
                progress = int((completed_count / total_commands) * 100)
                
                # 更新任务状态
                self._active_tasks[task_id]['completed_count'] = completed_count
                
                # 发送进度更新
                self._progress_queue.put({
                    'task_id': task_id,
                    'progress': progress,
                    'status': f'已完成 {completed_count}/{total_commands} 个命令',
                    'timestamp': time.time()
                })
            
            # 计算执行时间
            execution_time = time.time() - self._active_tasks[task_id]['start_time']
            
            # 更新任务状态
            self._active_tasks[task_id]['status'] = 'completed'
            self._active_tasks[task_id]['end_time'] = time.time()
            self._active_tasks[task_id]['execution_time'] = execution_time
            
            # 发送完成状态
            self._progress_queue.put({
                'task_id': task_id,
                'progress': 100,
                'status': '批量执行完成',
                'timestamp': time.time()
            })
            
            # 发送结果
            result_data = {
                'task_id': task_id,
                'command_count': total_commands,
                'execution_time': f"{execution_time:.2f}秒",
                'results': results,
                'status': 'success',
                'timestamp': time.time()
            }
            
            self._result_queue.put(result_data)
            self._status_queue.put({
                'type': 'batch_completed',
                'data': result_data
            })
            
            return result_data
            
        except Exception as e:
            # 发送错误状态
            error_data = {
                'task_id': task_id,
                'error': str(e),
                'timestamp': time.time()
            }
            
            self._status_queue.put({
                'type': 'batch_failed',
                'data': error_data
            })
            
            return {
                'task_id': task_id,
                'error': str(e),
                'status': 'error'
            }
        finally:
            # 清理资源
            with self._lock:
                if task_id in self._cancel_events:
                    del self._cancel_events[task_id]
                if task_id in self._active_tasks:
                    del self._active_tasks[task_id]
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
        """
        if task_id in self._cancel_events:
            self._cancel_events[task_id].set()
            
            # 发送取消状态
            self._status_queue.put({
                'type': 'task_cancelled',
                'data': {
                    'task_id': task_id,
                    'timestamp': time.time()
                }
            })
            
            return True
        return False
    
    def get_active_tasks(self) -> Dict[str, Any]:
        """
        获取活跃任务
        """
        return self._active_tasks
    
    def get_progress(self, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取任务进度
        
        Args:
            task_id: 任务ID，None表示获取所有任务进度
        """
        progress_items = []
        while not self._progress_queue.empty():
            item = self._progress_queue.get()
            if not task_id or item['task_id'] == task_id:
                progress_items.append(item)
        return progress_items
    
    def get_status_updates(self) -> List[Dict[str, Any]]:
        """
        获取状态更新
        """
        status_items = []
        while not self._status_queue.empty():
            status_items.append(self._status_queue.get())
        return status_items
    
    def get_results(self, task_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID，None表示获取所有结果
        """
        result_items = []
        while not self._result_queue.empty():
            item = self._result_queue.get()
            if not task_id or item['task_id'] == task_id:
                result_items.append(item)
        return result_items
    
    def clear_queues(self):
        """
        清空队列
        """
        # 清空进度队列
        while not self._progress_queue.empty():
            self._progress_queue.get()
        
        # 清空状态队列
        while not self._status_queue.empty():
            self._status_queue.get()
        
        # 清空结果队列
        while not self._result_queue.empty():
            self._result_queue.get()
    
    def shutdown(self):
        """
        关闭异步反馈模块
        """
        # 停止网络监控
        self.stop_network_monitor()
        
        # 取消所有活跃任务
        for task_id in list(self._active_tasks.keys()):
            self.cancel_task(task_id)
        
        # 清空队列
        self.clear_queues()
        
        print("✅ 异步反馈模块已关闭")


def get_async_feedback(remote_host) -> AsyncFeedback:
    """
    获取异步反馈实例
    
    Args:
        remote_host: RemoteHost实例
    """
    return AsyncFeedback(remote_host)
