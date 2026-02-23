#!/usr/bin/env python3
"""
Rcoder 增强版命令行工具
集成MCP、TLS、远程部署等所有功能
"""

import sys
import os
import argparse
import json
import getpass
import subprocess

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_header(title):
    print("=" * 60)
    print(title)
    print("=" * 60)
    print()


def cmd_install(args):
    """install命令 - 完整安装"""
    print_header("Rcoder 完整安装")
    
    # 获取配置
    host = input(f"远程服务器IP (默认: 192.168.1.8): ").strip() or "192.168.1.8"
    port = input(f"远程服务器端口 (默认: 8099): ").strip() or "8099"
    port = int(port)
    password = getpass.getpass(f"远程服务器密码 (默认: ): ") or ""
    
    print()
    print("配置信息：")
    print(f"  服务器: {host}:{port}")
    print(f"  密码: {'*' * len(password)}")
    print()
    
    confirm = input("确认以上配置？(Y/n): ").strip().lower()
    if confirm not in ['', 'y', 'yes']:
        print("安装取消")
        return
    
    # 步骤1: 部署远程TLS服务端
    print()
    print("步骤1: 部署远程TLS服务端...")
    try:
        from deploy_tls_server import main as deploy_server
        deploy_server()
        print("✅ 远程TLS服务端部署成功")
    except Exception as e:
        print(f"❌ 远程部署失败: {e}")
        return
    
    # 步骤2: 生成本地MCP客户端
    print()
    print("步骤2: 生成本地MCP客户端...")
    try:
        script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        client_path = os.path.join(script_dir, "trae_skill", "rcoder_mcp_client.py")
        config_path = os.path.join(script_dir, "trae_skill", "rcoder_mcp_config.json")
        
        # 生成客户端
        template = '''#!/usr/bin/env python3
"""
Rcoder MCP客户端 - Trae直接连接，内部TLS连接远程
符合JSON-RPC 2.0规范
"""

import sys
import json
import socket
import ssl
import os

REMOTE_HOST = "{host}"
REMOTE_PORT = {port}
PASSWORD = "{password}"
CERT_FILE = os.path.join(os.path.dirname(__file__), "..", "trae_cert", "server.crt")

def send_command(cmd):
    try:
        print(f"[DEBUG] 连接 {{REMOTE_HOST}}:{{REMOTE_PORT}}", file=sys.stderr)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(CERT_FILE)
        context.check_hostname = False
        
        tls_sock = context.wrap_socket(sock, server_hostname=REMOTE_HOST)
        tls_sock.connect((REMOTE_HOST, REMOTE_PORT))
        
        print("[DEBUG] TLS连接成功", file=sys.stderr)

        req = json.dumps({{"command": cmd, "password": PASSWORD}})
        tls_sock.send(req.encode())
        print(f"[DEBUG] 发送命令: {{cmd[:50]}}...", file=sys.stderr)

        resp = tls_sock.recv(8192)
        print("[DEBUG] 收到响应", file=sys.stderr)
        tls_sock.close()

        result = json.loads(resp.decode('utf-8'))
        print(f"[DEBUG] 解析结果成功", file=sys.stderr)
        return result
    except Exception as e:
        print(f"[ERROR] {{type(e).__name__}}: {{str(e)}}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return {{"success": False, "error": f"{{type(e).__name__}}: {{str(e)}}"}}


def main():
    print(f"[Rcoder MCP客户端] 已启动", file=sys.stderr)

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                print("[DEBUG] stdin关闭，退出", file=sys.stderr)
                break

            line = line.strip()
            if not line:
                continue

            request = json.loads(line)
            request_id = request.get("id")
            method = request.get("method", "")
            params = request.get("params", {{}}) or {{}}

            print(f"[DEBUG] 收到请求: {{method}}, id: {{request_id}}", file=sys.stderr)
            print(f"[DEBUG] 完整请求: {{json.dumps(request)}}", file=sys.stderr)

            response = {{"jsonrpc": "2.0", "id": request_id}}

            if method == "initialize":
                response["result"] = {{
                    "protocolVersion": "2024-11-05",
                    "capabilities": {{"tools": {{}}}},
                    "serverInfo": {{"name": "rcoder", "version": "1.0.0"}}
                }}
            elif method == "tools/list":
                response["result"] = {{
                    "tools": [
                        {{"name": "execute", "description": "执行远程命令",
                         "inputSchema": {{"type": "object", "properties": {{"command": {{"type": "string"}}}}, "required": ["command"]}}}},
                        {{"name": "getStatus", "description": "查看系统状态", "inputSchema": {{"type": "object", "properties": {{}}}}}},
                        {{"name": "listDirectory", "description": "列出目录",
                         "inputSchema": {{"type": "object", "properties": {{"path": {{"type": "string", "default": "."}}}}}}}},
                    ]
                }}
            elif method == "tools/call":
                name = params.get("name", "")
                args_val = params.get("arguments", {{}})

                if name == "execute":
                    cmd = args_val.get("command", "")
                    result = send_command(cmd)
                    response["result"] = {{"content": [{{"type": "text", "text": json.dumps(result)}}]}}
                elif name == "getStatus":
                    result = send_command("echo '=== 系统状态 ===' && uname -a && uptime && free -h")
                    response["result"] = {{"content": [{{"type": "text", "text": json.dumps(result)}}]}}
                elif name == "listDirectory":
                    path = args_val.get("path", ".")
                    result = send_command(f"ls -la {{path}}")
                    response["result"] = {{"content": [{{"type": "text", "text": json.dumps(result)}}]}}
                else:
                    response["error"] = {{"code": -32601, "message": f"未知工具: {{name}}"}}
            else:
                response["error"] = {{"code": -32601, "message": f"未知方法: {{method}}"}}

            response_str = json.dumps(response)
            print(f"[DEBUG] 发送响应: {{response_str}}", file=sys.stderr)
            print(response_str, flush=True)

        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON解析错误: {{e}}, 内容: {{line[:100]}}", file=sys.stderr)
            error_resp = {{
                "jsonrpc": "2.0",
                "id": None,
                "error": {{"code": -32700, "message": f"JSON解析错误: {{str(e)}}"}}
            }}
            print(json.dumps(error_resp), flush=True)
        except Exception as e:
            print(f"[ERROR] {{type(e).__name__}}: {{str(e)}}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            error_resp = {{
                "jsonrpc": "2.0",
                "id": None,
                "error": {{"code": -32603, "message": f"{{type(e).__name__}}: {{str(e)}}"}}
            }}
            print(json.dumps(error_resp), flush=True)


if __name__ == "__main__":
    main()
'''
        content = template.format(host=host, port=port, password=password)
        
        with open(client_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        # 生成配置
        config = {
            "mcpServers": {
                "Rcoder": {
                    "command": "python",
                    "args": [client_path]
                }
            }
        }
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        print(f"✅ 本地MCP客户端生成: {client_path}")
        print(f"✅ MCP配置生成: {config_path}")
        
    except Exception as e:
        print(f"❌ 本地客户端生成失败: {e}")
        return
    
    # 完成
    print()
    print("=" * 60)
    print("🎉 完整安装成功！")
    print("=" * 60)
    print()
    print("下一步：")
    print("1. 在Trae中打开MCP设置")
    print("2. 选择'手动添加'")
    print("3. 复制以下配置并粘贴：")
    print()
    with open(config_path, "r", encoding="utf-8") as f:
        print(f.read())
    print()


def cmd_mcp(args):
    """mcp命令 - MCP配置管理"""
    print_header("Rcoder MCP 配置")
    
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(script_dir, "trae_skill", "rcoder_mcp_config.json")
    
    if args.action == "show":
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                print(f.read())
        else:
            print("❌ MCP配置文件不存在，请先运行 'rcoder install'")
    
    elif args.action == "status":
        # 测试MCP客户端
        print("测试MCP客户端...")
        client_path = os.path.join(script_dir, "trae_skill", "rcoder_mcp_client.py")
        
        if not os.path.exists(client_path):
            print("❌ MCP客户端不存在，请先运行 'rcoder install'")
            return
        
        # 简单测试
        try:
            import subprocess
            proc = subprocess.Popen(
                ["python", client_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
            
            # 发送initialize
            init_req = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {}
            }
            proc.stdin.write(json.dumps(init_req) + "\n")
            proc.stdin.flush()
            
            line = proc.stdout.readline()
            if line:
                print("✅ MCP客户端启动成功")
                print(f"响应: {line.strip()}")
            else:
                print("❌ MCP客户端没有响应")
            
            proc.terminate()
            
        except Exception as e:
            print(f"❌ 测试失败: {e}")


def main():
    """主入口"""
    parser = argparse.ArgumentParser(
        description='Rcoder - 增强版远程代码执行与管理系统',
        epilog='示例: rcoder install'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # install 命令
    install_parser = subparsers.add_parser('install', help='完整安装（远程服务端+本地客户端）')
    
    # mcp 命令
    mcp_parser = subparsers.add_parser('mcp', help='MCP配置管理')
    mcp_parser.add_argument('action', choices=['show', 'status'], help='MCP操作')
    
    # 原有命令 - 保持兼容
    from rcoder.utils import (
        quick_setup, get_default_remote, validate_config,
        export_config, import_config, create_alias
    )
    
    # setup 命令
    setup_parser = subparsers.add_parser('setup', help='快速设置向导')
    
    # run 命令
    run_parser = subparsers.add_parser('run', help='执行命令')
    run_parser.add_argument('cmd', help='要执行的命令')
    run_parser.add_argument('-s', '--server', help='服务器名称')
    run_parser.add_argument('-t', '--timeout', type=int, default=60, help='超时时间')
    
    # ls 命令
    ls_parser = subparsers.add_parser('ls', help='列出目录内容')
    ls_parser.add_argument('path', nargs='?', default='.', help='目录路径')
    ls_parser.add_argument('-s', '--server', help='服务器名称')
    
    # status 命令
    status_parser = subparsers.add_parser('status', help='查看系统状态')
    status_parser.add_argument('-s', '--server', help='服务器名称')
    
    args = parser.parse_args()
    
    # 处理新命令
    if args.command == 'install':
        cmd_install(args)
    elif args.command == 'mcp':
        cmd_mcp(args)
    
    # 处理原有命令
    elif args.command == 'setup':
        quick_setup()
    
    elif args.command == 'run':
        try:
            remote = get_default_remote()
            result = remote.run(args.cmd, timeout=args.timeout)
            print(result)
        except Exception as e:
            print(f"❌ 执行命令失败: {e}")
            sys.exit(1)
    
    elif args.command == 'ls':
        try:
            remote = get_default_remote()
            result = remote.ls(args.path)
            print(result)
        except Exception as e:
            print(f"❌ 列出目录失败: {e}")
            sys.exit(1)
    
    elif args.command == 'status':
        try:
            remote = get_default_remote()
            print("=== 系统状态 ===")
            print(remote.hostname())
            print(remote.uptime())
        except Exception as e:
            print(f"❌ 获取系统状态失败: {e}")
            sys.exit(1)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
