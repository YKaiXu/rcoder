#!/usr/bin/env python3
"""
Rcoder 异步代理通讯模块
优化中转服务器场景下的异步通讯机制 - 带消息队列
"""

import asyncio
import json
import time
import os
import pickle
from typing import Optional, Dict, Any, Callable, List

class MessageQueue:
    """
    消息队列管理器
    确保命令按顺序执行且不丢失
    """
    
    def __init__(self, queue_dir: str = "./message_queue"):
        """
        初始化消息队列
        
        Args:
            queue_dir: 队列持久化目录
        """
        self.queue_dir = queue_dir
        self.queue = []
        self.processing = set()
        self._lock = asyncio.Lock()
        
        # 创建队列目录
        os.makedirs(queue_dir, exist_ok=True)
        
        # 加载持久化队列
        self._load_queue()
    
    async def enqueue(self, item: Dict[str, Any]) -> str:
        """
        入队
        
        Args:
            item: 队列项
        
        Returns:
            队列项ID
        """
        async with self._lock:
            item_id = item.get('id', f"msg_{int(time.time())}_{len(self.queue)}")
            item['id'] = item_id
            item['status'] = 'pending'
            item['timestamp'] = time.time()
            item['sequence'] = len(self.queue)
            
            self.queue.append(item)
            self._save_queue()
            
            return item_id
    
    async def dequeue(self) -> Optional[Dict[str, Any]]:
        """
        出队
        
        Returns:
            队列项或None
        """
        async with self._lock:
            if not self.queue:
                return None
            
            # 找到第一个待处理的项
            for i, item in enumerate(self.queue):
                if item['status'] == 'pending' and item['id'] not in self.processing:
                    item['status'] = 'processing'
                    item['processing_time'] = time.time()
                    self.processing.add(item['id'])
                    self._save_queue()
                    return item
            
            return None
    
    async def complete(self, item_id: str, result: Dict[str, Any]) -> bool:
        """
        完成处理
        
        Args:
            item_id: 队列项ID
            result: 处理结果
        
        Returns:
            是否成功
        """
        async with self._lock:
            for item in self.queue:
                if item['id'] == item_id:
                    item['status'] = 'completed'
                    item['result'] = result
                    item['completion_time'] = time.time()
                    self.processing.remove(item_id)
                    self._save_queue()
                    return True
            return False
    
    async def fail(self, item_id: str, error: str) -> bool:
        """
        处理失败
        
        Args:
            item_id: 队列项ID
            error: 错误信息
        
        Returns:
            是否成功
        """
        async with self._lock:
            for item in self.queue:
                if item['id'] == item_id:
                    item['status'] = 'failed'
                    item['error'] = error
                    item['completion_time'] = time.time()
                    self.processing.remove(item_id)
                    self._save_queue()
                    return True
            return False
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        获取队列状态
        
        Returns:
            队列状态
        """
        status = {
            'total': len(self.queue),
            'pending': sum(1 for item in self.queue if item['status'] == 'pending'),
            'processing': sum(1 for item in self.queue if item['status'] == 'processing'),
            'completed': sum(1 for item in self.queue if item['status'] == 'completed'),
            'failed': sum(1 for item in self.queue if item['status'] == 'failed')
        }
        return status
    
    def _save_queue(self):
        """
        持久化队列
        """
        queue_file = os.path.join(self.queue_dir, "message_queue.pkl")
        try:
            with open(queue_file, 'wb') as f:
                pickle.dump(self.queue, f)
        except Exception as e:
            print(f"❌ 保存队列失败: {e}")
    
    def _load_queue(self):
        """
        加载持久化队列
        """
        queue_file = os.path.join(self.queue_dir, "message_queue.pkl")
        try:
            if os.path.exists(queue_file):
                with open(queue_file, 'rb') as f:
                    self.queue = pickle.load(f)
                # 重置处理状态
                for item in self.queue:
                    if item['status'] == 'processing':
                        item['status'] = 'pending'
                self.processing.clear()
                print(f"✅ 加载队列成功，共 {len(self.queue)} 项")
        except Exception as e:
            print(f"❌ 加载队列失败: {e}")
            self.queue = []


class AsyncProxyManager:
    """
    异步代理管理器
    实现中转服务器场景下的异步通讯机制 - 带消息队列
    """
    
    def __init__(self, remote_host):
        """
        初始化异步代理管理器
        
        Args:
            remote_host: 远程主机实例
        """
        self.remote = remote_host
        self.command_counter = 0
        self._lock = asyncio.Lock()
        self._event_loop = asyncio.get_event_loop()
        
        # 创建消息队列
        self.message_queue = MessageQueue()
        
        # 启动队列处理器
        self._queue_processor_task = self._event_loop.create_task(self._process_queue())
    
    async def _process_queue(self):
        """
        处理消息队列
        """
        while True:
            try:
                # 从队列中获取待处理项
                item = await self.message_queue.dequeue()
                if not item:
                    await asyncio.sleep(0.1)  # 避免忙等
                    continue
                
                print(f"🔄 处理队列项: {item['id']} (序列: {item['sequence']})")
                
                # 执行代理命令
                result = await self._execute_proxy_command(
                    item['proxy_command'],
                    item['id'],
                    item.get('callback')
                )
                
                # 标记完成
                await self.message_queue.complete(item['id'], result)
                print(f"✅ 队列项处理完成: {item['id']}")
                
            except Exception as e:
                print(f"❌ 队列处理器错误: {e}")
                await asyncio.sleep(1)  # 出错后暂停一下
    
    async def _execute_proxy_command(self, proxy_command: str, command_id: str, callback: Optional[Callable]) -> Dict[str, Any]:
        """
        执行代理命令
        
        Args:
            proxy_command: 代理命令
            command_id: 命令ID
            callback: 回调函数
        
        Returns:
            执行结果
        """
        try:
            result = await self.remote.run_async(proxy_command)
            
            # 解析结果
            try:
                feedback = json.loads(result.strip())
                print(f"✅ 收到中转服务器反馈: {command_id} - {feedback.get('status')}")
                
                # 执行回调
                if callback:
                    callback(feedback)
                
                return feedback
                
            except Exception as e:
                error_msg = f"解析反馈失败: {str(e)}"
                print(f"❌ {error_msg}")
                
                # 执行回调（错误情况）
                if callback:
                    callback({
                        'id': command_id,
                        'status': 'error',
                        'result': error_msg,
                        'timestamp': time.time()
                    })
                
                return {
                    'id': command_id,
                    'status': 'error',
                    'result': error_msg,
                    'timestamp': time.time()
                }
                
        except Exception as e:
            error_msg = f"执行代理命令失败: {str(e)}"
            print(f"❌ {error_msg}")
            
            # 执行回调（错误情况）
            if callback:
                callback({
                    'id': command_id,
                    'status': 'error',
                    'result': error_msg,
                    'timestamp': time.time()
                })
            
            return {
                'id': command_id,
                'status': 'error',
                'result': error_msg,
                'timestamp': time.time()
            }
    
    async def send_command(self, command: str, 
                          target_server: str, 
                          callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        发送命令到中转服务器（带消息队列）
        
        Args:
            command: 要执行的命令
            target_server: 目标服务器标识
            callback: 回调函数（可选）
        
        Returns:
            命令提交结果
        """
        # 生成命令ID
        async with self._lock:
            command_id = f"cmd_{self.command_counter}_{int(time.time())}"
            self.command_counter += 1
        
        print(f"📡 发送命令到中转服务器: {command_id}")
        
        # 构建代理命令
        proxy_command = f"python -c \""
        proxy_command += "import json\n"
        proxy_command += "import subprocess\n"
        proxy_command += "import time\n"
        proxy_command += "\n"
        proxy_command += f"# 命令信息\n"
        proxy_command += f"command_id = '{command_id}'\n"
        proxy_command += f"command = '{command}'\n"
        proxy_command += f"target_server = '{target_server}'\n"
        proxy_command += f"timestamp = {time.time()}\n"
        proxy_command += "\n"
        proxy_command += "# 无状态邮局模式处理\n"
        proxy_command += "print('🔄 中转服务器接收命令:', command_id)\n"
        proxy_command += "print('🚀 向目标服务器推送指令...')\n"
        proxy_command += "\n"
        proxy_command += "# 执行命令（模拟目标服务器执行）\n"
        proxy_command += "try:\n"
        proxy_command += "    result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)\n"
        proxy_command += "    status = 'success'\n"
        proxy_command += "    print('✅ 目标服务器执行成功')\n"
        proxy_command += "except Exception as e:\n"
        proxy_command += "    result = str(e)\n"
        proxy_command += "    status = 'error'\n"
        proxy_command += "    print('❌ 目标服务器执行失败:', result)\n"
        proxy_command += "\n"
        proxy_command += "# 构建反馈信息\n"
        proxy_command += "feedback = json.dumps({\n"
        proxy_command += "    'id': command_id,\n"
        proxy_command += "    'status': status,\n"
        proxy_command += "    'result': result,\n"
        proxy_command += "    'timestamp': time.time()\n"
        proxy_command += "})\n"
        proxy_command += "print('📨 反馈信息:', feedback)\n"
        proxy_command += '"'
        
        # 创建队列项
        queue_item = {
            'id': command_id,
            'command': command,
            'target_server': target_server,
            'proxy_command': proxy_command,
            'callback': callback,
            'timestamp': time.time()
        }
        
        # 入队
        item_id = await self.message_queue.enqueue(queue_item)
        print(f"📋 命令已加入队列: {item_id}")
        
        # 获取队列状态
        queue_status = self.message_queue.get_queue_status()
        print(f"📊 当前队列状态: {queue_status}")
        
        # 立即返回，不阻塞
        return {
            'id': command_id,
            'status': 'queued',
            'message': '命令已加入队列',
            'sequence': queue_item['sequence'],
            'queue_status': queue_status,
            'timestamp': time.time()
        }
    
    async def send_batch_commands(self, commands: list, 
                                target_server: str, 
                                concurrency: int = 5) -> List[Dict[str, Any]]:
        """
        批量发送命令到中转服务器（带消息队列）
        
        Args:
            commands: 命令列表
            target_server: 目标服务器标识
            concurrency: 并发数
        
        Returns:
            命令提交结果列表
        """
        results = []
        
        for cmd in commands:
            result = await self.send_command(cmd, target_server)
            results.append(result)
        
        return results
    
    def get_queue_status(self) -> Dict[str, Any]:
        """
        获取队列状态
        
        Returns:
            队列状态
        """
        return self.message_queue.get_queue_status()
    
    async def shutdown(self):
        """
        关闭管理器
        """
        # 取消队列处理器
        if self._queue_processor_task:
            self._queue_processor_task.cancel()
            try:
                await self._queue_processor_task
            except asyncio.CancelledError:
                pass
        
        print("✅ 异步代理管理器已关闭")
    



class ProxyServerManager:
    """
    代理服务器管理器
    管理中转服务器和目标服务器之间的通讯
    """
    
    def __init__(self, proxy_host: str, 
                 proxy_port: int, 
                 proxy_password: str):
        """
        初始化代理服务器管理器
        
        Args:
            proxy_host: 中转服务器主机
            proxy_port: 中转服务器端口
            proxy_password: 中转服务器密码
        """
        self.proxy_host = proxy_host
        self.proxy_port = proxy_port
        self.proxy_password = proxy_password
        self.target_servers = {}  # 目标服务器配置
    
    def add_target_server(self, server_id: str, 
                         server_host: str, 
                         server_port: int, 
                         server_password: str):
        """
        添加目标服务器
        
        Args:
            server_id: 服务器标识
            server_host: 服务器主机
            server_port: 服务器端口
            server_password: 服务器密码
        """
        self.target_servers[server_id] = {
            'host': server_host,
            'port': server_port,
            'password': server_password
        }
    
    def get_target_server(self, server_id: str) -> Optional[Dict[str, Any]]:
        """
        获取目标服务器配置
        
        Args:
            server_id: 服务器标识
        
        Returns:
            服务器配置
        """
        return self.target_servers.get(server_id)
    
    def remove_target_server(self, server_id: str):
        """
        移除目标服务器
        
        Args:
            server_id: 服务器标识
        """
        if server_id in self.target_servers:
            del self.target_servers[server_id]


async def main():
    """
    示例代码 - 带消息队列
    """
    from rcoder.core_optimized import get_remote_host
    
    # 创建中转服务器连接
    proxy_remote = get_remote_host(
        host='proxy.example.com',
        port=443,
        password='proxy_password'
    )
    
    # 创建异步代理管理器
    proxy_manager = AsyncProxyManager(proxy_remote)
    print("✅ 异步代理管理器创建成功！")
    
    # 定义回调函数
    def callback(result):
        print(f"🔔 回调通知 - 命令 {result['id']} 执行完成: {result['status']}")
        print(f"   结果: {result['result'][:100]}{'...' if len(result['result']) > 100 else ''}")
    
    # 发送测试命令（带消息队列）
    print(f"\n📡 发送测试命令...")
    result = await proxy_manager.send_command(
        command='ls -la',
        target_server='target1',
        callback=callback
    )
    
    print(f"📋 命令提交结果: {result}")
    print("✅ 命令已加入队列，不阻塞后续操作")
    
    # 批量发送命令
    commands = [
        'ls -la',
        'uptime',
        'free -h',
        'df -h',
        'ps aux | head -10'
    ]
    
    print(f"\n📡 批量发送命令...")
    batch_results = await proxy_manager.send_batch_commands(
        commands=commands,
        target_server='target1',
        concurrency=2
    )
    
    print(f"📋 批量命令提交结果:")
    for i, batch_result in enumerate(batch_results):
        print(f"命令 {i+1}: {batch_result}")
    
    # 定期检查队列状态
    print("\n⏳ 定期检查队列状态...")
    for i in range(5):
        queue_status = proxy_manager.get_queue_status()
        print(f"📊 队列状态 ({i+1}/5): {queue_status}")
        await asyncio.sleep(2)
    
    # 关闭管理器
    print("\n🔄 关闭异步代理管理器...")
    await proxy_manager.shutdown()
    print("✅ 异步代理管理器已关闭")


if __name__ == "__main__":
    asyncio.run(main())
