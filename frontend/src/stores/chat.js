import { defineStore } from 'pinia'
import { ref, reactive } from 'vue'
import { chatApi } from '../api'

export const useChatStore = defineStore('chat', () => {
  const sessions = ref([])
  const currentSessionId = ref('')
  const messages = ref([])
  const isLoading = ref(false)
  const error = ref(null)

  /**
   * 初始化：加载最新会话和历史会话列表
   * 页面加载时调用，恢复上次的对话状态
   */
  async function initChat() {
    error.value = null
    try {
      // 并行加载会话列表和最新会话
      const [sessionsList, latestSession] = await Promise.all([
        chatApi.getSessions(),
        chatApi.getLatestSession()
      ])
      sessions.value = sessionsList

      if (latestSession && latestSession.session_id) {
        currentSessionId.value = latestSession.session_id
        // 加载最新会话的消息
        await loadMessages(currentSessionId.value)
      }
    } catch (err) {
      console.error('初始化聊天失败:', err)
      error.value = '加载会话失败：' + (err.detail || '网络错误')
      setTimeout(() => { error.value = null }, 5000)
    }
  }

  async function loadSessions() {
    try {
      sessions.value = await chatApi.getSessions()
    } catch (err) {
      console.error('加载会话失败:', err)
      error.value = '加载会话失败：' + (err.detail || '网络错误')
      setTimeout(() => { error.value = null }, 5000)
    }
  }

  /**
   * 新建对话：显式创建新会话，清空当前消息
   */
  async function createNewSession() {
    error.value = null
    try {
      const result = await chatApi.createSession()
      currentSessionId.value = result.session_id
      messages.value = []
      await loadSessions()
    } catch (err) {
      console.error('创建会话失败:', err)
      error.value = '创建会话失败：' + (err.detail || '网络错误')
      setTimeout(() => { error.value = null }, 5000)
    }
  }

  /**
   * 加载指定会话的历史消息
   */
  async function loadMessages(sessionId) {
    currentSessionId.value = sessionId
    error.value = null
    try {
      const msgs = await chatApi.getMessages(sessionId)
      messages.value = msgs
    } catch (err) {
      console.error('加载消息失败:', err)
      error.value = '加载历史消息失败：' + (err.detail || '网络错误')
      setTimeout(() => { error.value = null }, 5000)
    }
  }

  /**
   * 生成消息唯一ID，避免数组下标作为key导致流式渲染错乱
   */
  function genMsgId() {
    return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
  }

  /**
   * 发送消息：消息始终归入当前会话
   */
  async function sendMessage(content) {
    // 并发防护：isLoading 已为 true 时直接返回，避免重复触发
    if (isLoading.value) {
      console.warn('[sendMessage] 已有消息在发送中，忽略重复请求')
      return
    }
    if (!content || !content.trim()) {
      return
    }
    isLoading.value = true
    error.value = null
    try {
      const userMsgId = genMsgId()
      const assistantMsgId = genMsgId()
      messages.value.push({ id: userMsgId, role: 'user', content: content })

      const assistantMsg = reactive({ id: assistantMsgId, role: 'assistant', content: '' })
      messages.value.push(assistantMsg)

      await chatApi.chatStream(
        currentSessionId.value,
        content,
        (chunk) => {
          // 只在当前AI消息对象存在时追加，防止会话切换后的脏写
          if (messages.value.includes(assistantMsg)) {
            assistantMsg.content += chunk
          }
        },
        (sessionId) => {
          if (sessionId && !currentSessionId.value) {
            currentSessionId.value = sessionId
          }
        }
      )

      await loadSessions()
    } catch (err) {
      console.error('发送消息失败:', err)
      messages.value.push({
        id: genMsgId(),
        role: 'system',
        content: '⚠️ 发送失败：' + (err.detail || err.message || '网络错误')
      })
    } finally {
      isLoading.value = false
    }
  }

  async function deleteSession(sessionId) {
    try {
      await chatApi.deleteSession(sessionId)
      await loadSessions()
      if (currentSessionId.value === sessionId) {
        // 当前会话被删除，切换到最新会话
        const latest = await chatApi.getLatestSession()
        if (latest && latest.session_id) {
          await loadMessages(latest.session_id)
        } else {
          await createNewSession()
        }
      }
    } catch (err) {
      console.error('删除会话失败:', err)
      error.value = '删除会话失败：' + (err.detail || '网络错误')
      setTimeout(() => { error.value = null }, 5000)
    }
  }

  return {
    sessions,
    currentSessionId,
    messages,
    isLoading,
    error,
    initChat,
    loadSessions,
    createNewSession,
    loadMessages,
    sendMessage,
    deleteSession
  }
})