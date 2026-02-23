# rcoder - Remote Server Management & SSH Tunnel Connections

A Python package for remote server management and SSH tunnel connections with advanced features like HTTPS disguise, proxy support, and automatic optimization.

[![Version](https://img.shields.io/badge/version-1.0.5-blue.svg)](https://pypi.org/project/rcoder/)
[![Python](https://img.shields.io/badge/python-3.7+-green.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## ⚠️ Legal Disclaimer & Terms of Use

**IMPORTANT - READ BEFORE USE:**

This software is provided for legitimate system administration, development, and educational purposes only. Users are solely responsible for ensuring compliance with all applicable laws, regulations, and ethical guidelines in their jurisdiction.

### 🔒 Security & Privacy Notice
- **No Hardcoded Credentials**: This package contains no hardcoded passwords, API keys, or authentication tokens
- **User Responsibility**: All authentication credentials must be provided by the user through secure configuration
- **Network Security**: Users must implement appropriate security measures for their network connections
- **Data Protection**: Users are responsible for protecting any data transmitted through this software

### 📋 Terms of Use
1. **Lawful Use Only**: This software may only be used for lawful purposes with proper authorization
2. **No Malicious Activities**: Prohibited from using for unauthorized access, data theft, or any illegal activities
3. **Compliance**: Users must comply with all applicable local, national, and international laws
4. **Authorization**: Users must have explicit permission to access any systems they connect to
5. **Liability**: Developers disclaim all liability for misuse or damages resulting from use of this software

### 🚨 Security Warnings
- **SSH Security**: Always use strong passwords and SSH keys for authentication
- **Network Encryption**: Ensure all connections use proper encryption protocols
- **Access Control**: Implement proper access controls and monitoring
- **Regular Updates**: Keep the software and dependencies updated for security patches

## 🚀 Features

- ✅ **Asynchronous SSH Connections** - Based on asyncssh for stable, long-term sessions
- ✅ **HTTPS Disguise** - Traffic disguised as HTTPS for better connectivity
- ✅ **Proxy Support** - Full support for proxy servers and relay connections
- ✅ **Auto-Optimization** - Intelligent command optimization for different network conditions
- ✅ **Concurrent Operations** - Support for multiple concurrent connections
- ✅ **Error Handling** - Comprehensive error handling and recovery mechanisms
- ✅ **File Transfer** - Secure file upload/download capabilities
- ✅ **Remote Management** - Complete remote server management toolkit

## 📦 Installation

```bash
pip install rcoder==1.0.5
```

## 🔧 Quick Start

### Basic Usage

```python
import asyncio
from rcoder.core import RcoderCore, RemoteHost

async def main():
    # Create Rcoder core instance
    rcoder_core = RcoderCore(
        host="your-server.com",
        port=22,
        use_https_disguise=True,
        proxy_server=("proxy.your-server.com", 443)  # Optional proxy
    )
    
    # Create remote host instance
    remote_host = RemoteHost(rcoder_core, server="my-server")
    
    # Execute commands
    result = remote_host.run("echo 'Hello from rcoder!' && hostname")
    print(f"Result: {result}")
    
    # List files
    files = remote_host.ls("/tmp")
    print(f"Files: {files}")

if __name__ == "__main__":
    asyncio.run(main())
```

### Command Line Interface

```bash
# Basic connection
rcoder connect --host your-server.com --username your-user

# With proxy
rcoder connect --host target-server.com --proxy proxy-server.com --port 443

# Execute command
rcoder exec --host your-server.com --command "ls -la /tmp"
```

## 🎯 Advanced Features

### Network Optimization

```python
from rcoder.auto_optimizer import AutoOptimizer

# Create optimizer for low bandwidth scenarios
optimizer = AutoOptimizer()

# Optimize commands for current network conditions
optimized_cmd = optimizer.optimize_command("ls -la /tmp/")
print(f"Optimized: {optimized_cmd}")
```

### Concurrent Operations

```python
import asyncio
from rcoder.async_proxy import AsyncProxyManager

async def concurrent_tasks():
    # Create proxy manager for multiple connections
    proxy_manager = AsyncProxyManager(remote_host)
    
    # Execute multiple tasks concurrently
    tasks = [
        proxy_manager.execute_async("task1", "uptime"),
        proxy_manager.execute_async("task2", "df -h"),
        proxy_manager.execute_async("task3", "free -m")
    ]
    
    results = await asyncio.gather(*tasks)
    return results
```

## 🔒 Security Features

- **No Hardcoded Credentials**: All authentication is user-provided
- **SSL/TLS Encryption**: All connections use proper encryption
- **Input Validation**: Comprehensive input validation and sanitization
- **Error Handling**: Secure error handling without information leakage
- **Connection Pooling**: Efficient connection management with security

## 📋 Configuration Options

### Connection Configuration

```python
config = {
    "host": "your-server.com",
    "port": 22,  # or 443 for HTTPS disguise
    "username": "your-username",
    "use_https_disguise": True,
    "proxy_server": ("proxy-host", 443),
    "timeout": 30,
    "retry_attempts": 3
}
```

### Network Optimization

```python
optimizer_config = {
    "scenario": "low_bandwidth",  # or "high_latency", "unstable_network"
    "enable_compression": True,
    "max_output_lines": 1000,
    "timeout_multiplier": 1.5
}
```

## 🚨 Important Security Notes

1. **Always use strong passwords or SSH keys**
2. **Configure proper firewall rules**
3. **Monitor connection logs regularly**
4. **Keep software and dependencies updated**
5. **Use VPN or secure networks when possible**
6. **Implement proper access controls**

## 🛠️ Development

### Setup Development Environment

```bash
git clone https://github.com/YKaiXu/rcoder.git
cd rcoder
pip install -r requirements.txt
pip install -e .
```

### Running Tests

```bash
python -m pytest tests/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚖️ Legal Compliance

By using this software, you acknowledge and agree to:

1. **Full Responsibility**: You are solely responsible for lawful use and compliance
2. **No Liability**: Developers disclaim all liability for misuse or damages
3. **Indemnification**: You agree to indemnify developers against any claims
4. **Jurisdiction**: Usage is subject to your local laws and regulations

## 🆘 Support & Issues

- **GitHub Issues**: [Report Issues](https://github.com/YKaiXu/rcoder/issues)
- **Security Issues**: Please report security vulnerabilities privately
- **Documentation**: See inline documentation and examples

---

**⚠️ Final Warning**: This software is powerful and must be used responsibly. Unauthorized access to computer systems is illegal and unethical. Always ensure you have explicit permission before accessing any system.