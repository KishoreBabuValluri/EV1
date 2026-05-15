// import axios from 'axios'

// const api = axios.create({
//   baseURL: '/api',
//   headers: { 'Content-Type': 'application/json' },
// })

// const token = localStorage.getItem('cn_token')
// if (token) api.defaults.headers.common['Authorization'] = `Bearer ${token}`

// export default api

import axios from 'axios'

/**
 * In local dev:   VITE_API_URL is not set → baseURL = '/api' → Vite proxy handles it
 * In production:  VITE_API_URL = 'https://chargenexus-api.onrender.com' → full URL used
 *
 * Set VITE_API_URL in Render frontend environment variables.
 */
const BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api'

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: false,
})

// Attach JWT from localStorage on every request
const token = localStorage.getItem('cn_token')
console.log(token,"tokennnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn")
if (token) api.defaults.headers.common['Authorization'] = `Bearer ${token}`

// Re-attach token on every request in case it changed after init
api.interceptors.request.use(config => {
  const t = localStorage.getItem('cn_token')
  if (t) config.headers['Authorization'] = `Bearer ${t}`
  return config
})

export default api