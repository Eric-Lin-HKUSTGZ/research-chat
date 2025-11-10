#!/bin/sh
# 重启所有服务

set -e

# 获取环境参数
ENV=${1:-stage}
echo "重启 $ENV 环境服务..."

# 检查环境参数
if [ "$ENV" != "stage" ] && [ "$ENV" != "prod" ]; then
    echo "错误: 环境参数必须是 stage 或 prod"
    exit 1
fi

# 加载环境配置
. "$(dirname "$0")/env.conf"

echo "重启 $ENV 环境服务..."

# 停止服务
sh "$(dirname "$0")/stop_services.sh" "$ENV"

# 等待一下
sleep 2

# 启动服务
sh "$(dirname "$0")/start_services.sh" "$ENV"

echo "服务重启完成！"



