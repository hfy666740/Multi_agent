import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  res => res.data,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(err.response?.data || err)
  }
)

export const authApi = {
  register: (username, email, password) => 
    api.post('/auth/register', { username, email, password }),
  login: (username, password) => 
    api.post('/auth/login', { username, password }),
  me: () => api.get('/auth/me')
}

export const chatApi = {
  getSessions: () => api.get('/sessions'),
  getMessages: (sessionId) => api.get(`/sessions/${sessionId}/messages`),
  createSession: () => api.post('/sessions'),
  getLatestSession: () => api.get('/sessions/latest'),
  chat: (sessionId, message) => api.post('/chat', { session_id: sessionId, message }),
  chatStream: (sessionId, message, onChunk, onComplete) => {
    return new Promise((resolve, reject) => {
      const token = localStorage.getItem('token')
      let ended = false // 防止end事件重复触发

      fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ session_id: sessionId, message })
      })
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok')
        }
        const reader = response.body.getReader()
        const decoder = new TextDecoder('utf-8')
        let fullContent = ''

        function read() {
          reader.read().then(({ done, value }) => {
            if (done) {
              if (!ended) {
                ended = true
                onComplete?.()
              }
              resolve(fullContent)
              return
            }

            const chunk = decoder.decode(value, { stream: true })
            const lines = chunk.split('\n').filter(line => line.trim())

            for (const line of lines) {
              try {
                const data = JSON.parse(line)
                if (data.type === 'chunk') {
                  fullContent += data.content
                  onChunk?.(data.content)
                } else if (data.type === 'end') {
                  // end事件只触发一次，避免重复拼接
                  if (!ended) {
                    ended = true
                    onComplete?.(data.session_id)
                  }
                } else if (data.type === 'error') {
                  reject(new Error(data.error || '流式输出错误'))
                  return
                }
              } catch (e) {
                console.error('Failed to parse chunk:', e)
              }
            }

            read()
          }).catch(reject)
        }

        read()
      }).catch(reject)
    })
  },
  deleteSession: (sessionId) => api.delete(`/sessions/${sessionId}`)
}

export const knowledgeApi = {
  getFiles: () => api.get('/knowledge/files'),
  reload: () => api.post('/knowledge/reload'),
  deleteFile: (filename) => api.delete(`/knowledge/files/${filename}`)
}

/**
 * 获取 Token 消耗统计
 */
export function getTokenStats(sessionId = null) {
  const params = sessionId ? { session_id: sessionId } : {}
  return api.get('/stats/tokens', { params })
}

/**
 * 获取 Token 消耗历史
 */
export function getTokenHistory(limit = 50, sessionId = null) {
  const params = { limit }
  if (sessionId) params.session_id = sessionId
  return api.get('/stats/tokens/history', { params })
}

export default api