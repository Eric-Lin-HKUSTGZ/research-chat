#!/bin/sh
# 检查服务状态

set -e

# 获取环境参数
ENV=${1:-stage}
echo "检查 $ENV 环境服务状态..."

# 检查环境参数
if [ "$ENV" != "stage" ] && [ "$ENV" != "prod" ]; then
    echo "错误: 环境参数必须是 stage 或 prod"
    exit 1
fi

# 加载环境配置
. "$(dirname "$0")/env.conf"

echo "检查 $ENV 环境服务状态..."

# 检查后端服务
echo "后端服务状态:"
i=1
while [ $i -le $BACKEND_COUNT ]; do
    # 根据环境选择端口
    case $ENV in
        stage)
            port=$((BACKEND_START_PORT_STAGE + i - 1))
            ;;
        prod)
            port=$((BACKEND_START_PORT_PROD + i - 1))
            ;;
        *)
            port=$((BACKEND_START_PORT_STAGE + i - 1))
            ;;
    esac
    
    pid_file="$BASE_DIR/pid/$ENV/backend_$i.pid"
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "  后端服务 $i: 运行中 (PID: $pid, 端口: $port)"
        else
            echo "  后端服务 $i: 已停止 (PID文件存在但进程不存在)"
        fi
    else
        echo "  后端服务 $i: 未运行 (PID文件不存在)"
    fi
    
    # 检查端口是否被占用
    if lsof -ti :$port >/dev/null 2>&1; then
        echo "    端口 $port: 被占用"
    else
        echo "    端口 $port: 空闲"
    fi
    
    i=$((i + 1))
done

echo "服务状态检查完成！"



