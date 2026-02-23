#!/usr/bin/env python3
"""
Rcoder 服务器安装工具
用于自动安装和配置中转服务器和目标服务器
"""

import os
import time
from typing import Optional, Dict, Any

class ServerInstaller:
    """
    服务器安装器类
    处理远程服务器的自动安装和配置
    """
    
    def __init__(self, remote_host):
        """
        初始化服务器安装器
        
        Args:
            remote_host: 远程主机实例
        """
        self.remote = remote_host
        self.installation_steps = []
        self.verbose = True
    
    def install_rcoder_server(self, server_type: str = 'target', 
                             use_venv: bool = True, 
                             venv_path: str = '~/.rcoder/venv') -> Dict[str, Any]:
        """
        在远程服务器上安装Rcoder服务器端
        
        Args:
            server_type: 服务器类型 ('target' 或 'proxy')
            use_venv: 是否使用虚拟环境
            venv_path: 虚拟环境路径
        
        Returns:
            安装结果
        """
        print(f"=== 安装 {server_type} 服务器 ===")
        
        results = {
            'success': False,
            'steps': [],
            'errors': [],
            'status': 'pending'
        }
        
        try:
            # 步骤1: 系统更新
            self._log(f"1. 更新系统包")
            if self._update_system():
                results['steps'].append('系统更新成功')
            else:
                results['errors'].append('系统更新失败')
            
            # 步骤2: 安装必要依赖
            self._log(f"2. 安装必要依赖")
            if self._install_dependencies():
                results['steps'].append('依赖安装成功')
            else:
                results['errors'].append('依赖安装失败')
            
            # 步骤3: 安装Python
            self._log(f"3. 安装Python")
            if self._install_python():
                results['steps'].append('Python安装成功')
            else:
                results['errors'].append('Python安装失败')
            
            # 步骤4: 安装和配置虚拟环境
            if use_venv:
                self._log(f"4. 安装和配置虚拟环境")
                if self._setup_venv(venv_path):
                    results['steps'].append('虚拟环境配置成功')
                else:
                    results['errors'].append('虚拟环境配置失败')
            else:
                results['steps'].append('跳过虚拟环境配置')
            
            # 步骤5: 安装Rcoder服务器端
            self._log(f"5. 安装Rcoder服务器端")
            if self._install_rcoder_server(use_venv, venv_path):
                results['steps'].append('Rcoder服务器安装成功')
            else:
                results['errors'].append('Rcoder服务器安装失败')
            
            # 步骤6: 配置服务器
            self._log(f"6. 配置服务器")
            config_result = self._configure_server(server_type, use_venv, venv_path)
            if config_result:
                results['steps'].append('服务器配置成功')
                results['config'] = config_result
            else:
                results['errors'].append('服务器配置失败')
            
            # 步骤7: 启动服务
            self._log(f"7. 启动服务")
            if self._start_services(use_venv, venv_path):
                results['steps'].append('服务启动成功')
            else:
                results['errors'].append('服务启动失败')
            
            # 步骤8: 验证安装
            self._log(f"8. 验证安装")
            if self._verify_installation():
                results['steps'].append('安装验证成功')
                results['success'] = True
                results['status'] = 'completed'
            else:
                results['errors'].append('安装验证失败')
                results['status'] = 'failed'
            
        except Exception as e:
            error_msg = f"安装过程出错: {str(e)}"
            self._log(error_msg)
            results['errors'].append(error_msg)
            results['status'] = 'failed'
        
        print()
        if results['success']:
            print(f"✅ {server_type} 服务器安装成功！")
        else:
            print(f"❌ {server_type} 服务器安装失败！")
            print(f"错误: {results['errors']}")
        
        return results
    
    def _log(self, message: str):
        """
        记录日志
        
        Args:
            message: 日志消息
        """
        if self.verbose:
            print(f"   {message}")
    
    def _update_system(self) -> bool:
        """
        更新系统包
        """
        try:
            # 检测系统类型
            os_info = self.remote.run('cat /etc/os-release | grep -E "^ID=" | cut -d= -f2 | tr -d \"\'"')
            os_info = os_info.strip().lower()
            
            if 'ubuntu' in os_info or 'debian' in os_info:
                # Ubuntu/Debian
                self.remote.run('sudo apt update -y')
                self.remote.run('sudo apt upgrade -y')
            elif 'centos' in os_info or 'rhel' in os_info or 'rocky' in os_info:
                # CentOS/RHEL/Rocky
                self.remote.run('sudo yum update -y')
            elif 'alpine' in os_info:
                # Alpine
                self.remote.run('sudo apk update')
                self.remote.run('sudo apk upgrade')
            else:
                # 尝试通用方法
                self._log("未知系统类型，跳过系统更新")
            
            return True
        except Exception as e:
            self._log(f"系统更新出错: {e}")
            return False
    
    def _install_dependencies(self) -> bool:
        """
        安装必要依赖
        """
        try:
            # 检测系统类型
            os_info = self.remote.run('cat /etc/os-release | grep -E "^ID=" | cut -d= -f2 | tr -d \"\'"')
            os_info = os_info.strip().lower()
            
            if 'ubuntu' in os_info or 'debian' in os_info:
                # Ubuntu/Debian
                self.remote.run('sudo apt install -y build-essential curl wget git openssl libssl-dev')
            elif 'centos' in os_info or 'rhel' in os_info or 'rocky' in os_info:
                # CentOS/RHEL/Rocky
                self.remote.run('sudo yum install -y gcc gcc-c++ curl wget git openssl openssl-devel')
            elif 'alpine' in os_info:
                # Alpine
                self.remote.run('sudo apk add build-base curl wget git openssl openssl-dev')
            
            return True
        except Exception as e:
            self._log(f"依赖安装出错: {e}")
            return False
    
    def _install_python(self) -> bool:
        """
        安装Python
        """
        try:
            # 检查Python是否已安装
            python_version = self.remote.run('python3 --version 2>/dev/null || python --version 2>/dev/null')
            
            if 'Python 3.' in python_version:
                self._log(f"Python已安装: {python_version}")
                return True
            
            # 检测系统类型并安装Python
            os_info = self.remote.run('cat /etc/os-release | grep -E "^ID=" | cut -d= -f2 | tr -d \"\'"')
            os_info = os_info.strip().lower()
            
            if 'ubuntu' in os_info or 'debian' in os_info:
                # Ubuntu/Debian
                self.remote.run('sudo apt install -y python3 python3-pip python3-venv')
            elif 'centos' in os_info or 'rhel' in os_info or 'rocky' in os_info:
                # CentOS/RHEL/Rocky
                self.remote.run('sudo yum install -y python3 python3-pip python3-venv')
            elif 'alpine' in os_info:
                # Alpine
                self.remote.run('sudo apk add python3 py3-pip python3-venv')
            
            # 验证安装
            new_version = self.remote.run('python3 --version')
            return 'Python 3.' in new_version
        except Exception as e:
            self._log(f"Python安装出错: {e}")
            return False
    
    def _setup_venv(self, venv_path: str) -> bool:
        """
        安装和配置虚拟环境
        """
        try:
            # 扩展路径
            expanded_path = self.remote.run(f'echo {venv_path}')
            expanded_path = expanded_path.strip()
            
            # 创建虚拟环境目录
            self.remote.run(f'mkdir -p $(dirname {expanded_path})')
            
            # 删除现有虚拟环境
            self.remote.run(f'rm -rf {expanded_path}')
            
            # 创建虚拟环境
            self.remote.run(f'python3 -m venv {expanded_path}')
            
            # 激活虚拟环境并升级pip
            activate_cmd = f'source {expanded_path}/bin/activate && pip install --upgrade pip'
            self.remote.run(activate_cmd)
            
            # 验证虚拟环境
            venv_python = self.remote.run(f'{expanded_path}/bin/python --version')
            return 'Python 3.' in venv_python
        except Exception as e:
            self._log(f"虚拟环境配置出错: {e}")
            return False
    
    def _install_rcoder_server(self, use_venv: bool, venv_path: str) -> bool:
        """
        安装Rcoder服务器端
        """
        try:
            # 克隆Rcoder仓库
            self.remote.run('git clone https://github.com/trae-ai/rcoder-server ~/.rcoder/server')
            
            # 安装依赖
            if use_venv:
                expanded_path = self.remote.run(f'echo {venv_path}')
                expanded_path = expanded_path.strip()
                install_cmd = f'source {expanded_path}/bin/activate && pip install -r ~/.rcoder/server/requirements.txt'
            else:
                install_cmd = 'pip install -r ~/.rcoder/server/requirements.txt'
            
            self.remote.run(install_cmd)
            
            return True
        except Exception as e:
            self._log(f"Rcoder服务器安装出错: {e}")
            return False
    
    def _configure_server(self, server_type: str, use_venv: bool, venv_path: str) -> Dict[str, Any]:
        """
        配置服务器
        """
        try:
            # 创建配置文件
            config = {
                'server_type': server_type,
                'port': 443,
                'use_https': True,
                'enable_compression': True,
                'enable_connection_pool': True
            }
            
            # 写入配置文件
            config_json = str(config).replace("'", '"')
            self.remote.run(f'echo "{config_json}" > ~/.rcoder/server/config.json')
            
            # 创建启动脚本
            if use_venv:
                expanded_path = self.remote.run(f'echo {venv_path}')
                expanded_path = expanded_path.strip()
                start_script = f"#!/bin/bash\nsource {expanded_path}/bin/activate\npython ~/.rcoder/server/server.py"
            else:
                start_script = f"#!/bin/bash\npython ~/.rcoder/server/server.py"
            
            self.remote.run(f'echo "{start_script}" > ~/.rcoder/server/start.sh')
            self.remote.run('chmod +x ~/.rcoder/server/start.sh')
            
            # 创建systemd服务文件
            service_file = f"[Unit]\nDescription=Rcoder Server\nAfter=network.target\n\n[Service]\nType=simple\nUser=$(whoami)\nExecStart=~/.rcoder/server/start.sh\nRestart=always\n\n[Install]\nWantedBy=multi-user.target"
            self.remote.run(f'echo "{service_file}" | sudo tee /etc/systemd/system/rcoder.service')
            
            return config
        except Exception as e:
            self._log(f"服务器配置出错: {e}")
            return {}
    
    def _start_services(self, use_venv: bool, venv_path: str) -> bool:
        """
        启动服务
        """
        try:
            # 重新加载systemd
            self.remote.run('sudo systemctl daemon-reload')
            
            # 启用并启动服务
            self.remote.run('sudo systemctl enable rcoder.service')
            self.remote.run('sudo systemctl start rcoder.service')
            
            # 等待服务启动
            time.sleep(5)
            
            # 检查服务状态
            status = self.remote.run('sudo systemctl status rcoder.service | grep -E "Active:"')
            return 'active (running)' in status
        except Exception as e:
            self._log(f"服务启动出错: {e}")
            return False
    
    def _verify_installation(self) -> bool:
        """
        验证安装
        """
        try:
            # 检查服务状态
            status = self.remote.run('sudo systemctl status rcoder.service | grep -E "Active:"')
            if 'active (running)' not in status:
                return False
            
            # 测试连接
            test_result = self.remote.run('curl -s http://localhost:443/health')
            return 'ok' in test_result.lower()
        except Exception as e:
            self._log(f"安装验证出错: {e}")
            return False


def install_server(remote_host, server_type: str = 'target', 
                  use_venv: bool = True, 
                  venv_path: str = '~/.rcoder/venv') -> Dict[str, Any]:
    """
    安装服务器的便捷函数
    
    Args:
        remote_host: 远程主机实例
        server_type: 服务器类型
        use_venv: 是否使用虚拟环境
        venv_path: 虚拟环境路径
    
    Returns:
        安装结果
    """
    installer = ServerInstaller(remote_host)
    return installer.install_rcoder_server(server_type, use_venv, venv_path)
