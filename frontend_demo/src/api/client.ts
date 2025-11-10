import axios from 'axios'
import { createStatusWebSocketClient, WebSocketClient } from '../utils/WebSocketClient'
import Cookies from 'js-cookie'

const API_BASE_URL = '/digital_twin/research_chat/api'
const AUTH_TOKEN_KEY = 'research_chat_auth_token'

// 判断是否为局域网环境
const isLocalNetwork = (): boolean => {
  const host = window.location.hostname
  // 判断是否为局域网 IP（10.x.x.x, 172.16-31.x.x, 192.168.x.x）或 localhost
  return (
    host === 'localhost' ||
    host === '127.0.0.1' ||
    host.startsWith('10.') ||
    host.startsWith('192.168.') ||
    /^172\.(1[6-9]|2\d|3[01])\./.test(host)
  )
}

// 动态获取 WebSocket URL（根据当前浏览器地址和环境）
const getWebSocketBaseURL = (): string => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const hostname = window.location.hostname

  // 如果是局域网环境，使用4200端口；否则使用当前浏览器端口
  let port = ''
  if (isLocalNetwork()) {
    port = ':4200'
  } else {
    // 线上环境：使用浏览器当前端口（如果不是默认端口）
    const currentPort = window.location.port
    if (currentPort && currentPort !== '80' && currentPort !== '443') {
      port = `:${currentPort}`
    }
  }

  return `${protocol}//${hostname}${port}/digital_twin/research_chat`
}

// 存储token的变量
let authToken: string | null = null
let websocket: WebSocket | null = null

// 初始化：从 Cookie 恢复 token
const initializeToken = () => {
  const savedToken = Cookies.get(AUTH_TOKEN_KEY)
  if (savedToken) {
    authToken = savedToken
    console.log('已从 Cookie 恢复登录状态')
  }
}

// 自动执行初始化
initializeToken()

// 检查是否已登录
export const isLoggedIn = (): boolean => {
  return authToken !== null
}

// 获取当前 token（供外部使用）
export const getAuthToken = (): string | null => {
  return authToken
}

// 设置 token（用于登录成功后）
export const setAuthToken = (token: string) => {
  authToken = token
  // 保存到 Cookie，7天过期
  Cookies.set(AUTH_TOKEN_KEY, token, { expires: 7 })
  console.log('Token 已保存到 Cookie')
}

// 清除token（登出）
export const logout = () => {
  authToken = null
  Cookies.remove(AUTH_TOKEN_KEY)
  console.log('已清除登录状态')
  if (websocket) {
    websocket.close()
    websocket = null
  }
}

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 用户登录函数
export const login = async (email: string, password: string): Promise<string> => {
  try {
    const response = await axios.post('/digital_twin/research_chat/api/auth/login', {
      email,
      password
    })
    const token = response.data.data.access_token
    setAuthToken(token)  // 使用新的 setAuthToken 函数保存到 Cookie
    return token
  } catch (error) {
    console.error('登录失败:', error)
    throw error
  }
}

// 请求拦截器
apiClient.interceptors.request.use(
  async (config) => {
    // 如果没有token，提示用户登录
    if (!authToken) {
      console.warn('未登录，请先登录')
      return Promise.reject(new Error('未登录，请先登录'))
    }

    // 添加Authorization头
    if (authToken) {
      config.headers.Authorization = `Bearer ${authToken}`
    }

    console.log('API Request:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.data)
    return response
  },
  (error) => {
    console.error('API Response Error:', error.response?.status, error.response?.data)
    return Promise.reject(error)
  }
)

export interface CreateResearchRequest {
  content: string
  session_id?: string
}

export interface SessionItem {
  id: number
  session_id: string
  session_name: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface MessageItem {
  id: number
  session_id: number
  user_id: number | string
  email: string
  content: string
  result_papers: any
  extra_info: any
  created_at: string
  updated_at: string
}

export interface ProcessInfoItem {
  id: number
  session_id: number
  message_id: number
  user_id: number | string
  email: string
  process_info: any
  extra_info: any
  creation_status: string
  created_at: string
  updated_at: string
}

// WebSocket相关函数
export const connectWebSocket = (sessionId?: string): Promise<WebSocket> => {
  return new Promise((resolve, reject) => {
    if (!authToken) {
      reject(new Error('No authentication token available'))
      return
    }

    const wsBaseUrl = getWebSocketBaseURL()
    const wsUrl = `${wsBaseUrl}/ws?token=${authToken}${sessionId ? `&session_id=${sessionId}` : ''}`
    websocket = new WebSocket(wsUrl)

    websocket.onopen = () => {
      console.log('WebSocket连接已建立')
      resolve(websocket!)
    }

    websocket.onerror = (error) => {
      console.error('WebSocket连接错误:', error)
      reject(error)
    }

    websocket.onclose = () => {
      console.log('WebSocket连接已关闭')
      websocket = null
    }
  })
}

// 连接到状态跟踪WebSocket（使用 WebSocketClient 封装类）
// 注意：浏览器 WebSocket API 不支持自定义 header；通过 URL 参数传递 token
export const connectStatusWebSocket = (
  messageId: number,
  locale: string = 'cn',
  handlers?: {
    onStatusUpdate?: (status: string, logs: string[]) => void
    onAuthError?: () => void
    onNotFoundError?: () => void
    onComplete?: () => void
  }
): WebSocketClient => {
  if (!authToken) {
    throw new Error('No authentication token available')
  }

  const wsBaseUrl = getWebSocketBaseURL()

  return createStatusWebSocketClient(wsBaseUrl, messageId, authToken, handlers || {}, locale)
}

export const disconnectWebSocket = () => {
  if (websocket) {
    websocket.close()
    websocket = null
  }
}

export const sendWebSocketMessage = (message: any) => {
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    websocket.send(JSON.stringify(message))
  } else {
    console.warn('WebSocket未连接')
  }
}

export const getWebSocket = (): WebSocket | null => {
  return websocket
}

// 生成 page_session_id
const generatePageSessionId = (): string => {
  return `page_${Date.now()}`
}

export const researchApi = {
  // 创建研究请求（一次性创建，后台异步处理）
  createResearchRequest: async (data: CreateResearchRequest & { locale?: string }) => {
    try {
      // 确保locale参数存在，默认为cn
      const requestData = {
        ...data,
        locale: data.locale || 'cn'
      }
      
      const response = await apiClient.post('/create', requestData, {
        headers: {
          'x-page-id': generatePageSessionId()
        }
      })
      if (response.data.code === 200 && response.data.data) {
        return response.data.data
      }
      throw new Error(response.data.message || '创建研究请求失败')
    } catch (error: any) {
      // 处理 409 冲突错误：会话中已有正在处理的任务
      if (error.response?.status === 409 || error.response?.data?.code === 409) {
        const errorMessage = error.response?.data?.message || '当前会话已有正在处理中的任务，请等待任务完成后再提交新的研究请求'
        throw new Error(errorMessage)
      }
      throw error
    }
  },

  // 获取会话列表
  getSessions: async (page?: number, size?: number) => {
    const params = new URLSearchParams()
    // 始终传递分页参数，如果没有提供则使用默认值
    params.append('page', (page || 1).toString())
    params.append('size', (size || 20).toString())

    const response = await apiClient.get(`/sessions?${params}`)
    // 适配新的后端格式：{code, message, data: {user_id, chat_type, sessions, pagination}}
    return response.data.data || response.data
  },

  // 获取会话消息
  getSessionMessages: async (sessionId: string, latest?: boolean) => {
    const params = new URLSearchParams()
    if (latest) params.append('latest', '1')

    const response = await apiClient.get(`/sessions/${sessionId}/messages?${params}`)
    // 适配新的后端格式：{code, message, data: [...]}
    return response.data.data || response.data
  },

  // 更新会话名称
  updateSessionName: async (sessionId: string, sessionName: string) => {
    const response = await apiClient.put(`/sessions/${sessionId}/name`, {
      session_name: sessionName
    })
    return response.data
  },

  // 删除会话
  deleteSession: async (sessionId: string) => {
    const response = await apiClient.delete(`/sessions/${sessionId}`)
    return response.data
  }
}

export default apiClient
