import React, { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { researchApi, SessionItem, MessageItem, isLoggedIn, connectStatusWebSocket } from '../api/client'
import '../App.css'

// 扩展消息类型（简化）
type ExtendedMessageItem = MessageItem

interface ChatProps {
  onLogout: () => void
}

const Chat: React.FC<ChatProps> = ({ onLogout }) => {
  const [sessions, setSessions] = useState<SessionItem[]>([])
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ExtendedMessageItem[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [statusMessage, setStatusMessage] = useState('')
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null)
  const [editingSessionName, setEditingSessionName] = useState('')
  const [statusLogs, setStatusLogs] = useState<string[]>([])
  const [taskStatus, setTaskStatus] = useState<string>('')
  const [locale, setLocale] = useState<'cn' | 'en'>('cn') // 添加locale状态

  // 分页相关状态
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(20)
  const [sessionsTotal, setSessionsTotal] = useState(0)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 加载会话列表
  const loadSessions = async () => {
    try {
      const response = await researchApi.getSessions(page, size)
      // 适配新的后端格式：response 现在是 {user_id, chat_type, sessions, pagination}
      if (response.sessions) {
        setSessions(response.sessions)
        setSessionsTotal(response.pagination?.total || response.sessions.length)
        // 如果当前会话不在当前页，自动选择第一个会话
        if (!currentSessionId && response.sessions.length > 0) {
          const firstSession = response.sessions[0]
          setCurrentSessionId(firstSession.session_id)
          await loadSessionMessages(firstSession.session_id)
        }
      } else if (Array.isArray(response)) {
        // 兼容旧格式
        setSessions(response)
        setSessionsTotal(response.length)
        if (!currentSessionId && response.length > 0) {
          const firstSession = response[0]
          setCurrentSessionId(firstSession.session_id)
          await loadSessionMessages(firstSession.session_id)
        }
      }
    } catch (error) {
      console.error('加载会话列表失败:', error)
      setStatusMessage('❌ 加载会话列表失败')
    }
  }

  // 分页处理函数
  const handlePageChange = (newPage: number) => {
    setPage(newPage)
  }

  const handleSizeChange = (newSize: number) => {
    setSize(newSize)
    setPage(1) // 重置到第一页
  }

  // 当page或size变化时重新加载sessions
  useEffect(() => {
    if (isLoggedIn()) {
      loadSessions()
    }
  }, [page, size])

  // 加载会话消息
  const loadSessionMessages = async (sessionId: string) => {
    try {
      const messagesData = await researchApi.getSessionMessages(sessionId, true)
      // 适配新的后端格式：messagesData 现在是数组 [{id, question, answer, process, question_timestamp, answer_timestamp}]

      // 处理消息数据，将 question 和 answer 转换为 content
      const processedMessages: ExtendedMessageItem[] = messagesData.map((msg: any) => ({
        id: msg.id,
        session_id: 0, // 占位符
        user_id: 0,    // 占位符
        email: '',     // 占位符
        content: msg.answer?.response || msg.answer || msg.question || '',
        result_papers: msg.answer,
        extra_info: msg.process,
        created_at: msg.question_timestamp || new Date().toISOString(),
        updated_at: msg.answer_timestamp || new Date().toISOString(),
      }))

      setMessages(processedMessages)

      // 检查最新消息的任务状态，如果正在处理中则启动 WebSocket 轮询
      if (messagesData.length > 0) {
        const latestMessage = messagesData[0]
        const process = latestMessage.process

        if (process && process.creation_status) {
          const status = process.creation_status
          const messageId = latestMessage.id

          // 如果状态不是 'created' 或 'failed'，说明任务正在进行中
          if (status !== 'created' && status !== 'failed') {
            console.log(`检测到进行中的任务: message_id=${messageId}, status=${status}`)
            setIsLoading(true)
            setStatusMessage(`🔄 正在恢复任务状态监控: ${status}`)

            // 启动 WebSocket 轮询监控任务进度
            startStatusPolling(sessionId, messageId)
          }
        }
      }
    } catch (error) {
      console.error('加载会话消息失败:', error)
      setStatusMessage('❌ 加载会话消息失败')
    }
  }

  const startStatusPolling = (sessionId: string, messageId: number) => {
    const id = window.setInterval(async () => {
      try {
        // 使用新的 WebSocketClient 封装，传递locale参数
        const wsClient = connectStatusWebSocket(messageId, locale, {
          onStatusUpdate: (status, logs) => {
            // 更新任务状态
            setTaskStatus(status)

            // 更新状态日志
            if (logs && logs.length > 0) {
              setStatusLogs(logs)
              const latestLog = logs[logs.length - 1]
              setStatusMessage(`🔍 ${latestLog}`)
            } else {
              const statusMessages: { [key: string]: string } = {
                'pending': '⏳ 任务等待中...',
                'creating': '🚀 任务正在进行中...',
                'created': '✅ 任务成功完成',
                'failed': '❌ 任务失败'
              }
              setStatusMessage(statusMessages[status] || '任务正在进行中...')
            }
          },
          onComplete: async () => {
            // 任务完成，停止轮询
            window.clearInterval(id)
            setIsLoading(false)
            setStatusMessage('✅ 内容生成完成')

            // 重新加载会话和消息
            await loadSessions()
            await loadSessionMessages(sessionId)

            // 清空状态日志
            setTimeout(() => {
              setStatusLogs([])
              setTaskStatus('')
            }, 3000)
          },
          onAuthError: () => {
            // 认证失败，停止轮询并跳转登录
            window.clearInterval(id)
            setIsLoading(false)
            alert('认证失败，请重新登录')
            onLogout()
          },
          onNotFoundError: () => {
            // 任务不存在，停止轮询
            window.clearInterval(id)
            setIsLoading(false)
            setTaskStatus('')
            setStatusMessage('任务不存在或已结束')

            // 刷新会话及消息
            ;(async () => {
              try {
                await loadSessions()
                await loadSessionMessages(sessionId)
              } catch {}
            })()
          }
        })

        // 连接 WebSocket
        let settled = false
        wsClient.connect()
          .then(() => {
            // 确保一次连接不长时间占用（后端也会尽快关闭）
            window.setTimeout(() => {
              if (!settled) {
                wsClient.close()
              }
            }, 800)
          })
          .catch((error) => {
            console.error('WebSocket 连接失败:', error)
            settled = true
          })

        // 标记已处理
        settled = true
      } catch (e) {
        // 忽略瞬时错误，下一次轮询重试
        console.error('轮询WebSocket错误:', e)
      }
    }, 1000)
  }

  // 发送消息（仅支持一次性创建 + WebSocket 轮询）
  const sendMessage = async () => {
    if (!inputMessage.trim() || isLoading) return

    const message = inputMessage.trim()
    setInputMessage('')
    setIsLoading(true)

    try {
      setStatusMessage('🚀 正在生成内容，请稍候...')
      const createResponse = await researchApi.createResearchRequest({
        content: message,
        session_id: currentSessionId || undefined,
        locale: locale
      })

      const { session_id, message_id } = createResponse

      // 更新当前会话ID
      if (!currentSessionId && session_id) {
        setCurrentSessionId(session_id)
      }

      // 每秒短连接轮询 WebSocket 状态
      startStatusPolling(session_id, message_id)

    } catch (error: any) {
      console.error('发送消息失败:', error)
      setIsLoading(false)

      // 处理 409 冲突错误：会话中已有正在处理的任务
      if (error.message && error.message.includes('正在处理中的任务')) {
        setStatusMessage('⚠️ ' + error.message)
        // 3秒后自动清除提示
        setTimeout(() => {
          setStatusMessage('')
        }, 5000)
      } else {
        setStatusMessage('❌ 发送消息失败: ' + (error.message || '未知错误'))
      }
    }
  }

  // 更新会话名称
  const updateSessionName = async (sessionId: string, newName: string) => {
    try {
      await researchApi.updateSessionName(sessionId, newName)
      await loadSessions()
    } catch (error) {
      console.error('更新会话名称失败:', error)
    }
  }

  // 开始新对话
  const startNewChat = () => {
    setCurrentSessionId(null)
    setMessages([])
    setStatusMessage('✅ 已开始新对话，请输入您的第一条消息')
  }

  // 选择会话
  const selectSession = async (session: SessionItem) => {
    setCurrentSessionId(session.session_id)
    await loadSessionMessages(session.session_id)
    setStatusMessage(`✅ 已加载对话: ${session.session_name}`)
  }

  // 删除会话
  const deleteSession = async (sessionId: string) => {
    if (!confirm('确定要删除这个对话吗？')) return

    try {
      await researchApi.deleteSession(sessionId)
      await loadSessions()

      if (currentSessionId === sessionId) {
        setCurrentSessionId(null)
        setMessages([])
      }

      setStatusMessage('✅ 对话已删除')
    } catch (error) {
      console.error('删除会话失败:', error)
      setStatusMessage('❌ 删除会话失败')
    }
  }

  // 开始编辑会话名称
  const startEditSessionName = (session: SessionItem) => {
    setEditingSessionId(session.session_id)
    setEditingSessionName(session.session_name)
  }

  // 保存编辑的会话名称
  const saveEditSessionName = async () => {
    if (!editingSessionId || !editingSessionName.trim()) return

    try {
      await updateSessionName(editingSessionId, editingSessionName.trim())
      setEditingSessionId(null)
      setEditingSessionName('')
      setStatusMessage('✅ 对话名称已更新')
    } catch (error) {
      console.error('更新对话名称失败:', error)
      setStatusMessage('❌ 更新对话名称失败')
    }
  }

  // 取消编辑
  const cancelEditSessionName = () => {
    setEditingSessionId(null)
    setEditingSessionName('')
  }

  // 组件挂载时只加载会话列表，不建立WebSocket连接
  useEffect(() => {
    const initializeApp = async () => {
      try {
        // 检查登录状态
        if (!isLoggedIn()) {
          console.log('用户未登录，等待登录')
          onLogout()
          return
        }

        console.log('用户已登录，初始化应用')

        // 只加载会话列表，不建立WebSocket连接
        await loadSessions()
      } catch (error) {
        console.error('应用初始化失败:', error)
        setStatusMessage('❌ 应用初始化失败，请刷新页面重试')
      }
    }

    initializeApp()
  }, [])

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h1>🤖 科研智能体 - 创新方案生成助手</h1>
        
        {/* 语言切换按钮 */}
        <div style={{
          position: 'absolute',
          right: '120px',
          top: '20px',
          display: 'flex',
          gap: '8px'
        }}>
          <button
            onClick={() => setLocale('cn')}
            style={{
              padding: '8px 12px',
              background: locale === 'cn' ? '#007bff' : '#f8f9fa',
              color: locale === 'cn' ? 'white' : '#333',
              border: '1px solid #ddd',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            中文
          </button>
          <button
            onClick={() => setLocale('en')}
            style={{
              padding: '8px 12px',
              background: locale === 'en' ? '#007bff' : '#f8f9fa',
              color: locale === 'en' ? 'white' : '#333',
              border: '1px solid #ddd',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            English
          </button>
        </div>
        
        <button
          onClick={onLogout}
          style={{
            position: 'absolute',
            right: '20px',
            top: '20px',
            padding: '8px 16px',
            background: '#dc3545',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          退出登录
        </button>
      </div>

      <div className="chat-content">
        {/* 侧边栏 */}
        <div className="sidebar">
          <button className="new-chat-btn" onClick={startNewChat}>
            ➕ 新建对话
          </button>

          <div className="conversation-list">
            <h3>📋 历史对话</h3>
            {sessions.map((session) => (
              <div
                key={session.session_id}
                className={`conversation-item ${
                  currentSessionId === session.session_id ? 'active' : ''
                }`}
                onClick={() => !editingSessionId && selectSession(session)}
              >
                {editingSessionId === session.session_id ? (
                  <div style={{ padding: '8px' }}>
                    <input
                      type="text"
                      value={editingSessionName}
                      onChange={(e) => setEditingSessionName(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && saveEditSessionName()}
                      style={{
                        width: '100%',
                        padding: '4px',
                        border: '1px solid #ddd',
                        borderRadius: '4px',
                        fontSize: '12px'
                      }}
                      autoFocus
                    />
                    <div style={{ marginTop: '4px', textAlign: 'right' }}>
                      <button
                        onClick={saveEditSessionName}
                        style={{
                          background: '#28a745',
                          color: 'white',
                          border: 'none',
                          padding: '2px 6px',
                          borderRadius: '3px',
                          fontSize: '10px',
                          marginRight: '4px',
                          cursor: 'pointer'
                        }}
                      >
                        ✓
                      </button>
                      <button
                        onClick={cancelEditSessionName}
                        style={{
                          background: '#dc3545',
                          color: 'white',
                          border: 'none',
                          padding: '2px 6px',
                          borderRadius: '3px',
                          fontSize: '10px',
                          cursor: 'pointer'
                        }}
                      >
                        ✗
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div style={{ fontWeight: 'bold' }}>{session.session_name}</div>
                    <div style={{ fontSize: '11px', color: '#666', marginTop: '4px' }}>
                      {new Date(session.updated_at).toLocaleString()}
                    </div>
                    <div style={{ float: 'right', marginTop: '-20px' }}>
                      <button
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#007bff',
                          cursor: 'pointer',
                          fontSize: '12px',
                          marginRight: '4px'
                        }}
                        onClick={(e) => {
                          e.stopPropagation()
                          startEditSessionName(session)
                        }}
                        title="编辑名称"
                      >
                        ✏️
                      </button>
                      <button
                        style={{
                          background: 'none',
                          border: 'none',
                          color: '#dc3545',
                          cursor: 'pointer',
                          fontSize: '12px'
                        }}
                        onClick={(e) => {
                          e.stopPropagation()
                          deleteSession(session.session_id)
                        }}
                        title="删除对话"
                      >
                        🗑️
                      </button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>

          {/* 分页控件 */}
          <div className="pagination-controls" style={{
            padding: '12px',
            borderTop: '1px solid #e0e0e0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '8px',
            fontSize: '12px'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span>每页显示：</span>
              <select
                value={size}
                onChange={(e) => handleSizeChange(Number(e.target.value))}
                style={{
                  padding: '4px 8px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  fontSize: '12px'
                }}
              >
                <option value={10}>10</option>
                <option value={20}>20</option>
                <option value={50}>50</option>
              </select>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <button
                onClick={() => handlePageChange(Math.max(1, page - 1))}
                disabled={page === 1}
                style={{
                  padding: '4px 8px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  background: page === 1 ? '#f5f5f5' : 'white',
                  cursor: page === 1 ? 'not-allowed' : 'pointer',
                  fontSize: '12px'
                }}
              >
                上一页
              </button>

              <span style={{ color: '#666' }}>
                第 {page} 页 · 共 {sessionsTotal} 条
              </span>

              <button
                onClick={() => handlePageChange(page + 1)}
                disabled={sessions.length < size}
                style={{
                  padding: '4px 8px',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                  background: sessions.length < size ? '#f5f5f5' : 'white',
                  cursor: sessions.length < size ? 'not-allowed' : 'pointer',
                  fontSize: '12px'
                }}
              >
                下一页
              </button>
            </div>
          </div>

        {/* 任务状态追踪区域 */}
        <div className="status-display" style={{ marginBottom: '8px' }}>
          <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '6px' }}>
            <div style={{ fontWeight: 'bold', marginBottom: '8px', color: '#374151' }}>
              📊 任务状态
            </div>

            {/* 任务状态指示 */}
            {taskStatus && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <div style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor:
                    taskStatus === 'created' ? '#10a37f' :
                    taskStatus === 'failed' ? '#dc3545' :
                    taskStatus === 'creating' ? '#fbbf24' :
                    '#6b7280'
                }}></div>
                <span style={{ fontSize: '12px', color: '#6b7280' }}>
                  {taskStatus === 'pending' && '⏳ 等待中'}
                  {taskStatus === 'creating' && '🚀 进行中'}
                  {taskStatus === 'created' && '✅ 已完成'}
                  {taskStatus === 'failed' && '❌ 失败'}
                </span>
              </div>
            )}

            {/* 状态日志 */}
            {statusLogs.length > 0 && (
              <div style={{
                maxHeight: '200px',
                overflowY: 'auto',
                fontSize: '11px',
                color: '#6b7280',
                background: 'white',
                padding: '8px',
                borderRadius: '4px',
                border: '1px solid #e5e7eb'
              }}>
                {statusLogs.map((log, index) => (
                  <div key={index} style={{ marginBottom: '4px' }}>
                    {log}
                  </div>
                ))}
              </div>
            )}

            {/* 无任务时显示 */}
            {!taskStatus && statusLogs.length === 0 && (
              <div style={{ fontSize: '12px', color: '#9ca3af' }}>
                暂无任务运行
              </div>
            )}
          </div>
        </div>

        {statusMessage && (
          <div className="status-display">
            {statusMessage}
          </div>
        )}
        </div>

        {/* 主聊天区域 */}
        <div className="main-chat">
          <div className="chat-messages">
            {messages.length === 0 ? (
              <div style={{ textAlign: 'center', color: '#666', marginTop: '50px' }}>
                <h3>欢迎使用科研智能体！</h3>
                <p>请输入您的研究想法，我将为您生成创新方案。</p>
              </div>
            ) : (
              messages.map((message) => (
                <div key={message.id} className="message assistant">
                  <div style={{ fontWeight: 'bold', marginBottom: '4px', color: '#374151' }}>
                    🤖 科研智能体
                  </div>
                  <div className="markdown-content">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {message.content}
                    </ReactMarkdown>
                  </div>
                  <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
                    {new Date(message.created_at).toLocaleString()}
                  </div>
                </div>
              ))
            )}

            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input">
            <div className="input-group">
              <input
                type="text"
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                placeholder="输入您的研究想法，我将为您生成创新方案..."
                disabled={isLoading}
              />
              <button onClick={sendMessage} disabled={isLoading || !inputMessage.trim()}>
                发送
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Chat
