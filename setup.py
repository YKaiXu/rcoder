from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="rcoder",
    version="2.0.2",
    author="YuKaiXu",
    author_email="yukaixu@outlook.com",
    description="Remote server management and SSH tunnel connections with HTTPS disguise",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/YKaiXu/rcoder",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Networking",
        "Topic :: System :: Systems Administration",
    ],
    python_requires=">=3.7",
    install_requires=[
        "asyncssh>=2.14.0",
        "cryptography>=41.0.0",
        "psutil>=5.9.8",
        "python-daemon>=3.0.1",
        "requests>=2.31.0",
        "websockets>=11.0.3",
        "aiofiles>=23.2.1",
        "aiohttp>=3.8.6",
        "paramiko>=3.3.1",
        "asyncio-mqtt>=0.16.1",
        "jsonrpc-base>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "rcoder=rcoder.cli:main",
            "rcoder-cli=rcoder.cli_enhanced:main",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)