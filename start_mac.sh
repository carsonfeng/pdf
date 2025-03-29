#!/bin/bash

# 创建虚拟环境（如果不存在）
if [ ! -d "venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 创建上传目录
mkdir -p app/uploads
mkdir -p logs

# 运行应用
echo "启动应用..."
export FLASK_APP=run.py
export FLASK_ENV=development
flask run --host=0.0.0.0 --port=5001 