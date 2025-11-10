import { useState, useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import Chat from './pages/Chat'
import Login from './pages/Login'
import { isLoggedIn, logout } from './api/client'
import './App.css'

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    // 检查初始登录状态
    setIsAuthenticated(isLoggedIn())
  }, [])

  const handleLoginSuccess = () => {
    setIsAuthenticated(true)
    navigate('/chat')
  }

  const handleLogout = () => {
    logout()
    setIsAuthenticated(false)
    navigate('/login')
  }

  return (
    <div className="App">
      <Routes>
        <Route
          path="/login"
          element={
            isAuthenticated ? <Navigate to="/chat" replace /> : <Login onLoginSuccess={handleLoginSuccess} />
          }
        />
        <Route
          path="/chat"
          element={
            isAuthenticated ? <Chat onLogout={handleLogout} /> : <Navigate to="/login" replace />
          }
        />
        <Route
          path="/"
          element={<Navigate to={isAuthenticated ? "/chat" : "/login"} replace />}
        />
      </Routes>
    </div>
  )
}

export default App



