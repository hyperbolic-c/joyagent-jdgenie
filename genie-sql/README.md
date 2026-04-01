# Genie SQL

`python >= 3.11`

## 项目结构

```
.
├── genie_sql
│   ├── api                             # api 服务
│   ├── model                           # 协议和 DataClass
│   ├── prompt                          # Prompt 仓库
│   ├── tool                            # nl2sql 执行逻辑
│   └── util                            # 工具类
├── .env_template                       # 环境变量
├── server.py                           # FastAPI 服务启动
└── start.sh                            # 启动脚本

```

## 项目启动

python 环境和依赖安装  
```bash
pip install uv
cd genie-sql
uv sync
source .venv/bin/activate
```

启动服务
```bash

cd genie-sql

cp .env_template .env
# 填写环境变量

uv run python server.py
```
