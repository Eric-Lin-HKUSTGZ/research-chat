#!/bin/sh
# 简化部署脚本 - 避免权限问题

set -e

ENV=${1:-stage}
echo "简化部署 $ENV 环境..."

# 加载环境配置
. "$(dirname "$0")/env.conf"

# 设置环境变量
export ENV=$ENV

# 创建本地部署目录
LOCAL_DEPLOY_DIR="./deploy_local"
mkdir -p "$LOCAL_DEPLOY_DIR"

# 复制代码到本地目录
echo "复制代码到本地目录..."
rm -rf "$LOCAL_DEPLOY_DIR/*"
cp -r backend/* "$LOCAL_DEPLOY_DIR/"
cp -r frontend_demo "$LOCAL_DEPLOY_DIR/"

# 设置执行权限
chmod +x "$LOCAL_DEPLOY_DIR/"*.sh 2>/dev/null || true

# 启动服务
echo "启动 $ENV 环境服务..."
cd "$LOCAL_DEPLOY_DIR"

# 使用本地Python环境
PYTHON_CMD="python3"
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo "错误: 找不到Python解释器"
    exit 1
fi

echo "使用Python: $PYTHON_CMD"

# 安装依赖
echo "安装依赖..."
$PYTHON_CMD -m pip install -r requirements.txt

# 启动后端服务
echo "启动后端服务..."
APP_ENV=$ENV $PYTHON_CMD wsgi.py &

echo "部署完成！"
echo "后端服务运行在: http://localhost:5000"
echo "API端点: http://localhost:5000/research_chat/api/"
echo ""
echo "要停止服务，请按 Ctrl+C 或运行: pkill -f wsgi.py"
