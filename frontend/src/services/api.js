import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

console.log(import.meta.env.VITE_API_BASE_URL,"ip adresssssssssssssssssss")
const token = localStorage.getItem('cn_token')
if (token) api.defaults.headers.common['Authorization'] = `Bearer ${token}`

export default api
