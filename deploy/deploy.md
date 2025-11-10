# 科研智能体部署说明

## 项目结构

```
research_chat/
├── frontend_demo/          # 前端代码
│   ├── src/               # React 源码
│   ├── package.json       # 前端依赖
│   ├── vite.config.ts     # Vite 配置
│   └── start_dev.sh       # 前端开发启动脚本
├── backend/               # 后端代码
│   ├── app/              # FastAPI 应用
│   │   ├── routes/       # API 路由
│   │   ├── services/     # 业务逻辑
│   │   ├── utils/        # 工具函数
│   │   └── config.py     # 配置管理
│   ├── env/              # 环境配置
│   │   ├── dev           # 开发环境
│   │   ├── stage         # 测试环境
│   │   └── prod          # 生产环境
│   ├── database/         # 数据库脚本
│   ├── requirements.txt  # Python 依赖
│   ├── wsgi.py          # WSGI 入口
│   └── start_dev.sh     # 后端开发启动脚本
└── deploy/               # 部署脚本
    ├── deploy.sh         # 一键部署
    ├── start_services.sh # 启动服务
    ├── stop_services.sh  # 停止服务
    ├── restart_services.sh # 重启服务
    ├── status.sh         # 检查状态
    ├── conda_manager.sh  # Conda 环境管理
    └── env.conf          # 环境配置
```

## 部署步骤

### 1. 开发环境部署

```bash
# 启动后端服务
cd research_chat/backend
chmod +x start_dev.sh
./start_dev.sh

# 启动前端服务（新终端）
cd research_chat/frontend_demo
npm install
chmod +x start_dev.sh
./start_dev.sh
```

### 2. 生产环境部署

```bash
# 一键部署
cd research_chat
chmod +x deploy/*.sh
./deploy/deploy.sh stage  # 或 prod
```

### 3. 服务管理

```bash
# 检查服务状态
./deploy/status.sh stage

# 重启服务
./deploy/restart_services.sh stage

# 停止服务
./deploy/stop_services.sh stage
```

## 环境配置

### 端口配置
- 开发环境: 后端 5000, 前端 5173
- 测试环境: 后端 5011-5012, 前端 5173
- 生产环境: 后端 5001-5002, 前端 5173

### 数据库配置
- 数据库: MySQL
- 连接字符串: `mysql+aiomysql://user:password@host:port/database`

### LLM 服务配置
- API 端点: `http://35.220.164.252:3888/v1`
- 模型: `deepseek-ai/DeepSeek-V3`

## API 端点

### 认证
所有 API 请求需要在 Header 中包含:
```
Authorization: Bearer demo_token
```

### 主要端点
- `POST /research_chat/api/lit-research/create` - 创建研究请求
- `GET /research_chat/api/lit-research/sessions` - 获取会话列表
- `GET /research_chat/api/lit-research/sessions/{session_id}/messages` - 获取会话消息
- `GET /research_chat/api/lit-research/sessions/{session_id}/processes` - 获取会话进程
- `PUT /research_chat/api/lit-research/sessions/{session_id}/name` - 更新会话名称
- `DELETE /research_chat/api/lit-research/sessions/{session_id}` - 删除会话

## 日志管理

- 日志文件: `research_api.log`
- 日志级别: INFO (开发), WARNING (生产)
- 日志格式: `时间 - 模块 - 级别 - 消息`

## 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   lsof -ti :5001  # 检查端口占用
   kill -9 <PID>   # 杀死进程
   ```

2. **数据库连接失败**
   - 检查数据库服务是否运行
   - 验证连接字符串配置
   - 确认数据库用户权限

3. **前端无法连接后端**
   - 检查后端服务是否启动
   - 验证代理配置
   - 检查 CORS 设置

4. **Conda 环境问题**
   ```bash
   conda env list                    # 查看环境列表
   conda activate 312_research_chat  # 激活环境
   conda install python=3.12        # 安装 Python
   ```

### 性能优化

1. **后端优化**
   - 调整 Gunicorn worker 数量
   - 配置数据库连接池
   - 启用缓存机制

2. **前端优化**
   - 启用代码分割
   - 配置 CDN
   - 优化资源加载

## 监控和维护

### 健康检查
```bash
curl http://localhost:5001/health
```

### 日志监控
```bash
tail -f research_api.log
```

### 数据库维护
```bash
# 备份数据库
mysqldump -u user -p sci_agent_academic > backup.sql

# 恢复数据库
mysql -u user -p sci_agent_academic < backup.sql
```



