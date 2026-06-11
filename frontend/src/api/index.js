import axios from 'axios'
import router from '../router'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      router.push('/login')
    }
    return Promise.reject(err)
  }
)

export default api

// Auth
export const login = (username, password) =>
  api.post('/auth/login', { username, password })

// Chat
export const sendMessage = (message) =>
  api.post('/chat', { message })

// Servers
export const getServers = () => api.get('/servers/')
export const createServer = (data) => api.post('/servers/', data)
export const updateServer = (id, data) => api.put(`/servers/${id}`, data)
export const deleteServer = (id) => api.delete(`/servers/${id}`)
export const testServer = (id) => api.post(`/servers/${id}/test`)

// Tasks
export const getTasks = (page = 1, pageSize = 20) =>
  api.get('/tasks/', { params: { page, page_size: pageSize } })
export const getTask = (id) => api.get(`/tasks/${id}`)
