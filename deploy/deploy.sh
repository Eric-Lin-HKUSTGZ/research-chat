#!/bin/sh
# 一键部署脚本

set -e

ENV=${1:-stage}
echo "部署 $ENV 环境..."

# 检查环境参数
if [ "$ENV" != "stage" ] && [ "$ENV" != "prod" ]; then
    echo "错误: 环境参数必须是 stage 或 prod"
    exit 1
fi

# 加载环境配置
echo "$(dirname "$0")/env.conf"
. "$(dirname "$0")/env.conf"

# 设置环境变量
export ENV=$ENV

# 创建必要目录
echo "创建目录结构..."
mkdir -p $FRONTEND_DEMO_DIR
mkdir -p $BACKEND_DIR
mkdir -p $DEPLOY_DIR
mkdir -p $PID_DIR
mkdir -p $PID_DIR/$ENV
mkdir -p $LOG_DIR

# 复制代码
echo "复制代码..."
echo "复制前端代码 frontend_demo..."
rm -rf "$FRONTEND_DEMO_DIR/"
rsync -av --exclude='node_modules' "$SYSTEM_NAME/frontend_demo/" "$FRONTEND_DEMO_DIR/"
echo "复制后端代码..."
rm -rf "$BACKEND_DIR/"
cp -r "$SYSTEM_NAME/backend/" "$BACKEND_DIR/"
echo "复制部署脚本..."
rm -rf "$DEPLOY_DIR/"
cp -r "$SYSTEM_NAME/deploy/" "$DEPLOY_DIR/"

# 设置执行权限
echo "设置脚本执行权限..."
chmod +x "$DEPLOY_DIR/"*.sh || true

# 启动服务
echo "启动服务..."
bash "$DEPLOY_DIR/start_services.sh" "$ENV"

echo "部署完成！"