import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || ''

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 15000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      const refresh = localStorage.getItem('refresh_token')
      if (refresh) {
        try {
          const res = await axios.post(`${BASE_URL}/api/auth/token/refresh/`, { refresh })
          const newAccess = res.data.access
          localStorage.setItem('access_token', newAccess)
          original.headers['Authorization'] = `Bearer ${newAccess}`
          return api(original)
        } catch {
          localStorage.clear()
          window.dispatchEvent(new CustomEvent('auth:expired'))
        }
      }
    }

    return Promise.reject(error)
  }
)

export const authApi = {
  register: (data) => api.post('/api/auth/register/', data),
  login: (data) => api.post('/api/auth/login/', data),
  logout: (refresh) => api.post('/api/auth/logout/', { refresh }),
  enableTotp: () => api.post('/api/auth/2fa/enable/'),
  verifyTotp: (code) => api.post('/api/auth/2fa/verify/', { code }),
  disableTotp: (password, code) => api.post('/api/auth/2fa/disable/', { password, code }),
  whoami: () => api.get('/api/whoami/'),
}

export default api
