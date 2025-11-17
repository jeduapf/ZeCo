/**
 * API Service Module
 * 
 * Centralized API client for all backend communication.
 * Handles:
 * - Request/response formatting
 * - Authentication token management
 * - Error handling
 * - Base URL configuration
 * - Common headers
 * 
 * Usage:
 *   import api from '@/services/api'
 *   const data = await api.get('/auth/me')
 */

// Support both VITE_API_BASE_URL and legacy VITE_API_BASE (docker-compose used VITE_API_BASE previously)
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_BASE || 'http://localhost:8000/api/v1'
const DEBUG = import.meta.env.VITE_DEBUG === 'true'

/**
 * Logger utility for debugging API calls
 */
const log = {
  request: (method, url, data = null) => {
    if (DEBUG) {
      console.log(`🌐 [API] ${method.toUpperCase()} ${url}`, data || '')
    }
  },
  response: (method, url, status, data = null) => {
    if (DEBUG) {
      console.log(`🌐 [API] ${method.toUpperCase()} ${url} → ${status}`, data || '')
    }
  },
  error: (method, url, status, error) => {
    console.error(`❌ [API] ${method.toUpperCase()} ${url} → ${status}`, error)
  }
}

/**
 * Get authorization token from localStorage
 */
const getToken = () => {
  return localStorage.getItem('access_token')
}

/**
 * Set authorization token in localStorage
 */
const setToken = (token) => {
  if (token) {
    localStorage.setItem('access_token', token)
  } else {
    localStorage.removeItem('access_token')
  }
}

/**
 * Build request headers with authentication
 */
const getHeaders = (customHeaders = {}) => {
  const headers = {
    'Content-Type': 'application/json',
    ...customHeaders
  }

  const token = getToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  return headers
}

/**
 * Handle API errors
 */
const handleError = async (response, method, url) => {
  let errorMessage = `HTTP ${response.status}`

  try {
    const errorData = await response.json()
    errorMessage = errorData.detail || errorData.message || errorMessage
  } catch {
    try {
      errorMessage = await response.text()
    } catch {
      // Use default error message
    }
  }

  log.error(method, url, response.status, errorMessage)

  const error = new Error(errorMessage)
  error.status = response.status
  error.response = response

  throw error
}

/**
 * Generic fetch wrapper with error handling
 */
const request = async (method, endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`
  const { data, customHeaders = {}, formData = false } = options

  const fetchOptions = {
    method,
    headers: formData ? { Authorization: `Bearer ${getToken()}` } : getHeaders(customHeaders)
  }

  // For FormData (file uploads), don't set Content-Type
  if (formData) {
    fetchOptions.body = data
  } else if (data) {
    fetchOptions.body = JSON.stringify(data)
  }

  log.request(method, endpoint, data)

  try {
    const response = await fetch(url, fetchOptions)

    if (!response.ok) {
      await handleError(response, method, endpoint)
    }

    // Handle empty responses (204 No Content)
    if (response.status === 204) {
      log.response(method, endpoint, response.status)
      return null
    }

    const responseData = await response.json()
    log.response(method, endpoint, response.status, responseData)

    return responseData
  } catch (error) {
    // If it's already our custom error, re-throw it
    if (error.status) {
      throw error
    }
    // Network error or parsing error
    console.error(`🌐 [API] Network error on ${method} ${endpoint}:`, error)
    throw error
  }
}

/**
 * HTTP Methods
 */
const api = {
  get: (endpoint, customHeaders = {}) =>
    request('GET', endpoint, { customHeaders }),

  post: (endpoint, data = null, customHeaders = {}) =>
    request('POST', endpoint, { data, customHeaders }),

  put: (endpoint, data = null, customHeaders = {}) =>
    request('PUT', endpoint, { data, customHeaders }),

  patch: (endpoint, data = null, customHeaders = {}) =>
    request('PATCH', endpoint, { data, customHeaders }),

  delete: (endpoint, customHeaders = {}) =>
    request('DELETE', endpoint, { customHeaders }),

  // Special method for FormData (file uploads)
  postForm: (endpoint, formData) =>
    request('POST', endpoint, { data: formData, formData: true }),

  putForm: (endpoint, formData) =>
    request('PUT', endpoint, { data: formData, formData: true }),

  // Token management
  setToken,
  getToken,
  clearToken: () => setToken(null)
}

export default api

