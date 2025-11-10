#!/bin/bash
# 高可用重启服务脚本
# 特性:
# 1. 预检查环境，避免停服后长时间不可用
# 2. 滚动重启，逐个服务停止和启动
# 3. 失败快速回滚，避免全部服务不可用

set -e

# 获取环境参数
ENV=${1:-stage}
echo "==================================="
echo "高可用重启 $ENV 环境服务"
echo "==================================="

# 检查环境参数
if [ "$ENV" != "stage" ] && [ "$ENV" != "prod" ]; then
    echo "错误: 环境参数必须是 stage 或 prod"
    exit 1
fi

# 加载环境配置
SCRIPT_DIR="$(dirname "$0")"
. "$SCRIPT_DIR/env.conf"

# 加载 conda 环境管理
. "$SCRIPT_DIR/conda_manager.sh"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    printf "\033[0;32m[INFO]\033[0m %s\n" "$1"
}

log_warn() {
    printf "\033[1;33m[WARN]\033[0m %s\n" "$1"
}

log_error() {
    printf "\033[0;31m[ERROR]\033[0m %s\n" "$1"
}

log_debug() {
    if [ "$DEBUG" = "1" ]; then
        printf "\033[0;34m[DEBUG]\033[0m %s\n" "$1"
    fi
}

# 健康检查函数
check_service_health() {
    local port=$1
    local max_retries=${2:-30}
    local retry_count=0

    log_debug "健康检查端口 $port (最大重试 $max_retries 次)"

    while [ $retry_count -lt $max_retries ]; do
        if nc -z localhost $port 2>/dev/null; then
            log_debug "端口 $port 已开放"
            if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$port/api/health" 2>/dev/null | grep -q "200\|404"; then
                log_debug "HTTP 健康检查成功"
                return 0
            fi
        fi
        sleep 1
        retry_count=$((retry_count + 1))
    done
    log_error "健康检查失败: 端口 $port 在 $max_retries 秒后仍不可用"
    return 1
}

# 预检查函数
pre_check() {
    log_info "执行预检查..."

    # 检查 Python 版本
    if [ -n "$CONDA_PREFIX" ]; then
        PYTHON_VERSION=$("$CONDA_PREFIX/bin/python" --version 2>&1)
        log_info "Python 版本: $PYTHON_VERSION"
    else
        log_error "Conda 环境未激活"
        return 1
    fi

    # 检查依赖是否最新
    log_info "检查并更新后端依赖..."
    cd "$BASE_DIR/backend"
    "$CONDA_PREFIX/bin/pip" install -q -r requirements.txt --root-user-action=ignore

    # 验证关键 Python 包
    if [ "$ENV" = "prod" ] || [ "$ENV" = "stage" ]; then
        if ! "$CONDA_PREFIX/bin/python" -c "import uvicorn" 2>/dev/null; then
            log_warn "Uvicorn 未安装，尝试安装..."
            "$CONDA_PREFIX/bin/pip" install -q 'uvicorn[standard]'
        fi
    fi
    if ! "$CONDA_PREFIX/bin/python" -c "import fastapi" 2>/dev/null; then
        log_warn "FastAPI 未安装，尝试安装依赖..."
        "$CONDA_PREFIX/bin/pip" install -q -r requirements.txt --root-user-action=ignore
    fi

    # 检查环境配置文件
    ENV_CONFIG_FILE="$BACKEND_DIR/env/$ENV"
    if [ ! -f "$ENV_CONFIG_FILE" ]; then
        log_warn "环境配置文件不存在: $ENV_CONFIG_FILE"
    fi

    # 验证 ASGI 应用文件
    if [ ! -f "$BACKEND_DIR/asgi.py" ]; then
        log_error "找不到 asgi.py 文件在 $BACKEND_DIR"
        return 1
    fi

    # 检查必要目录
    mkdir -p "$BASE_DIR/pid/$ENV"
    mkdir -p "$LOG_DIR/$ENV"

    # 确保日志目录可写
    if [ ! -w "$LOG_DIR/$ENV" ]; then
        log_error "日志目录不可写: $LOG_DIR/$ENV"
        return 1
    fi

    log_info "预检查完成"
    return 0
}

# 获取服务状态
get_service_status() {
    local service_num=$1
    local port=$2
    local pid_file="$BASE_DIR/pid/$ENV/backend_$service_num.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "running"
            return 0
        fi
    fi

    # 通过端口检查
    if lsof -ti :$port >/dev/null 2>&1; then
        echo "running"
        return 0
    fi

    echo "stopped"
    return 1
}

# 停止单个服务
stop_single_service() {
    local service_num=$1
    local port=$2
    local pid_file="$BASE_DIR/pid/$ENV/backend_$service_num.pid"

    log_info "停止服务 #$service_num (端口 $port)..."

    # 尝试优雅停止
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid"

            # 等待优雅关闭
            local wait_count=0
            while [ $wait_count -lt 10 ] && kill -0 "$pid" 2>/dev/null; do
                sleep 1
                wait_count=$((wait_count + 1))
            done

            # 如果还在运行，强制停止
            if kill -0 "$pid" 2>/dev/null; then
                log_warn "优雅停止超时，强制停止进程 $pid"
                kill -9 "$pid"
                sleep 1
            fi
        fi
        rm -f "$pid_file"
    fi

    # 确保端口释放
    local port_pid=$(lsof -ti :$port 2>/dev/null | head -1)
    if [ -n "$port_pid" ]; then
        log_warn "端口 $port 仍被占用 (PID: $port_pid)，强制停止"
        kill -9 "$port_pid" 2>/dev/null || true
    fi

    log_info "服务 #$service_num 已停止"
}

# 启动单个服务
start_single_service() {
    local service_num=$1
    local port=$2
    local pid_file="$BASE_DIR/pid/$ENV/backend_$service_num.pid"

    log_info "启动服务 #$service_num (端口 $port)..."

    # 检查端口是否被占用
    if lsof -ti :$port >/dev/null 2>&1; then
        local existing_pid=$(lsof -ti :$port 2>/dev/null | head -1)
        log_warn "端口 $port 已被进程 $existing_pid 占用"
        if [ -f "$pid_file" ]; then
            local recorded_pid=$(cat "$pid_file")
            if [ "$existing_pid" = "$recorded_pid" ]; then
                log_info "服务 #$service_num 已在运行 (PID: $existing_pid)"
                return 0
            fi
        fi
        log_error "端口 $port 被其他进程占用，请先停止该进程"
        return 1
    fi

    # 设置环境变量
    cd "$BACKEND_DIR"
    export APP_ENV=$ENV
    export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"

    # 根据环境选择启动方式
    local start_command=""
    if [ "$ENV" = "prod" ] || [ "$ENV" = "stage" ]; then
        # 使用 gunicorn + uvicorn.workers.UvicornWorker 获得更好的进程管理
        start_command="$CONDA_PREFIX/bin/gunicorn \
            -w $WORKER_COUNT \
            -k uvicorn.workers.UvicornWorker \
            -b 0.0.0.0:$port \
            --timeout 180 \
            --graceful-timeout 180 \
            --keep-alive 180 \
            asgi:app"
        log_info "使用 Gunicorn + UvicornWorker 启动 (workers=$WORKER_COUNT, timeout=180s)"
    else
        # 开发模式仍使用 uvicorn --reload
        start_command="$CONDA_PREFIX/bin/python -m uvicorn asgi:app \
            --host 0.0.0.0 \
            --port $port \
            --timeout-keep-alive 180 \
            --timeout-graceful-shutdown 180 \
            --reload"
        log_info "使用 Uvicorn 开发模式启动 (timeout=180s)"
    fi

    # 启动服务
    log_debug "执行命令: $start_command"
    APP_ENV=$ENV \
        #nohup $start_command > "$LOG_DIR/$ENV/backend_$service_num.log" 2>&1 &
        nohup $start_command > /dev/null 2>&1 &

    local shell_pid=$!
    log_debug "Shell PID: $shell_pid"

    # 等待服务启动并获取实际 PID
    sleep 2
    local actual_pid=""
    local retry_count=0
    local max_retries=15

    while [ $retry_count -lt $max_retries ]; do
        actual_pid=$(lsof -ti :$port 2>/dev/null | head -1)
        if [ -n "$actual_pid" ]; then
            log_debug "找到实际 PID: $actual_pid"
            break
        fi
        sleep 1
        retry_count=$((retry_count + 1))
    done

    if [ -z "$actual_pid" ]; then
        log_error "无法找到端口 $port 上的进程"
        if [ -f "$LOG_DIR/$ENV/backend_$service_num.log" ]; then
            log_error "启动日志最后几行:"
            tail -n 10 "$LOG_DIR/$ENV/backend_$service_num.log"
        fi
        return 1
    fi

    echo "$actual_pid" > "$pid_file"
    log_info "服务 #$service_num PID 已记录: $actual_pid"

    # 健康检查
    log_info "执行健康检查..."
    if check_service_health $port; then
        log_info "✓ 服务 #$service_num 启动成功 (端口 $port, PID: $actual_pid)"
        return 0
    else
        log_error "✗ 服务 #$service_num 健康检查失败"
        if kill -0 "$actual_pid" 2>/dev/null; then
            log_warn "停止失败的服务进程 $actual_pid"
            kill -9 "$actual_pid" 2>/dev/null || true
        fi
        rm -f "$pid_file"
        return 1
    fi
}

# 批量启动服务
start_all_services() {
    local total_services=$BACKEND_COUNT
    local success_count=0
    local failed_count=0
    local failed_services=""

    log_info "准备启动 $total_services 个后端服务..."

    local i=1
    while [ $i -le $total_services ]; do
        local port
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

        log_info "----------------------------------------"
        log_info "启动服务 $i/$total_services"

        if start_single_service $i $port; then
            success_count=$((success_count + 1))
        else
            failed_count=$((failed_count + 1))
            failed_services="$failed_services $i"
            if [ $i -eq 1 ] && [ $failed_count -eq 1 ]; then
                log_error "第一个服务启动失败，中止启动过程"
                log_error "请检查环境配置和日志文件"
                return 1
            fi
            if [ $failed_count -ge $((total_services / 2 + 1)) ]; then
                log_error "失败服务数量过多 ($failed_count/$total_services)，中止启动"
                break
            fi
        fi

        i=$((i + 1))
    done

    echo ""
    log_info "========================================"
    log_info "启动完成统计:"
    log_info "  总服务数: $total_services"
    log_info "  成功启动: $success_count"
    log_info "  启动失败: $failed_count"
    if [ -n "$failed_services" ]; then
        log_error "  失败服务编号:$failed_services"
    fi
    log_info "========================================"

    if [ $failed_count -gt 0 ]; then
        return 1
    fi
    return 0
}

# 滚动重启服务
rolling_restart() {
    local total_services=$BACKEND_COUNT
    local failed_services=0
    local success_services=0

    log_info "开始滚动重启 $total_services 个服务..."

    # 记录原始服务状态 - 使用临时文件存储，兼容 sh
    local status_file="/tmp/research_chat_service_status_$$"
    > "$status_file"

    local i=1
    while [ $i -le $total_services ]; do
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

        local orig_status=$(get_service_status $i $port || echo "stopped")
        echo "$i:$orig_status" >> "$status_file"
        log_info "服务 #$i 原始状态: $orig_status"
        i=$((i + 1))
    done

    # 逐个重启服务
    i=1
    while [ $i -le $total_services ]; do
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

        log_info "----------------------------------------"
        log_info "重启服务 #$i/$total_services"

        # 从临时文件读取原始状态
        local orig_status=$(grep "^$i:" "$status_file" 2>/dev/null | cut -d: -f2)
        if [ -z "$orig_status" ]; then
            orig_status="stopped"
        fi

        # 如果服务原本就是停止的，只需要启动
        if [ "$orig_status" = "stopped" ]; then
            log_warn "服务 #$i 原本未运行，直接启动"
            if start_single_service $i $port; then
                success_services=$((success_services + 1))
            else
                log_error "服务 #$i 启动失败"
                failed_services=$((failed_services + 1))

                # 如果是第一个服务就失败，中止操作
                if [ $i -eq 1 ]; then
                    log_error "第一个服务启动失败，中止重启操作"
                    rm -f "$status_file"
                    return 1
                fi
            fi
        else
            # 停止服务
            stop_single_service $i $port

            # 短暂等待
            sleep 2

            # 启动服务
            if start_single_service $i $port; then
                success_services=$((success_services + 1))
            else
                log_error "服务 #$i 重启失败"
                failed_services=$((failed_services + 1))

                # 如果是第一个服务就失败，尝试恢复
                if [ $i -eq 1 ]; then
                    log_error "第一个服务重启失败，尝试恢复原服务"
                    # 这里可以添加恢复逻辑
                    log_error "中止重启操作，请检查日志"
                    rm -f "$status_file"
                    return 1
                fi

                # 如果失败率超过50%，停止继续重启
                if [ $failed_services -gt $((total_services / 2)) ]; then
                    log_error "失败服务数超过50%，中止重启操作"
                    rm -f "$status_file"
                    return 1
                fi
            fi
        fi

        i=$((i + 1))
    done

    # 清理临时文件
    rm -f "$status_file"

    # 输出最终结果
    log_info "========================================"
    log_info "滚动重启完成"
    log_info "总服务数: $total_services"
    log_info "成功: $success_services"
    log_info "失败: $failed_services"
    log_info "========================================"

    if [ $failed_services -gt 0 ]; then
        return 1
    fi
    return 0
}

# 快速重启（保留原有逻辑作为备选）
quick_restart() {
    log_info "执行快速重启..."
    if [ -f "$SCRIPT_DIR/stop_services.sh" ]; then
        sh "$SCRIPT_DIR/stop_services.sh" "$ENV"
    fi
    sleep 2
    start_all_services
}

# 显示启动后的服务信息
show_service_info() {
    log_info "服务访问信息:"

    local i=1
    while [ $i -le $BACKEND_COUNT ]; do
        local port
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

        local pid_file="$BASE_DIR/pid/$ENV/backend_$i.pid"
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                echo "  - 服务 #$i: http://localhost:$port/api (PID: $pid)"
            fi
        fi

        i=$((i + 1))
    done

    echo ""
    log_info "日志文件位置: $LOG_DIR/$ENV/"
    log_info "PID 文件位置: $BASE_DIR/pid/$ENV/"
}

# 主函数
main() {
    # 执行预检查
    if ! pre_check; then
        log_error "预检查失败，中止重启"
        exit 1
    fi

    # 检查是否需要快速重启
    if [ "$2" = "--quick" ]; then
        log_warn "使用快速重启模式（可能导致短暂服务中断）"
        quick_restart
    else
        # 默认使用滚动重启
        if ! rolling_restart; then
            log_error "滚动重启失败"

            # 询问是否尝试快速重启
            echo -n "是否尝试快速重启？这可能导致短暂的服务中断 [y/N]: "
            read answer
            if [ "$answer" = "y" ] || [ "$answer" = "Y" ]; then
                quick_restart
            else
                exit 1
            fi
        fi
    fi

    # 显示服务状态
    if [ -f "$SCRIPT_DIR/status.sh" ]; then
        sh "$SCRIPT_DIR/status.sh" "$ENV"
    fi
 }

# 执行主函数
main "$@"