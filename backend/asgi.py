"""
ASGI Application Entry Point
FastAPI 应用入口
"""
import os
import sys
from dotenv import load_dotenv

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

# Load environment variables from env/{APP_ENV} file
base_dir = os.path.dirname(__file__)
env_file = os.getenv('ENV_FILE')

if env_file:
    if not os.path.isabs(env_file):
        env_file = os.path.join(base_dir, env_file)
else:
    app_env = os.getenv('APP_ENV', 'dev')
    candidate = os.path.join(base_dir, 'env', app_env)
    if os.path.exists(candidate):
        env_file = candidate
    else:
        env_file = os.path.join(base_dir, 'env', 'dev')

# Load environment variables
load_dotenv(env_file)
print(f"[ASGI] Loaded environment from: {env_file}")

from app.main import app

__all__ = ["app"]
