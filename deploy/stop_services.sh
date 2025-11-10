#!/bin/sh
# 停止所有服务

# 获取环境参数
ENV=${1:-stage}
echo "停止 $ENV 环境服务..."

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

# 停止后端服务
echo "停止后端服务..."
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
            port=$((BACKEND_START_PORT_STAGE + i - 1))  # 默认使用 stage 端口
            ;;
    esac
    pid_file="$BASE_DIR/pid/$ENV/backend_$i.pid"
    
    echo "停止后端服务 $i (端口 $port)..."
    
    if [ -f "$pid_file" ]; then
        pid=$(cat "$pid_file")
        echo "  PID 文件记录的进程号: $pid"
        
        if kill -0 "$pid" 2>/dev/null; then
            echo "  进程 $pid 存在，尝试停止..."
            kill "$pid"
            sleep 2
            
            if kill -0 "$pid" 2>/dev/null; then
                echo "  进程仍在运行，强制停止..."
                kill -9 "$pid"
                sleep 1
            fi
            
            if ! kill -0 "$pid" 2>/dev/null; then
                echo "  进程 $pid 已停止"
            else
                echo "  警告: 进程 $pid 仍无法停止"
            fi
        else
            echo "  PID $pid 对应的进程不存在，尝试智能查找..."
            
            # 智能查找相关 python 进程
            if [ -n "$BACKEND_DIR" ]; then
                smart_pids=$(ps aux | grep -E "python.*$BACKEND_DIR" | grep -v grep | awk '{print $2}' 2>/dev/null || true)
                
                if [ -n "$smart_pids" ]; then
                    echo "  发现相关 python 进程: $smart_pids"
                    
                    for smart_pid in $smart_pids; do
                        echo "    停止相关进程 $smart_pid..."
                        kill "$smart_pid"
                        sleep 2
                        
                        if kill -0 "$smart_pid" 2>/dev/null; then
                            echo "      进程仍在运行，强制停止..."
                            kill -9 "$smart_pid"
                            sleep 1
                        fi
                        
                        if ! kill -0 "$smart_pid" 2>/dev/null; then
                            echo "      进程 $smart_pid 已停止"
                        else
                            echo "      警告: 进程 $smart_pid 仍无法停止"
                        fi
                    done
                else
                    echo "  未发现相关 python 进程"
                fi
            fi
        fi
        
        rm -f "$pid_file"
    else
        echo "  PID 文件不存在，尝试智能查找..."
        
        # 智能查找相关 python 进程
        if [ -n "$BACKEND_DIR" ]; then
            smart_pids=$(ps aux | grep -E "python.*$BACKEND_DIR" | grep -v grep | awk '{print $2}' 2>/dev/null || true)
            
            if [ -n "$smart_pids" ]; then
                echo "  发现相关 python 进程: $smart_pids"
                
                for smart_pid in $smart_pids; do
                    echo "    停止相关进程 $smart_pid..."
                    kill "$smart_pid"
                    sleep 1
                    
                    if kill -0 "$smart_pid" 2>/dev/null; then
                        echo "      进程仍在运行，强制停止..."
                        kill -9 "$smart_pid"
                        sleep 1
                    fi
                    
                    if ! kill -0 "$smart_pid" 2>/dev/null; then
                        echo "      进程 $smart_pid 已停止"
                    else
                        echo "      警告: 进程 $smart_pid 仍无法停止"
                    fi
                done
            else
                echo "  未发现相关 python 进程"
            fi
        fi
    fi
    
    i=$((i + 1))
done

echo "所有服务已停止！"