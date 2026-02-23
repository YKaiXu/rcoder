# OpenClaw SSH 会话管理器

这是一个基于 asyncssh 的长期稳定 SSH 会话管理器，用于管理远程 OpenClaw 主机并进行配置。

## 功能特性

- ✅ 基于 asyncssh 的异步 SSH 连接
- ✅ 长期稳定的会话管理
- ✅ 远程命令执行
- ✅ 文件上传/下载
- ✅ OpenClaw 状态检查
- ✅ OpenClaw 配置管理
- ✅ OpenClaw 服务启动/停止

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速使用

### 基本用法

```python
import asyncio
from ssh_manager import SSHSessionManager, OpenClawManager

async def main():
    # 创建SSH会话管理器
    ssh_manager = SSHSessionManager()
    
    try:
        # 连接到远程主机
        session_id = await ssh_manager.connect(
            host="192.168.1.8",
            username="yupeng",
            password="your_password",
            alias="openclaw-host"
        )
        
        # 创建OpenClaw管理器
        openclaw_manager = OpenClawManager(ssh_manager)
        
        # 检查openclaw状态
        status = await openclaw_manager.check_openclaw_status(session_id)
        print("状态检查结果:")
        for cmd, result in status.items():
            print(f"命令: {cmd}")
            print(f" stdout: {result['stdout']}")
            print(f" stderr: {result['stderr']}")
            print(f" 退出码: {result['exit_code']}")
            print()
        
        # 配置openclaw
        config_result = await openclaw_manager.configure_openclaw(session_id, {})
        print("配置结果:")
        for cmd, result in config_result.items():
            print(f"命令: {cmd}")
            print(f" 退出码: {result['exit_code']}")
            print()
        
        # 启动openclaw
        start_result = await openclaw_manager.start_openclaw(session_id)
        print(f"启动结果 - 退出码: {start_result['exit_code']}")
        
        # 检查启动状态
        check_result = await ssh_manager.execute(session_id, "ps aux | grep openclaw | grep -v grep")
        print(f"运行状态:")
        print(check_result['stdout'])
        
    finally:
        # 关闭所有会话
        await ssh_manager.close_all()

if __name__ == "__main__":
    asyncio.run(main())
```

### 直接运行示例

```bash
python ssh_manager.py
```

## 配置说明

### OpenClaw 配置文件

默认配置文件位于 `~/.openclaw/config.yaml`，包含以下内容：

```yaml
# OpenClaw配置文件

# 服务器配置
server:
  host: 0.0.0.0
  port: 3000

# 认证配置
auth:
  enabled: true
  users:
    - username: admin
      password: admin123

# 模型配置
models:
  default: claude-3-opus-20240229

# 日志配置
logging:
  level: info
```

## 注意事项

1. **安全性**：请确保在生产环境中修改默认的认证密码
2. **网络**：确保远程主机的 SSH 服务已启动且可访问
3. **权限**：确保用户有足够的权限执行相关操作
4. **依赖**：远程主机需要已安装 OpenClaw

## 故障排查

### 常见问题

1. **SSH 连接失败**：检查网络连接、主机地址、用户名和密码
2. **OpenClaw 未找到**：检查远程主机是否已安装 OpenClaw
3. **配置文件写入失败**：检查用户权限
4. **服务启动失败**：查看日志文件 `~/.openclaw/openclaw.log`

### 日志查看

```bash
# 查看本地日志
python ssh_manager.py 2>&1 | tee ssh_manager.log

# 查看远程OpenClaw日志
ssh yupeng@192.168.1.8 'cat ~/.openclaw/openclaw.log'
```

## 高级用法

### 多会话管理

```python
# 连接多个主机
session1 = await ssh_manager.connect("192.168.1.8", "user1", "pass1", alias="host1")
session2 = await ssh_manager.connect("192.168.1.9", "user2", "pass2", alias="host2")

# 执行不同操作
await ssh_manager.execute(session1, "command1")
await ssh_manager.execute(session2, "command2")
```

### 文件传输

```python
# 上传文件
await ssh_manager.upload_file(session_id, "local_config.yaml", "~/.openclaw/config.yaml")

# 下载文件
await ssh_manager.download_file(session_id, "~/.openclaw/openclaw.log", "local_openclaw.log")
```
