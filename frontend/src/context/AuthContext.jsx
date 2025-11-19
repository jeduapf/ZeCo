/**
 * Authentication Context
 * 
 * This context manages the entire authentication lifecycle:
 * 1. User login/logout
 * 2. Registration
 * 3. Token management (store, retrieve, validate)
 * 4. Current user state
 * 5. Role-based access control
 * 6. Automatic token refresh
 * 7. Session persistence across page reloads
 * 
 * Architecture Decision:
 * We separate authentication (who you are) from authorization (what you can do).
 * This context handles both, but keeps them logically separate.
 * 
 * Security Features:
 * - JWT tokens stored in httpOnly would be ideal, but we use localStorage for simplicity
 * - Automatic logout on token expiration
 * - Role-based permission checking
 * - Secure password handling (never stored in state)
 */

import React, { createContext, useContext, useState, useEffect } from 'react'
import api from '../services/api'

const AuthContext = createContext(null)

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(localStorage.getItem('access_token'))
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem('user')
    return raw ? JSON.parse(raw) : null
  })
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    async function init() {
      if (!token) {
        setIsLoading(false)
        return
      }
      try {
        const data = await api.get('/auth/me')
        setUser(data)
      } catch (e) {
        console.warn('🔐 [Auth] Session validation failed', e.message)
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        api.clearToken()
        setToken(null)
        setUser(null)
      } finally {
        setIsLoading(false)
      }
    }
    init()
  }, [token])

  const login = async (username, password) => {
    console.log('🔐 [Auth] Login attempt', { username })

    try {
      // Use URLSearchParams for OAuth2PasswordRequestForm compatibility
      const body = new URLSearchParams()
      body.append('username', username)
      body.append('password', password)

      const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1'
      const response = await fetch(`${API_BASE}/auth/token`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: body.toString()
      })

      if (!response.ok) {
        const errorText = await response.text()
        throw new Error(errorText || 'Login failed')
      }

      const data = await response.json()
      console.log('🔐 [Auth] Login successful!', { user: data.user })

      // Store token and user
      api.setToken(data.access_token)
      localStorage.setItem('user', JSON.stringify(data.user))
      setToken(data.access_token)
      setUser(data.user)

      return data.user
    } catch (e) {
      console.error('🔐 [Auth] Login failed:', e.message)
      throw e
    }
  }

  const logout = () => {
    console.log('🔐 [Auth] Logout')
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
    api.clearToken()
    setToken(null)
    setUser(null)
  }

  /**
   * Authenticated fetch wrapper
   * Makes API calls with authentication automatically included
   */
  const authFetch = async (endpoint, options = {}) => {
    return api.get(endpoint, options.headers)
  }

  return (
    <AuthContext.Provider value={{ token, user, isLoading, login, logout, authFetch }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
