import { useState, useCallback, useEffect } from 'react'
import { authApi } from '../api/client'

function getStoredUser() {
  try {
    const raw = localStorage.getItem('user')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export function useAuth() {
  const [user, setUser] = useState(getStoredUser)
  const [sessionExpiry, setSessionExpiry] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const isLoggedIn = Boolean(user && localStorage.getItem('access_token'))

  const storeSession = useCallback((data) => {
    localStorage.setItem('access_token', data.access)
    localStorage.setItem('refresh_token', data.refresh)
    localStorage.setItem('user', JSON.stringify(data.user))
    setUser(data.user)
    setSessionExpiry(data.session_expires_at)
    setError(null)
  }, [])

  const clearSession = useCallback(() => {
    localStorage.clear()
    setUser(null)
    setSessionExpiry(null)
  }, [])

  const register = useCallback(async (username, password, passwordConfirm) => {
    setIsLoading(true)
    setError(null)
    try {
      const res = await authApi.register({ username, password, password_confirm: passwordConfirm })
      return { ok: true, data: res.data }
    } catch (err) {
      const msg = extractError(err)
      setError(msg)
      return { ok: false, error: msg }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const login = useCallback(async (username, password, totpCode) => {
    setIsLoading(true)
    setError(null)
    try {
      const payload = { username, password }
      if (totpCode) payload.totp_code = totpCode
      const res = await authApi.login(payload)

      if (res.data.requires_totp) {
        return { ok: false, requiresTotp: true }
      }

      storeSession(res.data)
      return { ok: true, data: res.data }
    } catch (err) {
      const data = err.response?.data || {}
      if (data.retry_after_seconds) {
        return { ok: false, locked: true, retryAfter: data.retry_after_seconds, error: data.error }
      }
      const msg = data.error || extractError(err)
      setError(msg)
      return { ok: false, error: msg, attemptsRemaining: data.attempts_remaining }
    } finally {
      setIsLoading(false)
    }
  }, [storeSession])

  const logout = useCallback(async () => {
    const refresh = localStorage.getItem('refresh_token')
    if (refresh) {
      try {
        await authApi.logout(refresh)
      } catch {
      }
    }
    clearSession()
    return { ok: true }
  }, [clearSession])

  const whoami = useCallback(async () => {
    setIsLoading(true)
    try {
      const res = await authApi.whoami()
      setSessionExpiry(res.data.session_expires_at)
      return { ok: true, data: res.data }
    } catch (err) {
      return { ok: false, error: extractError(err) }
    } finally {
      setIsLoading(false)
    }
  }, [])

  const enableTotp = useCallback(async () => {
    try {
      const res = await authApi.enableTotp()
      return { ok: true, data: res.data }
    } catch (err) {
      return { ok: false, error: extractError(err) }
    }
  }, [])

  const verifyTotp = useCallback(async (code) => {
    try {
      const res = await authApi.verifyTotp(code)
      setUser(u => ({ ...u, totp_enabled: true }))
      return { ok: true, data: res.data }
    } catch (err) {
      return { ok: false, error: extractError(err) }
    }
  }, [])

  const disableTotp = useCallback(async (password, code) => {
    try {
      const res = await authApi.disableTotp(password, code)
      setUser(u => ({ ...u, totp_enabled: false }))
      return { ok: true, data: res.data }
    } catch (err) {
      return { ok: false, error: extractError(err) }
    }
  }, [])

  useEffect(() => {
    const handler = () => {
      clearSession()
      window.location.reload()
    }
    window.addEventListener('auth:expired', handler)
    return () => window.removeEventListener('auth:expired', handler)
  }, [clearSession])

  return {
    user,
    sessionExpiry,
    isLoading,
    error,
    isLoggedIn,
    register,
    login,
    logout,
    whoami,
    enableTotp,
    verifyTotp,
    disableTotp,
  }
}

function extractError(err) {
  if (!err.response) return 'Network error. Check your connection.'
  const data = err.response.data
  if (typeof data === 'string') return data
  if (data.detail) return data.detail
  if (data.error) return data.error
  const firstKey = Object.keys(data)[0]
  if (firstKey) {
    const val = data[firstKey]
    return Array.isArray(val) ? val[0] : val
  }
  return 'Something went wrong.'
}
