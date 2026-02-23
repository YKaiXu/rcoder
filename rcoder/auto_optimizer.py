#!/usr/bin/env python3
"""
Rcoder 自动优化模块
减少人工干预配置，自动根据场景优化连接方式
"""

import time
import asyncio
import json
import os
from typing import Optional, Dict, Any, List, Tuple
from rcoder.core_optimized import get_remote_host
from rcoder.async_feedback import get_async_feedback

class AutoOptimizer:
    """
    自动优化器类
    自动检测网络环境，优化连接方式，减少人工干预
    """
    
    def __init__(self, config_file: str = '~/.rcoder/auto_config.json'):
        """
        初始化自动优化器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = os.path.expanduser(config_file)
        self.config = self._load_config()
        self._remote_host = None
        self._feedback = None
        self._current_scenario = None
        self._current_strategy = None
        self._network_history = []
        self._scenario_history = []
        self._lock = None
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        """
        default_config = {
            "scenarios": {
                "low_bandwidth": {
                    "description": "低带宽场景",
                    "strategies": {
                        "enable_compression": True,
                        "enable_connection_pool": True,
                        "connection_pool_size": 10,
                        "timeout": 120,
                        "retry_count": 5,
                        "retry_delay": 2,
                        "batch_size": 3,
                        "use_cache": True,
                        "cache_expiry": 120,
                        "lightweight_monitoring": True
                    }
                },
                "very_low_bandwidth": {
                    "description": "极低带宽场景",
                    "strategies": {
                        "enable_compression": True,
                        "enable_connection_pool": True,
                        "connection_pool_size": 12,
                        "timeout": 180,
                        "retry_count": 8,
                        "retry_delay": 3,
                        "batch_size": 1,
                        "use_cache": True,
                        "cache_expiry": 180,
                        "lightweight_monitoring": True,
                        "enable_minimal_payload": True
                    }
                },
                "high_latency": {
                    "description": "高延迟场景",
                    "strategies": {
                        "enable_compression": True,
                        "enable_connection_pool": True,
                        "connection_pool_size": 8,
                        "timeout": 180,
                        "retry_count": 3,
                        "retry_delay": 3,
                        "batch_size": 2,
                        "use_cache": True,
                        "cache_expiry": 180,
                        "lightweight_monitoring": True
                    }
                },
                "very_high_latency": {
                    "description": "极高延迟场景",
                    "strategies": {
                        "enable_compression": True,
                        "enable_connection_pool": True,
                        "connection_pool_size": 6,
                        "timeout": 240,
                        "retry_count": 5,
                        "retry_delay": 5,
                        "batch_size": 1,
                        "use_cache": True,
                        "cache_expiry": 240,
                        "lightweight_monitoring": True
                    }
                },
                "unstable_network": {
                    "description": "网络不稳定场景",
                    "strategies": {
                        "enable_compression": True,
                        "enable_connection_pool": True,
                        "connection_pool_size": 5,
                        "timeout": 240,
                        "retry_count": 8,
                        "retry_delay": 1,
                        "batch_size": 1,
                        "use_cache": True,
                        "cache_expiry": 60,
                        "lightweight_monitoring": True,
                        "enable_breakpoint_resume": True
                    }
                },
                "very_unstable_network": {
                    "description": "极不稳定网络场景",
                    "strategies": {
                        "enable_compression": True,
                        "enable_connection_pool": True,
                        "connection_pool_size": 3,
                        "timeout": 300,
                        "retry_count": 10,
                        "retry_delay": 2,
                        "batch_size": 1,
                        "use_cache": True,
                        "cache_expiry": 30,
                        "lightweight_monitoring": True,
                        "enable_breakpoint_resume": True,
                        "enable_exponential_backoff": True
                    }
                },
                "proxy_transfer": {
                    "description": "中转服务器场景",
                    "strategies": {
                        "enable_compression": True,
                        "enable_connection_pool": True,
                        "connection_pool_size": 10,
                        "timeout": 150,
                        "retry_count": 5,
                        "retry_delay": 2,
                        "batch_size": 4,
                        "use_cache": True,
                        "cache_expiry": 90,
                        "lightweight_monitoring": False
                    }
                },
                "local_network": {
                    "description": "本地网络场景",
                    "strategies": {
                        "enable_compression": False,
                        "enable_connection_pool": True,
                        "connection_pool_size": 5,
                        "timeout": 60,
                        "retry_count": 2,
                        "retry_delay": 1,
                        "batch_size": 10,
                        "use_cache": True,
                        "cache_expiry": 30,
                        "lightweight_monitoring": False
                    }
                }
            },
            "default_strategy": {
                "enable_compression": True,
                "enable_connection_pool": True,
                "connection_pool_size": 5,
                "timeout": 60,
                "retry_count": 3,
                "retry_delay": 1,
                "batch_size": 5,
                "use_cache": True,
                "cache_expiry": 60,
                "lightweight_monitoring": False
            },
            "network_detection": {
                "interval": 30,
                "history_size": 50,
                "scenario_thresholds": {
                    "low_bandwidth": {
                        "max_bandwidth": 0.5  # MB/s
                    },
                    "high_latency": {
                        "min_latency": 500  # ms
                    },
                    "unstable_network": {
                        "packet_loss": 0.1  # 10%
                    }
                }
            },
            "auto_detection": True,
            "auto_adjust": True,
            "learning_mode": True,
            "log_level": "info"
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 合并默认配置
                    self._merge_config(default_config, config)
                    return default_config
        except Exception as e:
            print(f"警告: 加载配置文件失败: {e}")
        
        # 保存默认配置
        self._save_config(default_config)
        return default_config
    
    def _merge_config(self, default: Dict[str, Any], user: Dict[str, Any]):
        """
        合并配置
        """
        for key, value in user.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_config(default[key], value)
            else:
                default[key] = value
    
    def _save_config(self, config: Dict[str, Any]):
        """
        保存配置文件
        """
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"警告: 保存配置文件失败: {e}")
    
    def _detect_network_scenario(self) -> str:
        """
        检测网络场景
        """
        if not self._feedback:
            return "unknown"
        
        # 获取当前网络状态
        network_status = self._feedback.get_network_status()
        
        # 检查历史网络数据
        bandwidth_trend = self._feedback.get_bandwidth_trend()
        
        # 分析网络状态
        scenario = "local_network"  # 默认场景
        
        # 检查低带宽
        if 'bandwidth' in network_status:
            try:
                bandwidth = float(network_status['bandwidth'].split()[0])
                if bandwidth < 0.5:
                    scenario = "low_bandwidth"
                elif bandwidth < 0.2:
                    scenario = "very_low_bandwidth"  # 新增：极低带宽场景
            except:
                pass
        
        # 检查高延迟
        if 'latency' in network_status:
            try:
                latency = float(network_status['latency'].split()[0])
                if latency > 500:
                    scenario = "high_latency"
                elif latency > 1000:
                    scenario = "very_high_latency"  # 新增：极高延迟场景
            except:
                pass
        
        # 检查网络不稳定
        if len(bandwidth_trend) >= 5:
            # 计算带宽波动
            bandwidths = []
            for entry in bandwidth_trend[-5:]:
                if 'bandwidth' in entry:
                    bandwidths.append(entry['bandwidth'])
            
            if len(bandwidths) >= 3:
                # 计算标准差
                mean = sum(bandwidths) / len(bandwidths)
                variance = sum((b - mean) ** 2 for b in bandwidths) / len(bandwidths)
                std_dev = variance ** 0.5
                
                # 如果带宽波动较大，认为网络不稳定
                if std_dev > mean * 0.3:
                    scenario = "unstable_network"
                elif std_dev > mean * 0.5:
                    scenario = "very_unstable_network"  # 新增：极不稳定网络场景
        
        # 检查是否使用中转服务器
        if self._remote_host and hasattr(self._remote_host, 'rcoder'):
            if self._remote_host.rcoder.proxy_server:
                scenario = "proxy_transfer"
        
        # 记录场景
        self._scenario_history.append({
            'timestamp': time.time(),
            'scenario': scenario,
            'network_status': network_status
        })
        
        # 只保留最近50条记录
        if len(self._scenario_history) > 50:
            self._scenario_history.pop(0)
        
        return scenario
    
    def _get_strategy(self, scenario: str) -> Dict[str, Any]:
        """
        获取场景对应的策略
        """
        if scenario in self.config.get('scenarios', {}):
            return self.config['scenarios'][scenario]['strategies']
        return self.config.get('default_strategy', {})
    
    def _apply_strategy(self, strategy: Dict[str, Any]):
        """
        应用策略
        """
        if not self._remote_host or not hasattr(self._remote_host, 'rcoder'):
            return
        
        rcoder = self._remote_host.rcoder
        
        # 应用策略到rcoder实例
        if hasattr(rcoder, 'enable_compression'):
            rcoder.enable_compression = strategy.get('enable_compression', True)
        if hasattr(rcoder, 'enable_connection_pool'):
            rcoder.enable_connection_pool = strategy.get('enable_connection_pool', True)
        if hasattr(rcoder, 'connection_pool_size'):
            rcoder.connection_pool_size = strategy.get('connection_pool_size', 5)
        if hasattr(rcoder, '_timeout'):
            rcoder._timeout = strategy.get('timeout', 60)
        if hasattr(rcoder, '_retry_delay'):
            rcoder._retry_delay = strategy.get('retry_delay', 1)
        if hasattr(rcoder, '_cache_expiry'):
            rcoder._cache_expiry = strategy.get('cache_expiry', 60)
        
        # 应用新策略参数
        if hasattr(rcoder, 'enable_minimal_payload'):
            rcoder.enable_minimal_payload = strategy.get('enable_minimal_payload', False)
        if hasattr(rcoder, 'enable_exponential_backoff'):
            rcoder.enable_exponential_backoff = strategy.get('enable_exponential_backoff', False)
        if hasattr(rcoder, 'enable_breakpoint_resume'):
            rcoder.enable_breakpoint_resume = strategy.get('enable_breakpoint_resume', False)
    
    async def _monitor_and_adjust(self):
        """
        监控并自动调整策略
        """
        while True:
            try:
                # 检测网络场景
                scenario = self._detect_network_scenario()
                
                # 如果场景变化，应用新策略
                if scenario != self._current_scenario:
                    self._current_scenario = scenario
                    strategy = self._get_strategy(scenario)
                    self._current_strategy = strategy
                    
                    # 应用策略
                    self._apply_strategy(strategy)
                    
                    # 记录调整
                    print(f"📊 网络场景变化: {scenario}")
                    print(f"🔧 应用新策略: {strategy}")
                    
                    # 保存配置
                    self._save_config(self.config)
            except Exception as e:
                print(f"⚠️  监控调整失败: {e}")
            
            # 等待下一次检测
            await asyncio.sleep(self.config.get('network_detection', {}).get('interval', 30))
    
    def get_remote_host(self, host: str, port: int = 443, 
                      proxy_server: Optional[Tuple[str, int]] = None, 
                      password: Optional[str] = None) -> Any:
        """
        获取远程主机实例，自动应用优化策略
        
        Args:
            host: 服务器主机
            port: 服务器端口
            proxy_server: 中转服务器
            password: 认证密码
        """
        # 检测初始场景
        temp_remote = get_remote_host(
            host=host,
            port=port,
            proxy_server=proxy_server,
            enable_compression=True,
            enable_connection_pool=True,
            password=password
        )
        
        # 获取初始网络状态
        temp_feedback = get_async_feedback(temp_remote)
        temp_feedback.start_network_monitor()
        
        # 等待网络检测
        time.sleep(3)
        
        # 检测场景
        scenario = self._detect_network_scenario()
        strategy = self._get_strategy(scenario)
        
        # 停止临时监控
        temp_feedback.stop_network_monitor()
        temp_feedback.shutdown()
        
        # 使用检测到的策略创建最终的远程主机
        self._remote_host = get_remote_host(
            host=host,
            port=port,
            proxy_server=proxy_server,
            enable_compression=strategy.get('enable_compression', True),
            enable_connection_pool=strategy.get('enable_connection_pool', True),
            password=password
        )
        
        # 获取反馈实例
        self._feedback = get_async_feedback(self._remote_host)
        
        # 应用完整策略
        self._current_scenario = scenario
        self._current_strategy = strategy
        self._apply_strategy(strategy)
        
        # 启动网络监控
        self._feedback.start_network_monitor()
        
        # 启动自动调整
        import threading
        self._lock = threading.Lock()
        
        def monitor_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._monitor_and_adjust())
        
        monitor = threading.Thread(target=monitor_thread, daemon=True)
        monitor.start()
        
        print(f"✅ 自动优化器初始化完成")
        print(f"📊 检测到场景: {scenario}")
        print(f"🔧 应用策略: {strategy}")
        
        return self._remote_host
    
    def get_feedback(self):
        """
        获取异步反馈实例
        """
        return self._feedback
    
    def get_current_scenario(self) -> Optional[str]:
        """
        获取当前场景
        """
        return self._current_scenario
    
    def get_current_strategy(self) -> Optional[Dict[str, Any]]:
        """
        获取当前策略
        """
        return self._current_strategy
    
    def get_network_history(self) -> List[Dict[str, Any]]:
        """
        获取网络历史
        """
        return self._network_history
    
    def get_scenario_history(self) -> List[Dict[str, Any]]:
        """
        获取场景历史
        """
        return self._scenario_history
    
    def add_custom_scenario(self, name: str, description: str, strategies: Dict[str, Any]):
        """
        添加自定义场景
        
        Args:
            name: 场景名称
            description: 场景描述
            strategies: 场景策略
        """
        self.config['scenarios'][name] = {
            'description': description,
            'strategies': strategies
        }
        self._save_config(self.config)
        print(f"✅ 自定义场景 '{name}' 添加成功")
    
    def update_scenario(self, name: str, strategies: Dict[str, Any]):
        """
        更新场景策略
        
        Args:
            name: 场景名称
            strategies: 新的策略
        """
        if name in self.config.get('scenarios', {}):
            self.config['scenarios'][name]['strategies'].update(strategies)
            self._save_config(self.config)
            print(f"✅ 场景 '{name}' 策略更新成功")
        else:
            print(f"❌ 场景 '{name}' 不存在")
    
    def export_config(self, output_file: str):
        """
        导出配置
        
        Args:
            output_file: 输出文件路径
        """
        self._save_config(self.config)
        import shutil
        shutil.copy2(self.config_file, output_file)
        print(f"✅ 配置已导出到: {output_file}")
    
    def import_config(self, input_file: str):
        """
        导入配置
        
        Args:
            input_file: 输入文件路径
        """
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                imported_config = json.load(f)
            
            self.config.update(imported_config)
            self._save_config(self.config)
            print(f"✅ 配置已从: {input_file} 导入")
        except Exception as e:
            print(f"❌ 导入配置失败: {e}")
    
    def optimize_command(self, command: str) -> str:
        """
        优化命令，根据当前网络场景调整命令
        
        Args:
            command: 原始命令
            
        Returns:
            优化后的命令
        """
        if not command or not isinstance(command, str):
            return command
        
        # 获取当前策略
        strategy = self._current_strategy or self.config.get('default_strategy', {})
        
        # 基础优化
        optimized_command = command.strip()
        
        # 根据场景进行优化
        if self._current_scenario == "low_bandwidth":
            # 低带宽优化
            if "ls" in optimized_command and "-la" in optimized_command:
                optimized_command = optimized_command.replace("-la", "-l")  # 减少输出
            if "ping" in optimized_command and "-c" not in optimized_command:
                optimized_command += " -c 3"  # 限制ping次数
            if "find" in optimized_command and "-type f" not in optimized_command:
                optimized_command += " -type f"  # 只查找文件
                
        elif self._current_scenario == "very_low_bandwidth":
            # 极低带宽优化
            if "ls" in optimized_command:
                optimized_command = optimized_command.replace("-la", "")  # 移除详细列表
                optimized_command = optimized_command.replace("-l", "")  # 移除列表
            if "ping" in optimized_command:
                optimized_command = optimized_command.replace("-c 3", "-c 1")  # 最少ping次数
            if "df" in optimized_command and "-h" in optimized_command:
                optimized_command = optimized_command.replace("-h", "")  # 移除人性化输出
                
        elif self._current_scenario == "high_latency":
            # 高延迟优化
            if "apt" in optimized_command or "yum" in optimized_command:
                optimized_command += " -y"  # 自动确认
            if "scp" in optimized_command and "-C" not in optimized_command:
                optimized_command += " -C"  # 启用压缩
                
        elif self._current_scenario == "unstable_network":
            # 网络不稳定优化
            if "wget" in optimized_command and "-c" not in optimized_command:
                optimized_command += " -c"  # 断点续传
            if "curl" in optimized_command and "--retry" not in optimized_command:
                optimized_command += " --retry 3"  # 重试机制
                
        elif self._current_scenario == "proxy_transfer":
            # 中转服务器优化
            if "rsync" in optimized_command and "-z" not in optimized_command:
                optimized_command += " -z"  # 启用压缩
            if "ssh" in optimized_command and "-C" not in optimized_command:
                optimized_command += " -C"  # 启用压缩
                
        # 通用优化
        if strategy.get('enable_compression', True):
            # 添加压缩相关的优化
            if "tar" in optimized_command and "-z" not in optimized_command:
                optimized_command += " -z"  # tar命令启用压缩
                
        # 限制输出大小
        max_output_lines = strategy.get('max_output_lines', 1000)
        if max_output_lines and not ("| head" in optimized_command or "| tail" in optimized_command):
            if "find" in optimized_command or "grep" in optimized_command:
                optimized_command += f" | head -{max_output_lines}"
                
        print(f"🔄 命令优化: {self._current_scenario or 'default'} -> {optimized_command}")
        return optimized_command

def shutdown(self):
        """
        关闭自动优化器
        """
        if self._feedback:
            self._feedback.stop_network_monitor()
            self._feedback.shutdown()
        print("✅ 自动优化器已关闭")


def get_auto_optimizer(config_file: str = '~/.rcoder/auto_config.json') -> AutoOptimizer:
    """
    获取自动优化器实例
    
    Args:
        config_file: 配置文件路径
    """
    return AutoOptimizer(config_file)


# 示例代码
if __name__ == "__main__":
    print("=== Rcoder 自动优化器示例 ===")
    
    # 创建自动优化器
    optimizer = get_auto_optimizer()
    
    # 获取远程主机实例（自动优化）
    print("1. 获取远程主机实例（自动优化）")
    remote = optimizer.get_remote_host(
        host='192.168.1.8',
        port=443
        # proxy_server=('1.2.3.4', 443)  # 可选：中转服务器
    )
    print()
    
    # 获取反馈实例
    feedback = optimizer.get_feedback()
    
    # 等待策略应用
    print("2. 等待策略应用...")
    time.sleep(2)
    
    # 查看当前场景和策略
    print("3. 当前场景和策略")
    print(f"   当前场景: {optimizer.get_current_scenario()}")
    print(f"   当前策略: {optimizer.get_current_strategy()}")
    print()
    
    # 示例：执行命令
    print("4. 执行测试命令")
    try:
        result = remote.run("echo '测试命令执行' && sleep 2 && echo '命令执行完成'")
        print(f"   命令执行结果: {result}")
    except Exception as e:
        print(f"   命令执行失败: {e}")
    print()
    
    # 查看网络状态
    print("5. 查看当前网络状态")
    network_status = feedback.get_network_status()
    print(f"   状态: {network_status['status']}")
    print(f"   延迟: {network_status['latency']}")
    print(f"   带宽: {network_status['bandwidth']}")
    print()
    
    # 查看场景历史
    print("6. 查看场景历史")
    scenario_history = optimizer.get_scenario_history()
    if scenario_history:
        print(f"   最近场景: {[h['scenario'] for h in scenario_history[-5:]]}")
    else:
        print("   暂无场景历史")
    print()
    
    # 导出配置
    print("7. 导出配置")
    export_file = 'auto_config_export.json'
    optimizer.export_config(export_file)
    print()
    
    # 关闭自动优化器
    print("8. 关闭自动优化器")
    optimizer.shutdown()
    print()
    
    print("=== 示例完成 ===")
    print("✅ 自动优化器功能演示完成")
    print()
    print("关键特性:")
    print("1. 自动场景检测: 低带宽、高延迟、网络不稳定、中转服务器")
    print("2. 智能策略应用: 根据场景自动调整参数")
    print("3. 实时监控调整: 动态适应网络变化")
    print("4. 配置管理: 导入导出配置，支持自定义场景")
    print("5. 历史记录: 场景和网络状态历史")
    print()
    print("使用方法:")
    print("1. 创建自动优化器: optimizer = get_auto_optimizer()")
    print("2. 获取远程主机: remote = optimizer.get_remote_host(host='服务器地址')")
    print("3. 开始使用: result = remote.run('命令')")
    print("4. 自动优化器会在后台自动调整策略")
