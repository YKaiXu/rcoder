# Rcoder - Remote Code Execution and Management System

Rcoder is a powerful remote management system that allows you to directly communicate with remote hosts without a client, making it as simple to use remote hosts as it is to use local ones.

## ✨ Core Features

- **No MCP or skill configuration required**: Directly use by importing in Python
- **HTTPS disguise**: Supports custom ports, enhancing network security
- **Transfer server**: Supports transfer through other servers to solve network restriction issues
- **Batch command execution**: Execute multiple commands at once, improving efficiency
- **Asynchronous operations**: Support for asynchronous command execution without blocking the main thread
- **Monitoring and alerts**: Real-time system status monitoring to detect issues promptly
- **Key authentication**: Based on public-private key mechanism to ensure communication security
- **Local-like usage experience**: Provides wrappers for common commands like `ls`, `cat`, `mkdir`

## 🚀 Quick Start

### Method 1: Command Line Tool (Recommended)

```bash
# Quick setup wizard
python -m rcoder.cli setup

# Execute command
python -m rcoder.cli run "ls -la"

# View system status
python -m rcoder.cli status

# Execute batch commands
python -m rcoder.cli batch "echo hello" "hostname" "date"
```

### Method 2: Direct Import Usage

```python
# Import module
from rcoder.utils import get_default_remote

# Get default remote host instance
remote = get_default_remote()

# Execute command
result = remote.run("ls -la")
print(result)

# Use convenience methods
print(remote.ls("."))      # List directory
print(remote.cat("file.txt"))  # View file
print(remote.uptime())     # View system uptime
```

## 📦 Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd openclaw
```

### 2. Install Dependencies

Rcoder has minimal dependencies, mainly using Python standard libraries:

- Python 3.7+
- Standard libraries: ssl, socket, json, time, asyncio, hashlib, threading, queue

### 3. Configure Server

#### Method A: Use Quick Setup Wizard

```bash
python -m rcoder.cli setup
```

Follow the prompts to enter server information:
- Server name (e.g., my-server)
- Server address (IP or domain)
- Port number (default 443, supports custom)
- Whether to enable HTTPS disguise
- Whether to use a transfer server

#### Method B: Manually Create Configuration File

Create `~/.rcoder/config.json` file:

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

## 🎯 Usage Guide

### Basic Command Execution

```python
from rcoder.utils import get_default_remote

remote = get_default_remote()

# Execute any command
result = remote.run("echo 'Hello Rcoder'")
print(result)

# Wait for restart to complete
result = remote.run("reboot", wait_for_restart=True)
print(result)
```

### Batch Command Execution

```python
commands = [
    "echo 'Command 1'",
    "hostname",
    "date",
    "whoami"
]

results = remote.run_batch(commands)
for cmd, res in results.items():
    print(f"Command: {cmd}")
    print(f"Result: {res}")
    print()
```

### Asynchronous Operations

```python
import asyncio

async def main():
    # Asynchronously execute single command
    result = await remote.run_async("ls -la")
    print(result)
    
    # Asynchronously execute batch commands
    commands = ["echo 1", "echo 2", "echo 3"]
    results = await remote.run_batch_async(commands)
    print(results)

asyncio.run(main())
```

### File Operations

```python
# List directory
print(remote.ls("."))

# View file contents
print(remote.cat("README.md"))

# Create directory
print(remote.mkdir("new_dir"))

# Delete file
print(remote.rm("file.txt"))

# Copy file
print(remote.cp("source.txt", "dest.txt"))

# Move file
print(remote.mv("old.txt", "new.txt"))
```

### System Service Management

```python
# Start service
print(remote.systemctl("start", "nginx"))

# Stop service
print(remote.systemctl("stop", "nginx"))

# Restart service (auto wait for completion)
print(remote.systemctl("restart", "nginx"))

# View service status
print(remote.systemctl("status", "nginx"))
```

### System Information Viewing

```python
# View hostname
print(remote.hostname())

# View system uptime
print(remote.uptime())

# View memory usage
print(remote.free())

# View disk usage
print(remote.df())

# View IP address
print(remote.ip())

# View processes
print(remote.ps())

# View system load
print(remote.top())
```

## 🔧 Advanced Configuration

### HTTPS Disguise Configuration

Set in the configuration file:

```json
{
  "servers": {
    "my-server": {
      "host": "192.168.1.8",
      "port": 8443,  # Custom port
      "use_https_disguise": true,  # Enable HTTPS disguise
      "proxy_server": null
    }
  }
}
```

### Transfer Server Configuration

```json
{
  "servers": {
    "us-server": {
      "host": "us-server.com",
      "port": 443,
      "use_https_disguise": true,
      "proxy_server": ["hk-server.com", 443]  # Transfer through Hong Kong server
    }
  }
}
```

### Key Authentication Configuration

```python
from rcoder.core import get_remote_host

# Get remote host instance
remote = get_remote_host(host='192.168.1.8')

# Start using
print(remote.run("ls -la"))
```

## 📡 Network Configuration

### Public Network Access

For servers with public IP or IPv6 address, you can directly configure:

```json
{
  "servers": {
    "public-server": {
      "host": "your-public-ip",  # Public IP
      "port": 443,               # Or custom port
      "use_https_disguise": true,
      "proxy_server": null
    }
  }
}
```

### Firewall Settings

Ensure the server firewall allows access to the corresponding port:

```bash
# Allow port 443
sudo ufw allow 443/tcp

# Allow custom port (e.g., 8443)
sudo ufw allow 8443/tcp
```

## 🚨 Troubleshooting

### Common Issues

1. **Connection Failed**
   - Check if the server address and port are correct
   - Confirm if the server firewall allows the corresponding port
   - Verify if the network connection is normal

2. **Command Execution Failed**
   - Check if the command is available on the remote server
   - Confirm if user permissions are sufficient
   - View error messages and solve accordingly

3. **HTTPS Disguise Issues**
   - Ensure the port setting is correct
   - Verify if SSL configuration is valid

4. **Transfer Server Issues**
   - Check if the transfer server is accessible
   - Confirm if the transfer server configuration is correct

### Log Viewing

```python
# Enable monitoring
remote.rcoder.start_monitoring()

# View alerts
alerts = remote.rcoder.get_alerts()
for alert in alerts:
    print(f"Alert: {alert}")

# Stop monitoring
remote.rcoder.stop_monitoring()
```

## 📖 Command Line Tool Reference

### Basic Commands

| Command | Description | Example |
|---------|-------------|---------|
| `setup` | Quick setup wizard | `python -m rcoder.cli setup` |
| `run` | Execute command | `python -m rcoder.cli run "ls -la"` |
| `batch` | Execute batch commands | `python -m rcoder.cli batch "echo 1" "echo 2"` |
| `ls` | List directory contents | `python -m rcoder.cli ls /home` |
| `cat` | View file contents | `python -m rcoder.cli cat /etc/hosts` |
| `status` | View system status | `python -m rcoder.cli status` |
| `config` | Configuration management | `python -m rcoder.cli config validate` |

### Configuration Management Commands

| Subcommand | Description | Example |
|------------|-------------|---------|
| `validate` | Validate configuration file | `python -m rcoder.cli config validate` |
| `export` | Export configuration file | `python -m rcoder.cli config export` |
| `import` | Import configuration file | `python -m rcoder.cli config import config.json` |
| `alias` | Create command line alias | `python -m rcoder.cli config alias` |

## 🎨 Usage Tips

### 1. Create Command Line Alias

```bash
# Linux/macOS
echo 'alias rcoder="python -m rcoder.cli"' >> ~/.bashrc
source ~/.bashrc

# Windows (Command Prompt)
doskey rcoder=python -m rcoder.cli $*

# Use alias
rcoder run "ls -la"
```

### 2. Use in Scripts

```python
#!/usr/bin/env python3
"""Automation script example"""

from rcoder.utils import get_default_remote

def main():
    remote = get_default_remote()
    
    # Check system status
    print("=== System Status Check ===")
    print(remote.uptime())
    print(remote.free())
    print(remote.df())
    
    # Execute maintenance tasks
    print("\n=== Executing Maintenance Tasks ===")
    commands = [
        "apt update",
        "apt upgrade -y",
        "apt autoremove -y",
        "apt clean"
    ]
    
    results = remote.run_batch(commands)
    for cmd, res in results.items():
        print(f"Command: {cmd}")
        print(f"Result: {res[:200]}..." if len(res) > 200 else res)
        print()

if __name__ == "__main__":
    main()
```

### 3. Multi-server Management

```python
from rcoder.core import get_remote_host

# Server 1
server1 = get_remote_host(host='server1.com', port=443)

# Server 2 (via transfer)
server2 = get_remote_host(
    host='server2.com', 
    port=443, 
    proxy_server=('hk-proxy.com', 443)
)

# Execute commands respectively
print("Server 1:")
print(server1.run("hostname"))

print("\nServer 2:")
print(server2.run("hostname"))
```

## 📄 Configuration File Structure

```json
{
  "servers": {
    "server-name": {
      "host": "server address",
      "port": port number,
      "use_https_disguise": true/false,
      "proxy_server": ["transfer server address", port number]  // Optional
    }
  },
  "default_server": "default server name",
  "timeout": command timeout (seconds),
  "restart_max_wait": max restart wait time (seconds),
  "monitoring_interval": monitoring interval (seconds)
}
```

## 🔒 Security Best Practices

1. **Use key authentication**: Prioritize public-private key authentication to avoid password transmission
2. **Limit access**: Only allow necessary IP addresses to access the rcoder service
3. **Use HTTPS disguise**: Enable HTTPS disguise feature to enhance network security
4. **Regular updates**: Regularly update rcoder and dependency libraries
5. **Use strong passwords**: If password authentication is required, use strong passwords
6. **Monitor exceptions**: Enable monitoring to detect abnormal situations promptly

## 🆚 Comparison with SSH

| Feature | Rcoder | SSH |
|---------|--------|-----|
| No client required | ✅ | ❌
| HTTPS disguise | ✅ | ❌
| Transfer server | ✅ | ❌
| Batch command execution | ✅ | ⚠️ (requires scripting)
| Asynchronous operations | ✅ | ❌
| Monitoring and alerts | ✅ | ❌
| Local-like usage experience | ✅ | ⚠️ (requires learning SSH commands)
| Cross-platform support | ✅ | ✅
| Security | ✅ | ✅

## 📞 Support

If you encounter issues or have any suggestions, please contact us:

- Project Address: https://github.com/YKaiXu/rcoder
- Documentation: This README file
- Examples: `examples/` directory

## 📝 Version History

- **v1.0.0** - Initial version
  - Core functionality implementation
  - Command line tools
  - Configuration management
  - Documentation improvement

## 📄 License

MIT License

## 🤝 Contribution

Welcome to submit Issues and Pull Requests to improve Rcoder together!

---

**Rcoder - Making remote management simpler!** 🚀