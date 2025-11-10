import React, { useState } from 'react'
import { login } from '../api/client'
import '../App.css'

interface LoginProps {
  onLoginSuccess: () => void
}

const Login: React.FC<LoginProps> = ({ onLoginSuccess }) => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()

    if (!email.trim() || !password.trim()) {
      setErrorMessage('请输入邮箱和密码')
      return
    }

    setIsLoading(true)
    setErrorMessage('')

    try {
      await login(email.trim(), password.trim())
      onLoginSuccess()
    } catch (error: any) {
      console.error('登录失败:', error)
      if (error.response?.status === 404) {
        setErrorMessage('用户不存在')
      } else if (error.response?.status === 401) {
        setErrorMessage('密码错误')
      } else if (error.response?.status === 403) {
        setErrorMessage('用户已被禁用')
      } else {
        setErrorMessage('登录失败，请检查网络连接或稍后重试')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      height: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    }}>
      <div style={{
        background: 'white',
        padding: '40px',
        borderRadius: '12px',
        boxShadow: '0 10px 40px rgba(0,0,0,0.1)',
        width: '100%',
        maxWidth: '400px'
      }}>
        <h1 style={{
          textAlign: 'center',
          marginBottom: '30px',
          color: '#333',
          fontSize: '28px'
        }}>
          🤖 科研智能体
        </h1>

        <form onSubmit={handleLogin}>
          <div style={{ marginBottom: '20px' }}>
            <label style={{
              display: 'block',
              marginBottom: '8px',
              color: '#666',
              fontSize: '14px',
              fontWeight: '500'
            }}>
              邮箱
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="请输入邮箱"
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #ddd',
                borderRadius: '6px',
                fontSize: '14px',
                boxSizing: 'border-box'
              }}
            />
          </div>

          <div style={{ marginBottom: '24px' }}>
            <label style={{
              display: 'block',
              marginBottom: '8px',
              color: '#666',
              fontSize: '14px',
              fontWeight: '500'
            }}>
              密码
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              disabled={isLoading}
              style={{
                width: '100%',
                padding: '12px',
                border: '1px solid #ddd',
                borderRadius: '6px',
                fontSize: '14px',
                boxSizing: 'border-box'
              }}
            />
          </div>

          {errorMessage && (
            <div style={{
              padding: '12px',
              marginBottom: '20px',
              background: '#fee',
              border: '1px solid #fcc',
              borderRadius: '6px',
              color: '#c33',
              fontSize: '14px'
            }}>
              {errorMessage}
            </div>
          )}

          <button
            type="submit"
            disabled={isLoading}
            style={{
              width: '100%',
              padding: '14px',
              background: isLoading ? '#ccc' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              fontSize: '16px',
              fontWeight: '600',
              cursor: isLoading ? 'not-allowed' : 'pointer',
              transition: 'all 0.3s'
            }}
          >
            {isLoading ? '登录中...' : '登录'}
          </button>
        </form>

        <div style={{
          marginTop: '20px',
          textAlign: 'center',
          fontSize: '12px',
          color: '#999'
        }}>
          提示：首次使用请联系管理员注册账号
        </div>
      </div>
    </div>
  )
}

export default Login
