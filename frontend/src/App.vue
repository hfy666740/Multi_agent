<template>
  <div class="app-container">
    <div v-if="isLoggedIn" class="sidebar">
      <div class="sidebar-header">
        <button class="btn" @click="createNewChat">新建对话</button>
      </div>
      
      <div class="sidebar-section">
        <div class="sidebar-title">历史对话</div>
        <div 
          v-for="session in sessions" 
          :key="session.session_id"
          class="sidebar-item"
          :class="{ active: currentSessionId === session.session_id }"
          @click="selectSession(session.session_id)"
        >
          <div class="session-title">{{ session.title || '新对话' }}</div>
          <div class="session-info">
            <span class="session-count">{{ session.message_count }} 条消息</span>
            <span class="session-time">{{ formatTime(session.updated_at) }}</span>
          </div>
          <button class="delete-btn" @click.stop="deleteSession(session.session_id)">删除</button>
        </div>
      </div>

      <div class="sidebar-footer">
        <router-link to="/" class="nav-link" :class="{ active: $route.path === '/' }">聊天</router-link>
        <router-link v-if="user?.role === 'admin'" to="/knowledge" class="nav-link" :class="{ active: $route.path === '/knowledge' }">知识库</router-link>
        <button class="btn" @click="logout">退出登录</button>
      </div>
    </div>

    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { useChatStore } from './stores/chat'

const router = useRouter()
const authStore = useAuthStore()
const chatStore = useChatStore()

const isLoggedIn = computed(() => authStore.isLoggedIn)
const user = computed(() => authStore.user)
const sessions = computed(() => chatStore.sessions)
const currentSessionId = computed(() => chatStore.currentSessionId)

onMounted(async () => {
  if (isLoggedIn.value) {
    await chatStore.initChat()
  }
})

async function createNewChat() {
  await chatStore.createNewSession()
  router.push('/')
}

async function selectSession(sessionId) {
  try {
    await chatStore.loadMessages(sessionId)
    if (router.currentRoute.value.path !== '/') {
      router.push('/')
    }
  } catch (err) {
    console.error('加载会话消息失败:', err)
  }
}

async function deleteSession(sessionId) {
  await chatStore.deleteSession(sessionId)
}

function logout() {
  authStore.logout()
  router.push('/login')
}

function formatTime(time) {
  if (!time) return ''
  const date = new Date(time)
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}
</script>

<style scoped>
.app-container {
  display: flex;
  height: 100vh;
}

.sidebar-header {
  padding: 8px;
  margin-bottom: 16px;
}

.sidebar-section {
  flex: 1;
  overflow-y: auto;
}

.sidebar-title {
  padding: 8px 12px;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
}

.session-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-count {
  font-size: 14px;
}

.session-time {
  font-size: 12px;
  color: var(--text-secondary);
}

.delete-btn {
  padding: 4px 8px;
  font-size: 12px;
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s;
}

.sidebar-item {
  cursor: pointer;
}

.sidebar-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: #ef4444;
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.main-content {
  flex: 1;
  overflow-y: auto;
}
</style>