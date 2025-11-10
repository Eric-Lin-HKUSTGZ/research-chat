/**
 * WebSocket 客户端封装类
 *
 * 处理 WebSocket 连接的认证失败和任务不存在等错误场景
 */

export interface WebSocketClientConfig {
  url: string
  onMessage?: (data: any) => void
  onStatusUpdate?: (status: string, logs: string[]) => void
  onAuthError?: () => void
  onNotFoundError?: () => void
  onComplete?: () => void
  onError?: (error: Event) => void
}

export class WebSocketClient {
  private ws: WebSocket | null = null
  private config: WebSocketClientConfig

  constructor(config: WebSocketClientConfig) {
    this.config = config
  }

  /**
   * 连接 WebSocket
   */
  connect(): Promise<WebSocket> {
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.config.url)

        this.ws.onopen = () => {
          console.log('WebSocket 连接已建立:', this.config.url)
          resolve(this.ws!)
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket 连接失败:', error)
          if (this.config.onError) {
            this.config.onError(error)
          }
          reject(error)
        }

        this.ws.onclose = (event) => {
          this.handleClose(event)
        }

        this.ws.onmessage = (event) => {
          this.handleMessage(event)
        }
      } catch (error) {
        console.error('WebSocket 连接异常:', error)
        reject(error)
      }
    })
  }

  /**
   * 处理关闭事件
   */
  private handleClose(event: CloseEvent): void {
    console.log(`WebSocket 连接已关闭: code=${event.code}, reason=${event.reason}`)

    // WebSocket 关闭码 1003: 数据不可接受
    if (event.code === 1003) {
      const reason = event.reason || ''

      // 认证失败 (403 equivalent)
      if (reason.includes('Authentication failed')) {
        console.error('认证失败 (403)')
        if (this.config.onAuthError) {
          this.config.onAuthError()
        }
      }
      // 任务不存在 (404 equivalent)
      else if (reason.includes('Task not found')) {
        console.error('任务不存在 (404)')
        if (this.config.onNotFoundError) {
          this.config.onNotFoundError()
        }
      }
    }
    // 正常关闭
    else if (event.code === 1000) {
      console.log('任务已完成，连接正常关闭')
    }

    this.ws = null
  }

  /**
   * 处理消息事件
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const data = JSON.parse(event.data)

      // 触发通用消息回调
      if (this.config.onMessage) {
        this.config.onMessage(data)
      }

      // 处理状态更新
      if (data.code === 200 && data.data) {
        const { status, logs } = data.data

        if (this.config.onStatusUpdate) {
          this.config.onStatusUpdate(status, logs || [])
        }

        // 任务完成或失败
        if (status === 'created' || status === 'failed') {
          if (this.config.onComplete) {
            this.config.onComplete()
          }
        }
      }
    } catch (error) {
      console.error('解析 WebSocket 消息失败:', error)
    }
  }

  /**
   * 发送消息
   */
  send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('WebSocket 未连接，无法发送消息')
    }
  }

  /**
   * 关闭连接
   */
  close(): void {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  /**
   * 获取连接状态
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}

/**
 * 创建状态追踪 WebSocket 客户端的便捷函数
 */
export function createStatusWebSocketClient(
  baseUrl: string,
  messageId: number,
  token: string,
  handlers: {
    onStatusUpdate?: (status: string, logs: string[]) => void
    onAuthError?: () => void
    onNotFoundError?: () => void
    onComplete?: () => void
  },
  locale: string = 'cn'
): WebSocketClient {
  const url = `${baseUrl}/ws/status/${messageId}?token=${token}&locale=${locale}`

  return new WebSocketClient({
    url,
    onMessage: (data) => {
      console.log('收到状态消息:', data)
    },
    onStatusUpdate: handlers.onStatusUpdate,
    onAuthError: handlers.onAuthError || (() => {
      alert('认证失败，请重新登录')
      window.location.href = '/login'
    }),
    onNotFoundError: handlers.onNotFoundError || (() => {
      alert('任务不存在，请检查任务ID')
    }),
    onComplete: handlers.onComplete,
    onError: (error) => {
      console.error('WebSocket 错误:', error)
    }
  })
}
