#!/usr/bin/env python3
"""
Rcoder 系统进程管理模块
支持守护进程模式和系统服务注册
"""

import os
import sys
import time
import daemon
import psutil
import platform
import subprocess
from typing import Optional, Dict, Any


class ProcessManager:
    """
    进程管理器
    """
    
    def __init__(self):
        """
        初始化进程管理器
        """
        self.pid_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rcoder.pid')
        self.log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rcoder.log')
        self.platform = platform.system().lower()
    
    def is_running(self) -> bool:
        """
        检查rcoder是否正在运行
        
        Returns:
            bool: 是否正在运行
        """
        if not os.path.exists(self.pid_file):
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # 检查进程是否存在
            process = psutil.Process(pid)
            return process.is_running()
        except:
            return False
    
    def get_pid(self) -> Optional[int]:
        """
        获取当前运行的PID
        
        Returns:
            int: PID或None
        """
        if not os.path.exists(self.pid_file):
            return None
        
        try:
            with open(self.pid_file, 'r') as f:
                return int(f.read().strip())
        except:
            return None
    
    def start_daemon(self, main_func):
        """
        以守护进程模式启动
        
        Args:
            main_func: 主函数
        """
        if self.is_running():
            print(f"❌ Rcoder已经在运行 (PID: {self.get_pid()})")
            return False
        
        print(f"🔄 以守护进程模式启动Rcoder...")
        print(f"📋 PID文件: {self.pid_file}")
        print(f"📋 日志文件: {self.log_file}")
        
        # 创建日志目录
        log_dir = os.path.dirname(self.log_file)
        os.makedirs(log_dir, exist_ok=True)
        
        # 以守护进程模式运行
        with open(self.log_file, 'a') as log:
            with daemon.DaemonContext(
                stdout=log,
                stderr=log,
                working_directory=os.path.dirname(os.path.abspath(__file__))
            ):
                # 写入PID
                with open(self.pid_file, 'w') as f:
                    f.write(str(os.getpid()))
                
                try:
                    print(f"✅ Rcoder守护进程已启动 (PID: {os.getpid()})")
                    main_func()
                finally:
                    # 清理PID文件
                    if os.path.exists(self.pid_file):
                        try:
                            os.remove(self.pid_file)
                        except:
                            pass
        
        return True
    
    def stop(self):
        """
        停止运行的Rcoder进程
        
        Returns:
            bool: 是否停止成功
        """
        if not self.is_running():
            print("❌ Rcoder未在运行")
            return False
        
        pid = self.get_pid()
        print(f"🔄 停止Rcoder进程 (PID: {pid})...")
        
        try:
            process = psutil.Process(pid)
            process.terminate()
            
            # 等待进程退出
            for _ in range(10):
                if not process.is_running():
                    break
                time.sleep(0.5)
            
            # 如果进程仍在运行，强制终止
            if process.is_running():
                process.kill()
                time.sleep(0.5)
            
            # 清理PID文件
            if os.path.exists(self.pid_file):
                os.remove(self.pid_file)
            
            print("✅ Rcoder进程已停止")
            return True
        except Exception as e:
            print(f"❌ 停止进程失败: {e}")
            return False
    
    def restart(self, main_func):
        """
        重启Rcoder进程
        
        Args:
            main_func: 主函数
        
        Returns:
            bool: 是否重启成功
        """
        print("🔄 重启Rcoder进程...")
        
        # 停止当前进程
        self.stop()
        
        # 启动新进程
        return self.start_daemon(main_func)
    
    def status(self):
        """
        查看Rcoder运行状态
        """
        if self.is_running():
            pid = self.get_pid()
            process = psutil.Process(pid)
            status = {
                'pid': pid,
                'status': process.status(),
                'memory': f"{process.memory_info().rss / 1024 / 1024:.2f} MB",
                'cpu': f"{process.cpu_percent(interval=1):.1f}%",
                'start_time': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(process.create_time()))
            }
            
            print("✅ Rcoder运行状态:")
            for key, value in status.items():
                print(f"  {key}: {value}")
            
            return status
        else:
            print("❌ Rcoder未在运行")
            return None
    
    def register_service(self):
        """
        注册为系统服务
        """
        print(f"🔄 在{self.platform}平台注册系统服务...")
        
        if self.platform == 'linux':
            return self._register_linux_service()
        elif self.platform == 'windows':
            return self._register_windows_service()
        elif self.platform == 'darwin':
            return self._register_mac_service()
        else:
            print(f"❌ 不支持的平台: {self.platform}")
            return False
    
    def _register_linux_service(self):
        """
        在Linux上注册系统服务
        """
        service_file = '/etc/systemd/system/rcoder.service'
        python_path = sys.executable
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rcoder_main.py')
        
        service_content = f"""
[Unit]
Description=Rcoder - 远程代码执行与管理系统
After=network.target

[Service]
Type=simple
ExecStart={python_path} {script_path} --daemon
WorkingDirectory={os.path.dirname(script_path)}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""
        
        try:
            # 写入服务文件
            with open(service_file, 'w') as f:
                f.write(service_content)
            
            # 重新加载systemd
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            
            # 启用服务
            subprocess.run(['systemctl', 'enable', 'rcoder.service'], check=True)
            
            print(f"✅ 已在Linux上注册系统服务: {service_file}")
            print("📋 服务命令:")
            print("  systemctl start rcoder.service    # 启动服务")
            print("  systemctl stop rcoder.service     # 停止服务")
            print("  systemctl status rcoder.service   # 查看状态")
            print("  systemctl enable rcoder.service   # 开机自启")
            print("  systemctl disable rcoder.service  # 禁用开机自启")
            
            return True
        except Exception as e:
            print(f"❌ 注册Linux服务失败: {e}")
            print("⚠️  可能需要sudo权限")
            return False
    
    def _register_windows_service(self):
        """
        在Windows上注册系统服务
        """
        try:
            # 使用sc命令创建服务
            python_path = sys.executable
            script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rcoder_main.py')
            
            # 构建命令
            command = f'sc create Rcoder binPath= "{python_path} {script_path} --daemon" start= auto DisplayName= "Rcoder - 远程代码执行与管理系统"'
            
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            
            if 'SUCCESS' in result.stdout:
                print("✅ 已在Windows上注册系统服务: Rcoder")
                print("📋 服务命令:")
                print("  net start Rcoder    # 启动服务")
                print("  net stop Rcoder     # 停止服务")
                print("  sc query Rcoder     # 查看状态")
                print("  sc delete Rcoder    # 删除服务")
                return True
            else:
                print(f"❌ 注册Windows服务失败: {result.stderr}")
                print("⚠️  可能需要管理员权限")
                return False
        except Exception as e:
            print(f"❌ 注册Windows服务失败: {e}")
            return False
    
    def _register_mac_service(self):
        """
        在Mac上注册系统服务
        """
        launchd_plist = '~/Library/LaunchAgents/com.rcoder.plist'
        python_path = sys.executable
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'rcoder_main.py')
        
        plist_content = f"""
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rcoder</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
        <string>--daemon</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{self.log_file}</string>
    <key>StandardErrorPath</key>
    <string>{self.log_file}</string>
</dict>
</plist>
"""
        
        try:
            plist_path = os.path.expanduser(launchd_plist)
            plist_dir = os.path.dirname(plist_path)
            os.makedirs(plist_dir, exist_ok=True)
            
            # 写入plist文件
            with open(plist_path, 'w') as f:
                f.write(plist_content)
            
            # 加载服务
            subprocess.run(['launchctl', 'load', plist_path], check=True)
            
            print(f"✅ 已在Mac上注册系统服务: {plist_path}")
            print("📋 服务命令:")
            print(f"  launchctl load {plist_path}    # 加载服务")
            print(f"  launchctl unload {plist_path}  # 卸载服务")
            print(f"  launchctl start com.rcoder     # 启动服务")
            print(f"  launchctl stop com.rcoder      # 停止服务")
            
            return True
        except Exception as e:
            print(f"❌ 注册Mac服务失败: {e}")
            return False
    
    def unregister_service(self):
        """
        注销系统服务
        """
        print(f"🔄 注销系统服务...")
        
        if self.platform == 'linux':
            return self._unregister_linux_service()
        elif self.platform == 'windows':
            return self._unregister_windows_service()
        elif self.platform == 'darwin':
            return self._unregister_mac_service()
        else:
            print(f"❌ 不支持的平台: {self.platform}")
            return False
    
    def _unregister_linux_service(self):
        """
        在Linux上注销系统服务
        """
        try:
            subprocess.run(['systemctl', 'stop', 'rcoder.service'], check=True)
            subprocess.run(['systemctl', 'disable', 'rcoder.service'], check=True)
            subprocess.run(['rm', '/etc/systemd/system/rcoder.service'], check=True)
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
            
            print("✅ 已注销Linux系统服务")
            return True
        except Exception as e:
            print(f"❌ 注销Linux服务失败: {e}")
            return False
    
    def _unregister_windows_service(self):
        """
        在Windows上注销系统服务
        """
        try:
            subprocess.run('sc stop Rcoder', shell=True, capture_output=True)
            result = subprocess.run('sc delete Rcoder', shell=True, capture_output=True, text=True)
            
            if 'SUCCESS' in result.stdout:
                print("✅ 已注销Windows系统服务")
                return True
            else:
                print(f"❌ 注销Windows服务失败: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ 注销Windows服务失败: {e}")
            return False
    
    def _unregister_mac_service(self):
        """
        在Mac上注销系统服务
        """
        plist_path = os.path.expanduser('~/Library/LaunchAgents/com.rcoder.plist')
        
        try:
            subprocess.run(['launchctl', 'unload', plist_path], check=True)
            if os.path.exists(plist_path):
                os.remove(plist_path)
            
            print("✅ 已注销Mac系统服务")
            return True
        except Exception as e:
            print(f"❌ 注销Mac服务失败: {e}")
            return False


# 测试代码
if __name__ == "__main__":
    def test_main():
        print("✅ Rcoder守护进程测试")
        while True:
            time.sleep(1)
    
    pm = ProcessManager()
    
    import argparse
    parser = argparse.ArgumentParser(description='Rcoder进程管理')
    parser.add_argument('--start', action='store_true', help='启动守护进程')
    parser.add_argument('--stop', action='store_true', help='停止进程')
    parser.add_argument('--restart', action='store_true', help='重启进程')
    parser.add_argument('--status', action='store_true', help='查看状态')
    parser.add_argument('--register-service', action='store_true', help='注册系统服务')
    parser.add_argument('--unregister-service', action='store_true', help='注销系统服务')
    
    args = parser.parse_args()
    
    if args.start:
        pm.start_daemon(test_main)
    elif args.stop:
        pm.stop()
    elif args.restart:
        pm.restart(test_main)
    elif args.status:
        pm.status()
    elif args.register_service:
        pm.register_service()
    elif args.unregister_service:
        pm.unregister_service()
    else:
        parser.print_help()
