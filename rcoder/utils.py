#!/usr/bin/env python3
"""
Rcoder 工具模块
提供简化使用的工具函数和辅助功能，降低使用门槛
"""

import os
import json
import platform
from typing import Optional, Dict, Any

class ConfigManager:
    """配置管理类，简化配置过程"""
    
    def __init__(self, config_file: str = '~/.rcoder/config.json'):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = os.path.expanduser(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"警告: 加载配置文件失败: {e}")
        return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'servers': {
                'local': {
                    'host': '127.0.0.1',
                    'port': 443,
                    'use_https_disguise': True,
                    'proxy_server': None
                }
            },
            'default_server': 'local',
            'timeout': 60,
            'restart_max_wait': 60,
            'monitoring_interval': 30
        }
    
    def save_config(self):
        """保存配置文件"""
        try:
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"✅ 配置已保存到: {self.config_file}")
        except Exception as e:
            print(f"❌ 保存配置文件失败: {e}")
    
    def add_server(self, name: str, host: str, port: int = 443, 
                   use_https_disguise: bool = True, 
                   proxy_server: Optional[tuple] = None):
        """添加服务器配置"""
        self.config['servers'][name] = {
            'host': host,
            'port': port,
            'use_https_disguise': use_https_disguise,
            'proxy_server': proxy_server
        }
        self.save_config()
    
    def get_server(self, name: Optional[str] = None) -> Dict[str, Any]:
        """获取服务器配置"""
        server_name = name or self.config.get('default_server', 'local')
        return self.config['servers'].get(server_name, self.config['servers']['local'])


def quick_setup():
    """快速设置向导，引导用户完成初始配置"""
    print("=== Rcoder 快速设置向导 ===")
    print("帮助您快速配置 rcoder，降低使用门槛")
    print()
    
    config = ConfigManager()
    
    # 询问是否添加新服务器
    add_server = input("是否添加新服务器? (y/n): ").lower() == 'y'
    
    if add_server:
        server_name = input("服务器名称 (例如: my-server): ")
        server_host = input("服务器地址 (IP或域名): ")
        server_port = input("端口号 (默认443): ")
        server_port = int(server_port) if server_port else 443
        use_https = input("启用 HTTPS 伪装? (y/n, 默认y): ").lower() != 'n'
        
        # 询问是否使用中转服务器
        use_proxy = input("使用中转服务器? (y/n): ").lower() == 'y'
        proxy_server = None
        if use_proxy:
            proxy_host = input("中转服务器地址: ")
            proxy_port = input("中转服务器端口: ")
            proxy_server = (proxy_host, int(proxy_port))
        
        # 添加服务器配置
        config.add_server(
            name=server_name,
            host=server_host,
            port=server_port,
            use_https_disguise=use_https,
            proxy_server=proxy_server
        )
        
        # 设置为默认服务器
        config.config['default_server'] = server_name
        config.save_config()
        
        print(f"✅ 服务器 '{server_name}' 已添加并设置为默认服务器")
    
    print()
    print("=== 设置完成 ===")
    print("现在您可以使用以下命令快速开始:")
    print()
    print("1. 导入并获取远程主机:")
    print("   from rcoder.utils import get_default_remote")
    print("   remote = get_default_remote()")
    print()
    print("2. 执行命令:")
    print("   result = remote.run('ls -la')")
    print()


def get_default_remote():
    """获取默认远程主机实例，无需手动配置"""
    from rcoder.core import get_remote_host
    
    config = ConfigManager()
    server_config = config.get_server()
    
    return get_remote_host(
        host=server_config['host'],
        port=server_config['port'],
        use_https_disguise=server_config['use_https_disguise'],
        proxy_server=server_config['proxy_server']
    )


def create_alias():
    """创建命令行别名，方便快速访问"""
    shell = platform.system().lower()
    
    if shell == 'windows':
        # Windows 系统
        alias_cmd = 'doskey rcoder=python -m rcoder.cli $*'
        print("在 Windows 中创建别名:")
        print(f"请在命令提示符中执行: {alias_cmd}")
        print("或添加到注册表以永久生效")
    else:
        # Linux/macOS 系统
        shell_config = os.path.expanduser('~/.bashrc')
        if os.path.exists(os.path.expanduser('~/.zshrc')):
            shell_config = os.path.expanduser('~/.zshrc')
        
        alias_cmd = 'alias rcoder="python -m rcoder.cli"'
        print(f"在 {shell_config} 中添加以下行:")
        print(alias_cmd)
        print("然后执行: source", shell_config)
    
    print()
    print("创建别名后，您可以直接在终端中使用 'rcoder' 命令")


def validate_config():
    """验证配置文件的有效性"""
    config = ConfigManager()
    print("=== 配置验证 ===")
    print(f"配置文件: {config.config_file}")
    print(f"默认服务器: {config.config.get('default_server', 'local')}")
    print(f"服务器数量: {len(config.config.get('servers', {}))}")
    print()
    print("服务器配置:")
    for name, server in config.config.get('servers', {}).items():
        print(f"  - {name}:")
        print(f"    地址: {server.get('host')}:{server.get('port')}")
        print(f"    HTTPS伪装: {'启用' if server.get('use_https_disguise') else '禁用'}")
        if server.get('proxy_server'):
            print(f"    中转服务器: {server.get('proxy_server')[0]}:{server.get('proxy_server')[1]}")
    print()
    print("✅ 配置验证完成")


def export_config():
    """导出配置文件，方便在不同设备间共享"""
    config = ConfigManager()
    export_path = os.path.expanduser('~/.rcoder/config_export.json')
    config.save_config()
    print(f"✅ 配置已导出到: {export_path}")
    print("您可以将此文件复制到其他设备，然后使用 import_config() 导入")


def import_config(config_file: str):
    """导入配置文件"""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            imported_config = json.load(f)
        
        config = ConfigManager()
        config.config = imported_config
        config.save_config()
        print(f"✅ 配置已从 {config_file} 导入")
    except Exception as e:
        print(f"❌ 导入配置失败: {e}")
