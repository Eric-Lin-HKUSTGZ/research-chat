#!/bin/sh
# Conda 环境管理脚本

# 检查 conda 是否安装
if ! command -v conda >/dev/null 2>&1; then
    echo "错误: conda 未安装或不在 PATH 中"
    exit 1
fi

# 初始化 conda
eval "$(conda shell.bash hook)"

# 设置 conda 环境名称
CONDA_ENV_NAME=${CONDA_ENV_NAME:-"312_research_chat"}
CONDA_PYTHON_VERSION=${CONDA_PYTHON_VERSION:-"3.12"}

# 检查环境是否存在
if conda env list | grep -q "^$CONDA_ENV_NAME "; then
    echo "Conda 环境 $CONDA_ENV_NAME 已存在"
else
    echo "创建 Conda 环境 $CONDA_ENV_NAME..."
    conda create -n "$CONDA_ENV_NAME" python="$CONDA_PYTHON_VERSION" -y
fi

# 激活环境
echo "激活 Conda 环境 $CONDA_ENV_NAME..."
conda activate "$CONDA_ENV_NAME"

# 设置 CONDA_PREFIX 变量
export CONDA_PREFIX="$CONDA_PREFIX"

echo "Conda 环境管理完成"
echo "环境名称: $CONDA_ENV_NAME"
echo "Python 版本: $CONDA_PYTHON_VERSION"
echo "环境路径: $CONDA_PREFIX"



