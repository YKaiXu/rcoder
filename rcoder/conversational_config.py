#!/usr/bin/env python3
"""
Rcoder 对话式配置模块
允许用户通过对话方式配置Rcoder，包括MCP服务器和技能配置
"""

import json
import os
import time
from typing import Dict, Any, Optional

class ConversationalConfig:
    """
    对话式配置类
    提供交互式配置界面，支持MCP服务器和技能配置
    """
    
    def __init__(self, config_file: str = '~/.rcoder/config.json'):
        """
        初始化对话式配置
        
        Args:
            config_file: 配置文件路径
        """
        self.config_file = os.path.expanduser(config_file)
        self.config = self._load_config()
        self._conversations = []
    
    def _load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        """
        default_config = {
            "mcp": {
                "enabled": False,
                "server": "",
                "port": 443,
                "api_key": "",
                "timeout": 30
            },
            "skills": {
                "enabled": False,
                "directory": "~/.rcoder/skills",
                "auto_load": True
            },
            "network": {
                "auto_optimize": True,
                "use_proxy": False,
                "proxy_server": "",
                "proxy_port": 443,
                "password": ""
            },
            "optimization": {
                "enable_compression": True,
                "enable_connection_pool": True,
                "connection_pool_size": 5
            }
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
    
    def _ask_question(self, question: str, default: Optional[str] = None) -> str:
        """
        询问问题并获取回答
        
        Args:
            question: 问题
            default: 默认回答
        """
        prompt = f"{question}"
        if default is not None:
            prompt += f" (默认: {default})"
        prompt += ": "
        
        answer = input(prompt)
        if not answer and default is not None:
            return default
        return answer
    
    def _ask_yes_no(self, question: str, default: bool = True) -> bool:
        """
        询问是/否问题
        
        Args:
            question: 问题
            default: 默认回答
        """
        prompt = f"{question} ({'Y/n' if default else 'y/N'}): "
        answer = input(prompt).lower().strip()
        
        if not answer:
            return default
        return answer in ['y', 'yes']
    
    def start_configuration(self):
        """
        开始对话式配置
        """
        print("=== Rcoder 对话式配置 ===")
        print("欢迎使用Rcoder对话式配置助手。")
        print("我会引导您完成MCP服务器和技能配置。")
        print()
        
        # 配置MCP服务器
        self._configure_mcp()
        print()
        
        # 配置技能
        self._configure_skills()
        print()
        
        # 配置网络设置
        self._configure_network()
        print()
        
        # 配置优化设置
        self._configure_optimization()
        print()
        
        # 保存配置
        self._save_config(self.config)
        print("✅ 配置已保存到:", self.config_file)
        print()
        
        # 显示配置摘要
        self._show_config_summary()
        print()
        print("=== 配置完成 ===")
        print("您现在可以使用配置好的Rcoder了。")
    
    def _configure_mcp(self):
        """
        配置MCP服务器
        """
        print("1. MCP服务器配置")
        print("MCP服务器提供额外的功能和集成能力。")
        
        enable_mcp = self._ask_yes_no("是否启用MCP服务器", self.config['mcp']['enabled'])
        self.config['mcp']['enabled'] = enable_mcp
        
        if enable_mcp:
            server = self._ask_question("MCP服务器地址", self.config['mcp']['server'])
            self.config['mcp']['server'] = server
            
            port = self._ask_question("MCP服务器端口", str(self.config['mcp']['port']))
            try:
                self.config['mcp']['port'] = int(port)
            except:
                self.config['mcp']['port'] = 443
            
            api_key = self._ask_question("MCP API密钥", self.config['mcp']['api_key'])
            self.config['mcp']['api_key'] = api_key
            
            timeout = self._ask_question("MCP超时时间（秒）", str(self.config['mcp']['timeout']))
            try:
                self.config['mcp']['timeout'] = int(timeout)
            except:
                self.config['mcp']['timeout'] = 30
        
        print("✅ MCP服务器配置完成")
    
    def _configure_skills(self):
        """
        配置技能
        """
        print("2. 技能配置")
        print("技能扩展了Rcoder的功能。")
        
        enable_skills = self._ask_yes_no("是否启用技能系统", self.config['skills']['enabled'])
        self.config['skills']['enabled'] = enable_skills
        
        if enable_skills:
            directory = self._ask_question("技能目录", self.config['skills']['directory'])
            self.config['skills']['directory'] = directory
            
            auto_load = self._ask_yes_no("是否自动加载技能", self.config['skills']['auto_load'])
            self.config['skills']['auto_load'] = auto_load
        
        print("✅ 技能配置完成")
    
    def _configure_network(self):
        """
        配置网络设置
        """
        print("3. 网络设置")
        print("网络设置影响Rcoder的连接和性能。")
        
        auto_optimize = self._ask_yes_no("是否启用自动网络优化", self.config['network']['auto_optimize'])
        self.config['network']['auto_optimize'] = auto_optimize
        
        use_proxy = self._ask_yes_no("是否使用代理服务器", self.config['network']['use_proxy'])
        self.config['network']['use_proxy'] = use_proxy
        
        if use_proxy:
            proxy_server = self._ask_question("代理服务器地址", self.config['network']['proxy_server'])
            self.config['network']['proxy_server'] = proxy_server
            
            proxy_port = self._ask_question("代理服务器端口", str(self.config['network']['proxy_port']))
            try:
                self.config['network']['proxy_port'] = int(proxy_port)
            except:
                self.config['network']['proxy_port'] = 443
        
        # 配置认证密码
        use_password = self._ask_yes_no("是否使用认证密码", bool(self.config['network']['password']))
        if use_password:
            password = self._ask_question("认证密码", self.config['network']['password'])
            self.config['network']['password'] = password
        else:
            self.config['network']['password'] = ""
        
        print("✅ 网络设置配置完成")
    
    def _configure_optimization(self):
        """
        配置优化设置
        """
        print("4. 优化设置")
        print("优化设置可以提高Rcoder的性能和可靠性。")
        
        enable_compression = self._ask_yes_no("是否启用数据压缩", self.config['optimization']['enable_compression'])
        self.config['optimization']['enable_compression'] = enable_compression
        
        enable_connection_pool = self._ask_yes_no("是否启用连接池", self.config['optimization']['enable_connection_pool'])
        self.config['optimization']['enable_connection_pool'] = enable_connection_pool
        
        if enable_connection_pool:
            pool_size = self._ask_question("连接池大小", str(self.config['optimization']['connection_pool_size']))
            try:
                self.config['optimization']['connection_pool_size'] = int(pool_size)
            except:
                self.config['optimization']['connection_pool_size'] = 5
        
        print("✅ 优化设置配置完成")
    
    def _show_config_summary(self):
        """
        显示配置摘要
        """
        print("=== 配置摘要 ===")
        
        print("MCP服务器:")
        print(f"  启用: {'是' if self.config['mcp']['enabled'] else '否'}")
        if self.config['mcp']['enabled']:
            print(f"  服务器: {self.config['mcp']['server']}:{self.config['mcp']['port']}")
            print(f"  API密钥: {'***' if self.config['mcp']['api_key'] else '未设置'}")
        
        print("\n技能系统:")
        print(f"  启用: {'是' if self.config['skills']['enabled'] else '否'}")
        if self.config['skills']['enabled']:
            print(f"  目录: {self.config['skills']['directory']}")
            print(f"  自动加载: {'是' if self.config['skills']['auto_load'] else '否'}")
        
        print("\n网络设置:")
        print(f"  自动优化: {'是' if self.config['network']['auto_optimize'] else '否'}")
        print(f"  使用代理: {'是' if self.config['network']['use_proxy'] else '否'}")
        if self.config['network']['use_proxy']:
            print(f"  代理服务器: {self.config['network']['proxy_server']}:{self.config['network']['proxy_port']}")
        print(f"  使用密码认证: {'是' if self.config['network']['password'] else '否'}")
        
        print("\n优化设置:")
        print(f"  数据压缩: {'是' if self.config['optimization']['enable_compression'] else '否'}")
        print(f"  连接池: {'是' if self.config['optimization']['enable_connection_pool'] else '否'}")
        if self.config['optimization']['enable_connection_pool']:
            print(f"  连接池大小: {self.config['optimization']['connection_pool_size']}")
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            当前配置字典
        """
        return self.config
    
    def update_config(self, updates: Dict[str, Any]):
        """
        更新配置
        
        Args:
            updates: 要更新的配置项
        """
        self._merge_config(self.config, updates)
        self._save_config(self.config)
    
    def load_from_conversation(self, conversation: str):
        """
        从对话历史加载配置
        
        Args:
            conversation: 对话历史
        """
        # 这里可以实现从对话历史解析配置的逻辑
        # 例如，从用户的自然语言描述中提取配置信息
        pass


def start_conversational_config(config_file: str = '~/.rcoder/config.json'):
    """
    启动对话式配置
    
    Args:
        config_file: 配置文件路径
    """
    config = ConversationalConfig(config_file)
    config.start_configuration()
    return config


# 示例代码
if __name__ == "__main__":
    start_conversational_config()
