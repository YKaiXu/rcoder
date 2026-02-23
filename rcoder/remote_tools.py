#!/usr/bin/env python3
"""
Rcoder 远程工具模块
针对远程编程场景的优化，特别是远程主机直接下载文件的功能
"""

import time
import asyncio
from typing import Optional, List, Dict, Any

class RemoteTools:
    """
    远程工具类
    提供针对远程编程场景的优化工具
    """
    
    def __init__(self, remote_host):
        """
        初始化远程工具
        
        Args:
            remote_host: RemoteHost实例
        """
        self.remote_host = remote_host
    
    def download_file(self, url: str, destination: str, use_cache: bool = False) -> str:
        """
        在远程主机上下载文件
        优化：直接在远程主机上下载，避免通过本地中转
        
        Args:
            url: 文件下载URL
            destination: 保存路径
            use_cache: 是否使用缓存
        """
        # 检查URL类型，使用合适的下载工具
        download_cmd = ""
        
        # 检查远程主机是否有wget或curl
        has_wget = 'wget' in self.remote_host.run('which wget', use_cache=True)
        has_curl = 'curl' in self.remote_host.run('which curl', use_cache=True)
        
        if has_wget:
            # 使用wget下载，添加重试和断点续传
            download_cmd = f"wget -c --tries=5 --timeout=30 '{url}' -O '{destination}'"
        elif has_curl:
            # 使用curl下载，添加重试
            download_cmd = f"curl -L --retry 5 --connect-timeout 30 '{url}' -o '{destination}'"
        else:
            # 尝试使用Python下载
            download_cmd = f"python3 -c \"import urllib.request; urllib.request.urlretrieve('{url}', '{destination}')\""
        
        # 执行下载命令
        print(f"📥 开始下载文件: {url}")
        print(f"💾 保存到: {destination}")
        
        start_time = time.time()
        result = self.remote_host.run(download_cmd, use_cache=use_cache)
        execution_time = time.time() - start_time
        
        print(f"✅ 下载完成 (耗时: {execution_time:.1f}秒)")
        return result
    
    async def download_file_async(self, url: str, destination: str, use_cache: bool = False) -> str:
        """
        异步在远程主机上下载文件
        """
        return await self.remote_host.run_async(
            f"wget -c --tries=5 --timeout=30 '{url}' -O '{destination}'",
            use_cache=use_cache
        )
    
    def download_github_repo(self, repo_url: str, destination: str = '.', 
                           branch: Optional[str] = None, use_cache: bool = False) -> str:
        """
        在远程主机上克隆GitHub仓库
        优化：直接在远程主机上克隆，避免通过本地中转
        
        Args:
            repo_url: GitHub仓库URL
            destination: 保存路径
            branch: 分支名称
            use_cache: 是否使用缓存
        """
        # 检查是否有git
        has_git = 'git' in self.remote_host.run('which git', use_cache=True)
        
        if not has_git:
            return "错误: 远程主机未安装git"
        
        # 构建git克隆命令
        git_cmd = "git clone"
        if branch:
            git_cmd += f" -b {branch}"
        git_cmd += f" --depth 1 '{repo_url}' '{destination}'"
        
        print(f"📥 开始克隆GitHub仓库: {repo_url}")
        if branch:
            print(f"🌿 分支: {branch}")
        print(f"💾 保存到: {destination}")
        
        start_time = time.time()
        result = self.remote_host.run(git_cmd, use_cache=use_cache)
        execution_time = time.time() - start_time
        
        print(f"✅ 克隆完成 (耗时: {execution_time:.1f}秒)")
        return result
    
    async def download_github_repo_async(self, repo_url: str, destination: str = '.', 
                                       branch: Optional[str] = None, use_cache: bool = False) -> str:
        """
        异步在远程主机上克隆GitHub仓库
        """
        git_cmd = "git clone"
        if branch:
            git_cmd += f" -b {branch}"
        git_cmd += f" --depth 1 '{repo_url}' '{destination}'"
        
        return await self.remote_host.run_async(git_cmd, use_cache=use_cache)
    
    def install_python_package(self, package: str, version: Optional[str] = None, 
                             use_pip3: bool = True, use_cache: bool = False) -> str:
        """
        在远程主机上安装Python包
        优化：直接在远程主机上安装，避免通过本地中转
        
        Args:
            package: 包名
            version: 版本号
            use_pip3: 是否使用pip3
            use_cache: 是否使用缓存
        """
        # 构建pip命令
        pip_cmd = "pip3" if use_pip3 else "pip"
        install_cmd = f"{pip_cmd} install --no-cache-dir"
        
        if version:
            install_cmd += f" '{package}=={version}'"
        else:
            install_cmd += f" '{package}'"
        
        print(f"📦 开始安装Python包: {package}")
        if version:
            print(f"🔢 版本: {version}")
        
        start_time = time.time()
        result = self.remote_host.run(install_cmd, use_cache=use_cache)
        execution_time = time.time() - start_time
        
        print(f"✅ 安装完成 (耗时: {execution_time:.1f}秒)")
        return result
    
    async def install_python_package_async(self, package: str, version: Optional[str] = None, 
                                         use_pip3: bool = True, use_cache: bool = False) -> str:
        """
        异步在远程主机上安装Python包
        """
        pip_cmd = "pip3" if use_pip3 else "pip"
        install_cmd = f"{pip_cmd} install --no-cache-dir"
        
        if version:
            install_cmd += f" '{package}=={version}'"
        else:
            install_cmd += f" '{package}'"
        
        return await self.remote_host.run_async(install_cmd, use_cache=use_cache)
    
    def install_python_packages(self, packages: List[str], use_pip3: bool = True, 
                              use_cache: bool = False) -> Dict[str, str]:
        """
        在远程主机上批量安装Python包
        
        Args:
            packages: 包名列表
            use_pip3: 是否使用pip3
            use_cache: 是否使用缓存
        """
        results = {}
        pip_cmd = "pip3" if use_pip3 else "pip"
        
        print(f"📦 开始批量安装Python包 ({len(packages)}个)")
        
        for package in packages:
            install_cmd = f"{pip_cmd} install --no-cache-dir '{package}'"
            print(f"  - 安装: {package}")
            
            try:
                result = self.remote_host.run(install_cmd, use_cache=use_cache)
                results[package] = result
                print(f"    ✅ 成功")
            except Exception as e:
                results[package] = f"错误: {e}"
                print(f"    ❌ 失败: {e}")
        
        print(f"✅ 批量安装完成")
        return results
    
    async def install_python_packages_async(self, packages: List[str], use_pip3: bool = True, 
                                          use_cache: bool = False) -> Dict[str, str]:
        """
        异步在远程主机上批量安装Python包
        """
        tasks = []
        pip_cmd = "pip3" if use_pip3 else "pip"
        
        for package in packages:
            install_cmd = f"{pip_cmd} install --no-cache-dir '{package}'"
            task = self.remote_host.run_async(install_cmd, use_cache=use_cache)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        return dict(zip(packages, results))
    
    def update_system_packages(self, use_cache: bool = False) -> str:
        """
        在远程主机上更新系统包
        
        Args:
            use_cache: 是否使用缓存
        """
        # 检查系统类型
        os_type = self.remote_host.run('uname -s', use_cache=True).strip()
        
        update_cmd = ""
        if 'Linux' in os_type:
            # 检查包管理器
            has_apt = 'apt' in self.remote_host.run('which apt', use_cache=True)
            has_yum = 'yum' in self.remote_host.run('which yum', use_cache=True)
            has_dnf = 'dnf' in self.remote_host.run('which dnf', use_cache=True)
            
            if has_apt:
                update_cmd = "sudo apt update && sudo apt upgrade -y"
            elif has_dnf:
                update_cmd = "sudo dnf update -y"
            elif has_yum:
                update_cmd = "sudo yum update -y"
            else:
                return "错误: 无法识别的Linux包管理器"
        else:
            return f"错误: 不支持的操作系统: {os_type}"
        
        print("🔄 开始更新系统包")
        
        start_time = time.time()
        result = self.remote_host.run(update_cmd, use_cache=use_cache)
        execution_time = time.time() - start_time
        
        print(f"✅ 系统包更新完成 (耗时: {execution_time:.1f}秒)")
        return result
    
    def download_pypi_package(self, package: str, version: Optional[str] = None, 
                             destination: str = '.', use_cache: bool = False) -> str:
        """
        在远程主机上下载PyPI包
        优化：直接在远程主机上下载，避免通过本地中转
        
        Args:
            package: 包名
            version: 版本号
            destination: 保存路径
            use_cache: 是否使用缓存
        """
        # 构建下载URL
        if version:
            url = f"https://pypi.org/packages/source/{package[0]}/{package}/{package}-{version}.tar.gz"
        else:
            # 获取最新版本
            version_cmd = f"python3 -c \"import json, urllib.request; print(json.loads(urllib.request.urlopen('https://pypi.org/pypi/{package}/json').read())['info']['version'])\""
            version = self.remote_host.run(version_cmd, use_cache=use_cache).strip()
            url = f"https://pypi.org/packages/source/{package[0]}/{package}/{package}-{version}.tar.gz"
        
        # 下载文件
        return self.download_file(url, f"{destination}/{package}-{version}.tar.gz", use_cache)
    
    def setup_development_environment(self, python_version: str = '3.8', 
                                    packages: Optional[List[str]] = None, 
                                    use_cache: bool = False) -> Dict[str, str]:
        """
        在远程主机上设置开发环境
        
        Args:
            python_version: Python版本
            packages: 要安装的Python包列表
            use_cache: 是否使用缓存
        """
        results = {}
        
        print("🚀 开始设置开发环境")
        
        # 更新系统包
        results['system_update'] = self.update_system_packages(use_cache)
        print()
        
        # 安装Python和开发工具
        os_type = self.remote_host.run('uname -s', use_cache=True).strip()
        
        if 'Linux' in os_type:
            has_apt = 'apt' in self.remote_host.run('which apt', use_cache=True)
            has_yum = 'yum' in self.remote_host.run('which yum', use_cache=True)
            has_dnf = 'dnf' in self.remote_host.run('which dnf', use_cache=True)
            
            if has_apt:
                dev_tools_cmd = "sudo apt install -y python3 python3-pip python3-venv build-essential git"
            elif has_dnf:
                dev_tools_cmd = "sudo dnf install -y python3 python3-pip python3-venv gcc git"
            elif has_yum:
                dev_tools_cmd = "sudo yum install -y python3 python3-pip python3-venv gcc git"
            else:
                results['dev_tools'] = "错误: 无法识别的Linux包管理器"
                return results
            
            print("📦 安装开发工具")
            results['dev_tools'] = self.remote_host.run(dev_tools_cmd, use_cache=use_cache)
            print("✅ 开发工具安装完成")
            print()
        
        # 安装Python包
        if packages:
            print(f"📦 安装Python包 ({len(packages)}个)")
            results['python_packages'] = self.install_python_packages(packages, use_cache=use_cache)
            print()
        
        # 验证环境
        print("🔍 验证开发环境")
        results['python_version'] = self.remote_host.run('python3 --version', use_cache=use_cache)
        results['pip_version'] = self.remote_host.run('pip3 --version', use_cache=use_cache)
        results['git_version'] = self.remote_host.run('git --version', use_cache=use_cache)
        
        print("✅ 开发环境设置完成")
        return results
    
    def optimize_remote_connection(self, use_cache: bool = True) -> str:
        """
        优化远程主机的网络连接
        
        Args:
            use_cache: 是否使用缓存
        """
        print("⚡ 开始优化远程连接")
        
        # 检查系统类型
        os_type = self.remote_host.run('uname -s', use_cache=use_cache).strip()
        
        if 'Linux' in os_type:
            # 优化SSH连接
            ssh_opt_cmd = """
sudo bash -c 'cat >> /etc/ssh/ssh_config << EOF\n\n# Rcoder 优化设置\nServerAliveInterval 30\nServerAliveCountMax 10\nCompression yes\nTCPKeepAlive yes\nEOF'
"""
            
            # 优化系统网络设置
            net_opt_cmd = """
sudo bash -c 'cat >> /etc/sysctl.conf << EOF\n\n# Rcoder 网络优化\nnet.core.rmem_max=16777216\nnet.core.wmem_max=16777216\nnet.ipv4.tcp_rmem=4096 87380 16777216\nnet.ipv4.tcp_wmem=4096 65536 16777216\nnet.ipv4.tcp_window_scaling=1\nnet.ipv4.tcp_timestamps=1\nnet.ipv4.tcp_slow_start_after_idle=0\nEOF'
sudo sysctl -p
"""
            
            print("🔧 优化SSH连接设置")
            ssh_result = self.remote_host.run(ssh_opt_cmd, use_cache=use_cache)
            
            print("🔧 优化系统网络设置")
            net_result = self.remote_host.run(net_opt_cmd, use_cache=use_cache)
            
            print("✅ 远程连接优化完成")
            return f"SSH优化: {ssh_result}\n网络优化: {net_result}"
        else:
            return f"错误: 不支持的操作系统: {os_type}"
    
    def create_project(self, project_name: str, template: str = 'basic', 
                      use_cache: bool = False) -> str:
        """
        在远程主机上创建项目
        
        Args:
            project_name: 项目名称
            template: 模板类型 (basic, flask, django, fastapi)
            use_cache: 是否使用缓存
        """
        print(f"🏗️  开始创建项目: {project_name}")
        print(f"📋 模板: {template}")
        
        # 创建项目目录
        self.remote_host.run(f"mkdir -p {project_name}", use_cache=use_cache)
        
        if template == 'basic':
            # 创建基本项目结构
            structure = [
                f"{project_name}/README.md",
                f"{project_name}/requirements.txt",
                f"{project_name}/{project_name}/",
                f"{project_name}/{project_name}/__init__.py",
                f"{project_name}/{project_name}/main.py",
                f"{project_name}/setup.py",
            ]
            
            for path in structure:
                if path.endswith('/'):
                    self.remote_host.run(f"mkdir -p {path}", use_cache=use_cache)
                else:
                    self.remote_host.run(f"touch {path}", use_cache=use_cache)
            
            # 写入基本内容
            self.remote_host.run(f"echo '# {project_name}' > {project_name}/README.md", use_cache=use_cache)
            self.remote_host.run(f"echo '"""{project_name} package"""\n\n__version__ = "0.1.0"' > {project_name}/{project_name}/__init__.py", use_cache=use_cache)
            self.remote_host.run(f"echo 'def main():\n    print(\"Hello from {project_name}!")' > {project_name}/{project_name}/main.py", use_cache=use_cache)
            
        elif template == 'flask':
            # 创建Flask项目
            self.install_python_package('Flask', use_cache=use_cache)
            self.remote_host.run(f"echo 'from flask import Flask\n\napp = Flask(__name__)\n\n@app.route(\"/\")\ndef hello():\n    return \"Hello, World!\"\n\nif __name__ == \"__main__\":\n    app.run(debug=True)' > {project_name}/app.py", use_cache=use_cache)
            self.remote_host.run(f"echo 'Flask' > {project_name}/requirements.txt", use_cache=use_cache)
            
        elif template == 'django':
            # 创建Django项目
            self.install_python_package('Django', use_cache=use_cache)
            self.remote_host.run(f"cd {project_name} && django-admin startproject {project_name} .", use_cache=use_cache)
            
        elif template == 'fastapi':
            # 创建FastAPI项目
            self.install_python_package('fastapi', use_cache=use_cache)
            self.install_python_package('uvicorn', use_cache=use_cache)
            self.remote_host.run(f"echo 'from fastapi import FastAPI\n\napp = FastAPI()\n\n@app.get(\"/\")\nasync def root():\n    return {\"message\": \"Hello World\"}' > {project_name}/app.py", use_cache=use_cache)
            self.remote_host.run(f"echo 'fastapi\nuvicorn' > {project_name}/requirements.txt", use_cache=use_cache)
        
        print(f"✅ 项目 '{project_name}' 创建完成")
        return f"项目 '{project_name}' 已创建，使用模板: {template}"


def get_remote_tools(remote_host) -> RemoteTools:
    """
    获取远程工具实例
    
    Args:
        remote_host: RemoteHost实例
    """
    return RemoteTools(remote_host)
