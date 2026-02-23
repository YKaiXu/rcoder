# Rcoder - 远程代码执行与管理系统

Rcoder 是一个功能强大的远程管理系统，允许您直接与远程主机通信，无需客户端，使用远程主机就像使用本地主机一样简单。

## ✨ 核心特性

- **无需 MCP 或技能配置**：直接通过 Python 导入使用
- **HTTPS 伪装**：支持自定义端口，增强网络安全性
- **中转服务器**：支持通过其他服务器中转，解决网络限制问题
- **批量命令执行**：一次执行多个命令，提高效率
- **异步操作**：支持异步执行命令，不阻塞主线程
- **监控和告警**：实时监控系统状态，及时发现问题
- **密钥认证**：基于公钥私钥机制，确保通信安全
- **类似本地使用体验**：提供 `ls`、`cat`、`mkdir` 等常用命令的封装

## 🚀 快速开始

### 方法 1：命令行工具（推荐）

```bash
# 快速设置向导
python -m rcoder.cli setup

# 执行命令
python -m rcoder.cli run "ls -la"

# 查看系统状态
python -m rcoder.cli status

# 批量执行命令
python -m rcoder.cli batch "echo hello" "hostname" "date"
```

### 方法 2：直接导入使用

```python
# 导入模块
from rcoder.utils import get_default_remote

# 获取默认远程主机实例
remote = get_default_remote()

# 执行命令
result = remote.run("ls -la")
print(result)

# 使用便捷方法
print(remote.ls("."))      # 列出目录
print(remote.cat("file.txt"))  # 查看文件
print(remote.uptime())     # 查看系统运行时间
```

## 📦 安装

### 1. 克隆代码库

```bash
git clone <repository-url>
cd openclaw
```

### 2. 安装依赖

Rcoder 依赖极少，主要使用 Python 标准库：

- Python 3.7+
- 标准库：ssl, socket, json, time, asyncio, hashlib, threading, queue

### 3. 配置服务器

#### 方法 A：使用快速设置向导

```bash
python -m rcoder.cli setup
```

按照提示输入服务器信息：
- 服务器名称（例如：my-server）
- 服务器地址（IP 或域名）
- 端口号（默认 443，支持自定义）
- 是否启用 HTTPS 伪装
- 是否使用中转服务器

#### 方法 B：手动创建配置文件

创建 `~/.rcoder/config.json` 文件：

```json
{
  "servers": {
    "my-server": {
      "host": "192.168.1.8",
      "port": 443,
      "use_https_disguise": true,
      "proxy_server": null
    }
  },
  "default_server": "my-server",
  "timeout": 60,
  "restart_max_wait": 60,
  "monitoring_interval": 30
}
```

## 🎯 使用指南

### 基本命令执行

```python
from rcoder.utils import get_default_remote

remote = get_default_remote()

# 执行任意命令
result = remote.run("echo 'Hello Rcoder'")
print(result)

# 等待重启完成
result = remote.run("reboot", wait_for_restart=True)
print(result)
```

### 批量命令执行

```python
commands = [
    "echo 'Command 1'",
    "hostname",
    "date",
    "whoami"
]

results = remote.run_batch(commands)
for cmd, res in results.items():
    print(f"命令: {cmd}")
    print(f"结果: {res}")
    print()
```

### 异步操作

```python
import asyncio

async def main():
    # 异步执行单个命令
    result = await remote.run_async("ls -la")
    print(result)
    
    # 异步批量执行命令
    commands = ["echo 1", "echo 2", "echo 3"]
    results = await remote.run_batch_async(commands)
    print(results)

asyncio.run(main())
```

### 文件操作

```python
# 列出目录
print(remote.ls("."))

# 查看文件内容
print(remote.cat("README.md"))

# 创建目录
print(remote.mkdir("new_dir"))

# 删除文件
print(remote.rm("file.txt"))

# 复制文件
print(remote.cp("source.txt", "dest.txt"))

# 移动文件
print(remote.mv("old.txt", "new.txt"))
```

### 系统服务管理

```python
# 启动服务
print(remote.systemctl("start", "nginx"))

# 停止服务
print(remote.systemctl("stop", "nginx"))

# 重启服务（自动等待完成）
print(remote.systemctl("restart", "nginx"))

# 查看服务状态
print(remote.systemctl("status", "nginx"))
```

### 系统信息查看

```python
# 查看主机名
print(remote.hostname())

# 查看系统运行时间
print(remote.uptime())

# 查看内存使用
print(remote.free())

# 查看磁盘使用
print(remote.df())

# 查看 IP 地址
print(remote.ip())

# 查看进程
print(remote.ps())

# 查看系统负载
print(remote.top())
```

## 🔧 高级配置

### HTTPS 伪装配置

在配置文件中设置：

```json
{
  "servers": {
    "my-server": {
      "host": "192.168.1.8",
      "port": 8443,  # 自定义端口
      "use_https_disguise": true,  # 启用 HTTPS 伪装
      "proxy_server": null
    }
  }
}
```

### 中转服务器配置

```json
{
  "servers": {
    "us-server": {
      "host": "us-server.com",
      "port": 443,
      "use_https_disguise": true,
      "proxy_server": ["hk-server.com", 443]  # 通过香港服务器中转
    }
  }
}
```

### 密钥认证配置

```python
from rcoder.core import get_remote_host

# 获取远程主机实例
remote = get_remote_host(host='192.168.1.8')

# 开始使用
print(remote.run("ls -la"))
```

## 📡 网络配置

### 公网访问

对于有公网 IP 或 IPv6 地址的服务器，可以直接配置：

```json
{
  "servers": {
    "public-server": {
      "host": "your-public-ip",  # 公网 IP
      "port": 443,               # 或自定义端口
      "use_https_disguise": true,
      "proxy_server": null
    }
  }
}
```

### 防火墙设置

确保服务器防火墙允许相应端口的访问：

```bash
# 允许 443 端口
sudo ufw allow 443/tcp

# 允许自定义端口（例如 8443）
sudo ufw allow 8443/tcp
```

## 🚨 故障排查

### 常见问题

1. **连接失败**
   - 检查服务器地址和端口是否正确
   - 确认服务器防火墙是否允许相应端口
   - 验证网络连接是否正常

2. **命令执行失败**
   - 检查命令是否在远程服务器上可用
   - 确认用户权限是否足够
   - 查看错误信息，针对性解决

3. **HTTPS 伪装问题**
   - 确保端口设置正确
   - 验证 SSL 配置是否有效

4. **中转服务器问题**
   - 检查中转服务器是否可访问
   - 确认中转服务器配置是否正确

### 日志查看

```python
# 启用监控
remote.rcoder.start_monitoring()

# 查看告警
alerts = remote.rcoder.get_alerts()
for alert in alerts:
    print(f"告警: {alert}")

# 停止监控
remote.rcoder.stop_monitoring()
```

## 📖 命令行工具参考

### 基本命令

| 命令 | 描述 | 示例 |
|------|------|------|
| `setup` | 快速设置向导 | `python -m rcoder.cli setup` |
| `run` | 执行命令 | `python -m rcoder.cli run "ls -la"` |
| `batch` | 批量执行命令 | `python -m rcoder.cli batch "echo 1" "echo 2"` |
| `ls` | 列出目录内容 | `python -m rcoder.cli ls /home` |
| `cat` | 查看文件内容 | `python -m rcoder.cli cat /etc/hosts` |
| `status` | 查看系统状态 | `python -m rcoder.cli status` |
| `config` | 配置管理 | `python -m rcoder.cli config validate` |

### 配置管理命令

| 子命令 | 描述 | 示例 |
|--------|------|------|
| `validate` | 验证配置文件 | `python -m rcoder.cli config validate` |
| `export` | 导出配置文件 | `python -m rcoder.cli config export` |
| `import` | 导入配置文件 | `python -m rcoder.cli config import config.json` |
| `alias` | 创建命令行别名 | `python -m rcoder.cli config alias` |

## 🎨 使用技巧

### 1. 创建命令行别名

```bash
# Linux/macOS
echo 'alias rcoder="python -m rcoder.cli"' >> ~/.bashrc
source ~/.bashrc

# Windows (命令提示符)
doskey rcoder=python -m rcoder.cli $*

# 使用别名
rcoder run "ls -la"
```

### 2. 在脚本中使用

```python
#!/usr/bin/env python3
"""自动化脚本示例"""

from rcoder.utils import get_default_remote

def main():
    remote = get_default_remote()
    
    # 检查系统状态
    print("=== 系统状态检查 ===")
    print(remote.uptime())
    print(remote.free())
    print(remote.df())
    
    # 执行维护任务
    print("\n=== 执行维护任务 ===")
    commands = [
        "apt update",
        "apt upgrade -y",
        "apt autoremove -y",
        "apt clean"
    ]
    
    results = remote.run_batch(commands)
    for cmd, res in results.items():
        print(f"命令: {cmd}")
        print(f"结果: {res[:200]}..." if len(res) > 200 else res)
        print()

if __name__ == "__main__":
    main()
```

### 3. 多服务器管理

```python
from rcoder.core import get_remote_host

# 服务器 1
server1 = get_remote_host(host='server1.com', port=443)

# 服务器 2（通过中转）
server2 = get_remote_host(
    host='server2.com', 
    port=443, 
    proxy_server=('hk-proxy.com', 443)
)

# 分别执行命令
print("服务器 1:")
print(server1.run("hostname"))

print("\n服务器 2:")
print(server2.run("hostname"))
```

## 📄 配置文件结构

```json
{
  "servers": {
    "server-name": {
      "host": "服务器地址",
      "port": 端口号,
      "use_https_disguise": true/false,
      "proxy_server": ["中转服务器地址", 端口号]  // 可选
    }
  },
  "default_server": "默认服务器名称",
  "timeout": 命令超时时间（秒）,
  "restart_max_wait": 重启最大等待时间（秒）,
  "monitoring_interval": 监控间隔（秒）
}
```

## 🔒 安全最佳实践

1. **使用密钥认证**：优先使用公钥私钥认证，避免密码传输
2. **限制访问**：仅允许必要的 IP 地址访问 rcoder 服务
3. **使用 HTTPS 伪装**：启用 HTTPS 伪装功能，增强网络安全性
4. **定期更新**：定期更新 rcoder 和依赖库
5. **使用强密码**：如果需要密码认证，使用强密码
6. **监控异常**：启用监控功能，及时发现异常情况

## 🆚 与 SSH 对比

| 特性 | Rcoder | SSH |
|------|--------|-----|
| 无需客户端 | ✅ | ❌
| HTTPS 伪装 | ✅ | ❌
| 中转服务器 | ✅ | ❌
| 批量命令执行 | ✅ | ⚠️（需要脚本）
| 异步操作 | ✅ | ❌
| 监控和告警 | ✅ | ❌
| 类似本地使用体验 | ✅ | ⚠️（需要学习 SSH 命令）
| 跨平台支持 | ✅ | ✅
| 安全性 | ✅ | ✅

## 📞 支持

如果您遇到问题或有任何建议，欢迎联系我们：

- 项目地址：https://github.com/YKaiXu/rcoder
- 文档：本 README 文件
- 示例：`examples/` 目录

## 📝 版本历史

- **v1.0.0** - 初始版本
  - 核心功能实现
  - 命令行工具
  - 配置管理
  - 文档完善

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request，共同改进 Rcoder！

---

**Rcoder - 让远程管理更简单！** 🚀
