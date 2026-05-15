import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

const token = localStorage.getItem('cn_token')
if (token) api.defaults.headers.common['Authorization'] = `Bearer ${token}`

export default api
