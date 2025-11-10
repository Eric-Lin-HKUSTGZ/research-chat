# 科研智能体后端API文档

## 概述

科研智能体后端服务提供基于大语言模型的创新方案生成API，支持多轮对话、会话管理和实时进程监控。

## 基础信息

- **服务名称**: 科研智能体后端服务
- **版本**: 1.0.0
- **基础URL**: `http://localhost:5001`
- **API前缀**: `/research_chat/api`

## 认证

所有API请求需要在Header中包含认证Token:

```http
Authorization: Bearer demo_token
```

### 有效Token
- `demo_token`: 演示用户
- `research_token_001`: 研究用户1
- `research_token_002`: 研究用户2

## API端点

### 1. 创建研究请求

创建新的研究请求，系统将自动生成创新方案。

**请求**
```http
POST /research_chat/api/lit-research/create
Content-Type: application/json
Authorization: Bearer demo_token

{
  "content": "基于深度学习的图像分类算法优化",
  "session_id": "optional_session_id"
}
```

**参数**
- `content` (string, required): 研究主题或问题，最大长度300字符
- `session_id` (string, optional): 会话ID，如果不提供将创建新会话

**响应**
```json
{
  "code": 200,
  "message": "研究请求已创建",
  "data": {
    "message_id": 123,
    "session_id": "session_uuid"
  }
}
```

### 2. 获取会话列表

获取用户的所有研究会话。

**请求**
```http
GET /research_chat/api/lit-research/sessions?page=1&size=10
Authorization: Bearer demo_token
```

**参数**
- `page` (int, optional): 页码，从1开始
- `size` (int, optional): 每页大小

**响应**
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "id": 1,
      "conversation_id": "session_uuid",
      "conversation_name": "深度学习研究",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z"
    }
  ]
}
```

**分页响应**
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "sessions": [...],
    "pagination": {
      "page": 1,
      "size": 10,
      "total": 25,
      "pages": 3
    }
  }
}
```

### 3. 获取会话消息

获取指定会话的所有消息。

**请求**
```http
GET /research_chat/api/lit-research/sessions/{session_id}/messages?latest=true
Authorization: Bearer demo_token
```

**参数**
- `session_id` (string, required): 会话ID
- `latest` (bool, optional): 是否只获取最新消息
- `page` (int, optional): 页码
- `size` (int, optional): 每页大小

**响应**
```json
{
  "code": 200,
  "message": "成功",
  "data": [
    {
      "id": 1,
      "question": "基于深度学习的图像分类算法优化",
      "answer": {
        "response": "## 创新方案生成完成\n\n**研究主题**: 基于深度学习的图像分类算法优化\n..."
      },
      "question_timestamp": "2024-01-01T00:00:00Z",
      "answer_timestamp": "2024-01-01T00:01:00Z"
    }
  ]
}
```

### 4. 获取会话进程

获取指定会话的研究进程信息。

**请求**
```http
GET /research_chat/api/lit-research/sessions/{session_id}/processes?latest=true
Authorization: Bearer demo_token
```

**参数**
- `session_id` (string, required): 会话ID
- `latest` (bool, optional): 是否只获取最新进程
- `page` (int, optional): 页码
- `size` (int, optional): 每页大小

**响应**
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "id": 1,
    "conversation_id": "session_uuid",
    "message_id": 123,
    "user_id": "demo_user",
    "email": "demo_user@research.com",
    "process_info": {
      "logs": [
        "[2024-01-01 00:00:00] 🚀 开始处理研究请求",
        "[2024-01-01 00:00:01] 🔍 正在分析用户意图...",
        "[2024-01-01 00:00:02] ✅ 检测到科研请求，主题: 深度学习图像分类"
      ]
    },
    "extra_info": {},
    "creation_status": "created",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:01:00Z"
  }
}
```

### 5. 更新会话名称

更新指定会话的名称。

**请求**
```http
PUT /research_chat/api/lit-research/sessions/{session_id}/name
Content-Type: application/json
Authorization: Bearer demo_token

{
  "conversation_name": "新的会话名称"
}
```

**参数**
- `session_id` (string, required): 会话ID
- `conversation_name` (string, required): 新的会话名称，1-255字符

**响应**
```json
{
  "code": 200,
  "message": "会话名称更新成功",
  "data": null
}
```

### 6. 删除会话

删除指定的会话及其所有相关数据。

**请求**
```http
DELETE /research_chat/api/lit-research/sessions/{session_id}
Authorization: Bearer demo_token
```

**参数**
- `session_id` (string, required): 会话ID

**响应**
```json
{
  "code": 200,
  "message": "会话删除成功",
  "data": {
    "session_id": "session_uuid"
  }
}
```

### 7. 获取消息详情

获取指定消息的详细信息及其关联进程。

**请求**
```http
GET /research_chat/api/lit-research/messages/{message_id}
Authorization: Bearer demo_token
```

**参数**
- `message_id` (int, required): 消息ID

**响应**
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "message": {
      "id": 123,
      "conversation_id": "session_uuid",
      "role": "user",
      "content": "基于深度学习的图像分类算法优化",
      "created_at": "2024-01-01T00:00:00Z"
    },
    "processes": [
      {
        "id": 1,
        "conversation_id": "session_uuid",
        "message_id": 123,
        "user_id": "demo_user",
        "email": "demo_user@research.com",
        "process_info": {...},
        "creation_status": "created",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:01:00Z"
      }
    ]
  }
}
```

### 8. 获取进程详情

获取指定进程的详细信息。

**请求**
```http
GET /research_chat/api/lit-research/processes/{process_id}
Authorization: Bearer demo_token
```

**参数**
- `process_id` (int, required): 进程ID

**响应**
```json
{
  "code": 200,
  "message": "成功",
  "data": {
    "id": 1,
    "conversation_id": "session_uuid",
    "message_id": 123,
    "user_id": "demo_user",
    "email": "demo_user@research.com",
    "process_info": {
      "logs": [...]
    },
    "extra_info": {},
    "creation_status": "created",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:01:00Z"
  }
}
```

## 状态码

### HTTP状态码
- `200`: 成功
- `401`: 未授权（Token无效）
- `404`: 资源不存在
- `422`: 参数验证失败
- `500`: 服务器内部错误

### 进程状态
- `pending`: 等待处理
- `creating`: 正在处理
- `created`: 处理完成
- `failed`: 处理失败

## 错误响应

### 认证错误
```json
{
  "detail": "无效的认证令牌"
}
```

### 参数验证错误
```json
{
  "detail": [
    {
      "loc": ["body", "content"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 资源不存在
```json
{
  "detail": "会话不存在或无权限访问"
}
```

## 使用示例

### JavaScript/TypeScript

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:5001/research_chat/api',
  headers: {
    'Authorization': 'Bearer demo_token',
    'Content-Type': 'application/json'
  }
});

// 创建研究请求
const createResearch = async (content: string) => {
  const response = await api.post('/lit-research/create', { content });
  return response.data;
};

// 获取会话列表
const getSessions = async () => {
  const response = await api.get('/lit-research/sessions');
  return response.data;
};

// 获取会话消息
const getMessages = async (sessionId: string) => {
  const response = await api.get(`/lit-research/sessions/${sessionId}/messages`);
  return response.data;
};

// 监控进程状态
const monitorProcess = async (sessionId: string) => {
  const response = await api.get(`/lit-research/sessions/${sessionId}/processes?latest=true`);
  return response.data;
};
```

### Python

```python
import requests

API_BASE = "http://localhost:5001/research_chat/api"
HEADERS = {
    "Authorization": "Bearer demo_token",
    "Content-Type": "application/json"
}

# 创建研究请求
def create_research(content: str):
    response = requests.post(
        f"{API_BASE}/lit-research/create",
        headers=HEADERS,
        json={"content": content}
    )
    return response.json()

# 获取会话列表
def get_sessions():
    response = requests.get(
        f"{API_BASE}/lit-research/sessions",
        headers=HEADERS
    )
    return response.json()

# 获取会话消息
def get_messages(session_id: str):
    response = requests.get(
        f"{API_BASE}/lit-research/sessions/{session_id}/messages",
        headers=HEADERS
    )
    return response.json()
```

## 最佳实践

### 1. 错误处理
- 始终检查HTTP状态码
- 处理网络超时和连接错误
- 实现重试机制

### 2. 性能优化
- 使用分页获取大量数据
- 实现客户端缓存
- 避免频繁的API调用

### 3. 用户体验
- 显示加载状态
- 提供实时进度反馈
- 处理长时间运行的任务

### 4. 安全考虑
- 保护API Token
- 验证用户输入
- 使用HTTPS传输

## 限制和配额

### 请求限制
- 每分钟最多60次请求
- 单次请求超时时间: 30秒
- 最大内容长度: 300字符

### 数据限制
- 每个用户最多100个会话
- 每个会话最多1000条消息
- 单条消息最大长度: 10KB

## 更新日志

### v1.0.0 (2024-01-01)
- 初始版本发布
- 支持基础的研究请求创建
- 实现会话管理功能
- 添加实时进程监控



