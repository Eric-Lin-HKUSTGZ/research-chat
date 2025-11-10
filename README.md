# 科研智能体项目说明

## 项目概述

科研智能体是一个基于大语言模型的创新方案生成系统，能够根据用户的研究主题自动生成完整的研究方案。

## 功能特性

- 🤖 **智能意图识别**: 自动识别用户输入是科研请求还是普通聊天
- 🧠 **创新方案生成**: 基于研究主题生成包含5个部分的完整创新方案
- 💬 **多轮对话支持**: 支持历史对话管理和多轮交互
- 📊 **实时进程监控**: 实时显示方案生成进度和状态
- 🔐 **安全认证**: 基于Token的API认证机制

## 技术架构

### 前端技术栈
- **React 18**: 现代化前端框架
- **TypeScript**: 类型安全的JavaScript
- **Vite**: 快速构建工具
- **Axios**: HTTP客户端

### 后端技术栈
- **FastAPI**: 高性能Python Web框架
- **SQLAlchemy**: Python ORM
- **MySQL**: 关系型数据库
- **httpx**: 异步HTTP客户端

### 部署技术
- **Docker**: 容器化部署
- **Gunicorn**: WSGI服务器
- **Nginx**: 反向代理（可选）

## 项目结构

```
research_chat/
├── frontend_demo/          # 前端代码
│   ├── src/               # React 源码
│   │   ├── api/           # API 客户端
│   │   ├── pages/         # 页面组件
│   │   └── App.tsx        # 主应用组件
│   ├── package.json       # 前端依赖
│   └── vite.config.ts     # Vite 配置
├── backend/               # 后端代码
│   ├── app/              # FastAPI 应用
│   │   ├── routes/       # API 路由
│   │   ├── services/     # 业务逻辑
│   │   ├── utils/        # 工具函数
│   │   └── config.py     # 配置管理
│   ├── env/              # 环境配置
│   ├── database/         # 数据库脚本
│   └── requirements.txt  # Python 依赖
└── deploy/               # 部署脚本
    ├── deploy.sh         # 一键部署
    └── *.sh             # 服务管理脚本
```

## 快速开始

### 1. 环境准备

```bash
# 安装 Node.js (前端)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
nvm install 18
nvm use 18

# 安装 Python 3.12 (后端)
conda create -n research_chat python=3.12
conda activate research_chat
```

### 2. 数据库设置

```bash
# 创建数据库
mysql -u root -p
CREATE DATABASE sci_agent_academic CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

# 导入表结构
mysql -u root -p sci_agent_academic < backend/database/schema.sql
```

### 3. 开发环境启动

```bash
# 启动后端
cd backend
pip install -r requirements.txt
chmod +x start_dev.sh
./start_dev.sh

# 启动前端（新终端）
cd frontend_demo
npm install
chmod +x start_dev.sh
./start_dev.sh
```

### 4. 生产环境部署

```bash
# 一键部署
chmod +x deploy/*.sh
./deploy/deploy.sh stage
```

## API 文档

### 认证
所有API请求需要在Header中包含认证Token:
```
Authorization: Bearer demo_token
```

### 主要端点

#### 创建研究请求
```http
POST /research_chat/api/lit-research/create
Content-Type: application/json
Authorization: Bearer demo_token

{
  "content": "基于深度学习的图像分类算法优化",
  "session_id": "optional_session_id"
}
```

#### 获取会话列表
```http
GET /research_chat/api/lit-research/sessions
Authorization: Bearer demo_token
```

#### 获取会话消息
```http
GET /research_chat/api/lit-research/sessions/{session_id}/messages
Authorization: Bearer demo_token
```

#### 获取会话进程
```http
GET /research_chat/api/lit-research/sessions/{session_id}/processes?latest=true
Authorization: Bearer demo_token
```

## 配置说明

### 环境变量

#### 后端配置
- `DATABASE_URL`: 数据库连接字符串
- `LLM_API_ENDPOINT`: LLM服务端点
- `LLM_API_KEY`: LLM服务密钥
- `APP_ENV`: 应用环境 (dev/stage/prod)

#### 前端配置
- `VITE_API_BASE_URL`: API基础URL
- `VITE_APP_TITLE`: 应用标题

### 端口配置
- 开发环境: 后端 5000, 前端 5173
- 测试环境: 后端 5011-5012
- 生产环境: 后端 5001-5002

## 功能详解

### 创新方案生成

系统会根据用户输入的研究主题，生成包含以下5个部分的完整创新方案：

1. **方案名称**: 中英文名称
2. **研究领域背景**: 领域发展历程和重要性
3. **现有方法缺点**: 问题分析和针对性解决方案
4. **方案具体细节**: 技术架构和实验流程
5. **方案总结**: 创新性和优势总结

### 对话管理

- **新建对话**: 创建新的研究会话
- **历史对话**: 查看和管理历史会话
- **会话重命名**: 自定义会话名称
- **会话删除**: 清理不需要的会话

### 实时监控

- **进程状态**: 实时显示方案生成进度
- **日志输出**: 详细的执行日志
- **状态更新**: 自动更新处理状态

## 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   lsof -ti :5001
   kill -9 <PID>
   ```

2. **数据库连接失败**
   - 检查MySQL服务状态
   - 验证连接字符串
   - 确认用户权限

3. **前端无法连接后端**
   - 检查后端服务状态
   - 验证代理配置
   - 检查CORS设置

4. **LLM服务调用失败**
   - 检查网络连接
   - 验证API密钥
   - 查看服务状态

### 日志查看

```bash
# 查看应用日志
tail -f research_api.log

# 查看系统日志
journalctl -u research_chat -f
```

## 性能优化

### 后端优化
- 调整Gunicorn worker数量
- 配置数据库连接池
- 启用缓存机制
- 优化数据库查询

### 前端优化
- 启用代码分割
- 配置资源压缩
- 优化图片加载
- 使用CDN加速

## 安全考虑

- **API认证**: 基于Token的认证机制
- **输入验证**: 严格的输入参数验证
- **SQL注入防护**: 使用ORM防止SQL注入
- **CORS配置**: 合理的跨域资源共享设置
- **日志安全**: 避免敏感信息泄露

## 扩展功能

### 计划中的功能
- [ ] 用户管理系统
- [ ] 方案模板库
- [ ] 协作功能
- [ ] 导出功能
- [ ] 移动端支持

### 自定义开发
- 添加新的LLM提供商
- 扩展方案生成模板
- 集成外部数据源
- 添加分析功能

## 贡献指南

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 许可证

MIT License

## 联系方式

如有问题或建议，请通过以下方式联系：
- 邮箱: your-email@example.com
- 项目地址: https://github.com/your-username/research_chat
