<template>
  <div class="chat-container">
    <!-- 顶部错误提示 -->
    <div v-if="chatStore.error" class="error-banner">
      {{ chatStore.error }}
    </div>

    <div class="chat-messages" ref="messagesContainer">
      <div v-if="chatStore.messages.length === 0" class="empty-state">
        <h2>智扫通智能客服</h2>
        <p>开始一段新对话，或从左侧选择历史对话</p>
      </div>

      <div v-for="(msg, index) in chatStore.messages" :key="msg.id || msg.key || `msg-${index}`" class="message" :class="`message-${msg.role}`">
        <!-- 系统错误消息 -->
        <div v-if="msg.role === 'system'" class="system-message">
          {{ msg.content }}
        </div>
        <!-- 普通消息（用户/AI） -->
        <template v-else>
          <div class="message-avatar">
            <span v-if="msg.role === 'user'">你</span>
            <span v-else>AI</span>
          </div>
          <div class="message-content-wrapper">
            <!-- 用户消息：纯文本显示 -->
            <div v-if="msg.role === 'user'" class="message-content">
              {{ msg.content }}
            </div>
            <!-- AI消息：Markdown渲染 (#3) + 复制按钮 (#11) -->
            <div v-else class="message-content ai-content">
              <div class="markdown-body" v-html="renderMarkdown(msg.content)"></div>
              <button
                class="copy-btn"
                @click="copyMessage(msg.content)"
                :title="'复制内容'"
              >复制</button>
            </div>
          </div>
        </template>
      </div>

      <!-- 加载中动画 -->
      <div v-if="chatStore.isLoading" class="message message-assistant">
        <div class="message-avatar">
          <span>AI</span>
        </div>
        <div class="loading">
          <div class="loading-dot"></div>
          <div class="loading-dot"></div>
          <div class="loading-dot"></div>
        </div>
      </div>
    </div>

    <!-- Token统计面板 -->
    <div class="token-stats-wrapper">
      <div class="token-stats-bar" @click="showTokenPanel = !showTokenPanel">
        <span class="token-stats-bar-icon">{{ showTokenPanel ? '▼' : '▲' }}</span>
        <span>Token 统计</span>
        <span v-if="tokenStats?.total" class="token-stats-bar-summary">
          总计 {{ tokenStats.total.total_tokens || 0 }} Token
        </span>
      </div>
      <div v-if="showTokenPanel" class="token-stats-panel">
        <div v-if="tokenStats" class="token-stats-grid">
          <div
            v-for="agent in agentList"
            :key="agent.key"
            class="token-agent-card"
          >
            <div class="token-agent-header">
              <span class="token-agent-dot" :style="{ background: agent.color }"></span>
              <span class="token-agent-name">{{ agent.label }}</span>
            </div>
            <div class="token-agent-stats">
              <div class="token-stat-item">
                <span class="token-stat-label">调用</span>
                <span class="token-stat-value">{{ (tokenStats[agent.key] && tokenStats[agent.key].calls) || 0 }}</span>
              </div>
              <div class="token-stat-item">
                <span class="token-stat-label">输入</span>
                <span class="token-stat-value">{{ (tokenStats[agent.key] && tokenStats[agent.key].input_tokens) || 0 }}</span>
              </div>
              <div class="token-stat-item">
                <span class="token-stat-label">输出</span>
                <span class="token-stat-value">{{ (tokenStats[agent.key] && tokenStats[agent.key].output_tokens) || 0 }}</span>
              </div>
              <div class="token-stat-item">
                <span class="token-stat-label">总计</span>
                <span class="token-stat-value token-stat-total">{{ (tokenStats[agent.key] && tokenStats[agent.key].total_tokens) || 0 }}</span>
              </div>
            </div>
          </div>
          <!-- 总计行 -->
          <div v-if="tokenStats.total" class="token-total-row">
            <div class="token-total-item">
              <span class="token-stat-label">总调用</span>
              <span class="token-stat-value">{{ tokenStats.total.calls || 0 }}</span>
            </div>
            <div class="token-total-item">
              <span class="token-stat-label">总输入</span>
              <span class="token-stat-value">{{ tokenStats.total.input_tokens || 0 }}</span>
            </div>
            <div class="token-total-item">
              <span class="token-stat-label">总输出</span>
              <span class="token-stat-value">{{ tokenStats.total.output_tokens || 0 }}</span>
            </div>
            <div class="token-total-item token-total-sum">
              <span class="token-stat-label">总Token</span>
              <span class="token-stat-value">{{ tokenStats.total.total_tokens || 0 }}</span>
            </div>
          </div>
        </div>
        <div v-else class="token-stats-empty">暂无 Token 统计数据</div>
      </div>
    </div>

    <div class="chat-input-container">
      <div class="chat-input">
        <textarea
          v-model="inputText"
          placeholder="输入消息..."
          rows="1"
          maxlength="2000"
          @keydown.enter.exact.prevent="sendMessage"
          @input="adjustHeight"
        ></textarea>
        <!-- 消息长度提示 (#6) -->
        <span v-if="inputText.length > 1800" class="char-count">{{ inputText.length }}/2000</span>
        <button class="btn btn-primary" @click="sendMessage" :disabled="chatStore.isLoading || !inputText.trim()">
          发送
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { marked } from 'marked' // Markdown渲染库 (#3)
import { getTokenStats } from '../api'
import { useChatStore } from '../stores/chat'

const chatStore = useChatStore()

const inputText = ref('')

// Token统计面板状态
const showTokenPanel = ref(false)
const tokenStats = ref(null)
const agentList = [
  { key: 'supervisor', label: 'Supervisor（调度器）', color: '#8b5cf6' },
  { key: 'knowledge', label: '知识Agent', color: '#3b82f6' },
  { key: 'weather', label: '天气Agent', color: '#10b981' },
  { key: 'report', label: '报告Agent', color: '#f59e0b' },
  { key: 'direct', label: '直接回复', color: '#ef4444' },
]
const messagesContainer = ref(null)
let autoScrollEnabled = true // 是否启用自动滚动 (#2)

/**
 * 将AI回复的Markdown文本渲染为HTML (#3)
 * 使用marked库解析Markdown语法（标题、列表、加粗、代码块等）
 */
function renderMarkdown(content) {
  if (!content) return ''
  try {
    // 配置marked选项：禁用sanitize以支持HTML标签，开启gfm支持表格等
    return marked.parse(content, { breaks: true, gfm: true })
  } catch (e) {
    console.error('Markdown渲染失败:', e)
    return content
  }
}

/**
 * 复制AI消息内容到剪贴板 (#11)
 * 用户点击复制按钮时调用
 */
async function copyMessage(content) {
  try {
    await navigator.clipboard.writeText(content)
    // 简单的视觉反馈：临时改变按钮文字
    const event = window.event
    const btn = event.target
    const originalText = btn.textContent
    btn.textContent = '已复制!'
    setTimeout(() => { btn.textContent = originalText }, 1500)
  } catch (err) {
    console.error('复制失败:', err)
  }
}

/**
 * 获取 Token 消耗统计数据
 */
async function fetchTokenStats() {
  try {
    const sessionId = chatStore.currentSessionId || null
    const stats = await getTokenStats(sessionId)
    tokenStats.value = stats
  } catch (err) {
    console.error('获取Token统计失败:', err)
  }
}

async function sendMessage() {
  if (!inputText.value.trim() || chatStore.isLoading) return

  const text = inputText.value.trim()
  inputText.value = ''

  await chatStore.sendMessage(text)

  // 发送消息后更新Token统计
  await fetchTokenStats()

  // 发送后自动滚动到底部
  autoScrollEnabled = true
  nextTick(() => scrollToBottom())
}

function adjustHeight(event) {
  const textarea = event.target
  textarea.style.height = 'auto'
  textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px'
}

/**
 * 滚动聊天区域到底部 (#2)
 * 仅在用户未手动向上滚动时自动滚动（避免打断阅读历史消息）
 */
function scrollToBottom(force = false) {
  if (!messagesContainer.value) return

  if (force || autoScrollEnabled) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 监听消息变化，流式输出时自动滚动 (#2)
watch(
  () => chatStore.messages,
  async () => {
    await nextTick()
    scrollToBottom()
  },
  { deep: true }
)

// 监听用户滚动行为，判断是否应停止自动滚动
function handleScroll() {
  if (!messagesContainer.value) return
  const container = messagesContainer.value
  // 距离底部小于100px视为在底部附近，允许自动滚动
  const distanceToBottom = container.scrollHeight - container.scrollTop - container.clientHeight
  autoScrollEnabled = distanceToBottom < 100
}

onMounted(() => {
  nextTick(() => scrollToBottom())
  fetchTokenStats()
  // 绑定滚动事件监听 (#2)
  if (messagesContainer.value) {
    messagesContainer.value.addEventListener('scroll', handleScroll)
  }
})

onUnmounted(() => {
  // 解绑滚动事件监听，防止内存泄漏
  if (messagesContainer.value) {
    messagesContainer.value.removeEventListener('scroll', handleScroll)
  }
})
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

/* 错误提示横幅 */
.error-banner {
  position: fixed;
  top: 0;
  left: 260px;
  right: 0;
  background: #fef2f2;
  color: #dc2626;
  padding: 12px 24px;
  border-bottom: 1px solid #fecaca;
  text-align: center;
  z-index: 100;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding-bottom: 100px;
  padding-top: 50px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100%;
  color: var(--text-secondary);
}

.empty-state h2 {
  font-size: 32px;
  margin-bottom: 16px;
  color: var(--text-primary);
}

.message {
  display: flex;
  gap: 16px;
  padding: 24px;
}

/* 系统消息样式 */
.system-message {
  background: #fef3c7;
  color: #d97706;
  padding: 12px 20px;
  border-radius: 8px;
  text-align: center;
  margin: 16px auto;
  max-width: 60%;
  font-size: 14px;
}

.message-avatar {
  width: 36px;
  height: 36px;
  border-radius: 6px;
  background: var(--text-primary);
  color: var(--bg-primary);
  display: flex;
  justify-content: center;
  align-items: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.message-user .message-avatar {
  background: #10a37f;
}

.message-content-wrapper {
  flex: 1;
  min-width: 0;
}

.message-content {
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

/* AI消息区域样式（含Markdown和复制按钮）(#3, #11) */
.ai-content {
  position: relative;
}

.ai-content:hover .copy-btn {
  opacity: 1;
}

/* Markdown渲染样式 (#3) */
.markdown-body {
  line-height: 1.7;
  word-break: break-word;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3) {
  margin-top: 12px;
  margin-bottom: 6px;
  font-weight: 600;
}

.markdown-body :deep(p) {
  margin: 4px 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 20px;
  margin: 6px 0;
}

.markdown-body :deep(li) {
  margin: 2px 0;
}

.markdown-body :deep(strong) {
  color: var(--text-primary);
  font-weight: 600;
}

.markdown-body :deep(code) {
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 0.9em;
}

/* 复制按钮样式 (#11) */
.copy-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  opacity: 0;
  transition: opacity 0.2s;
  padding: 4px 10px;
  font-size: 12px;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  cursor: pointer;
  color: var(--text-secondary);
}

.copy-btn:hover {
  background: #e5e7eb;
  color: var(--text-primary);
}

.chat-input-container {
  position: fixed;
  bottom: 0;
  left: 260px;
  right: 0;
  background: var(--bg-primary);
  border-top: 1px solid var(--border-color);
}

.chat-input {
  position: relative;
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 12px 24px;
}

.chat-input textarea {
  max-height: 200px;
  flex: 1;
}

/* 字符计数提示 (#6) */
.char-count {
  position: absolute;
  right: 80px;
  bottom: 16px;
  font-size: 11px;
  color: #ef4444;
  pointer-events: none;
}

/* ========== Token统计面板 ========== */
.token-stats-wrapper {
  position: fixed;
  bottom: 78px;
  left: 260px;
  right: 0;
  z-index: 50;
  background: rgba(255, 255, 255, 0.97);
  backdrop-filter: blur(8px);
  border-top: 1px solid var(--border-color);
  box-shadow: 0 -2px 12px rgba(0, 0, 0, 0.06);
}

.token-stats-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  cursor: pointer;
  user-select: none;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  transition: color 0.2s, background 0.2s;
}

.token-stats-bar:hover {
  color: var(--text-primary);
  background: rgba(0, 0, 0, 0.02);
}

.token-stats-bar-icon {
  font-size: 10px;
  transition: transform 0.2s;
}

.token-stats-bar-summary {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-secondary);
}

.token-stats-panel {
  padding: 0 24px 16px;
  max-height: 300px;
  overflow-y: auto;
}

.token-stats-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.token-agent-card {
  flex: 1;
  min-width: 140px;
  max-width: 200px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 10px 12px;
}

.token-agent-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #f3f4f6;
}

.token-agent-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.token-agent-name {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.token-agent-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 8px;
}

.token-stat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
}

.token-stat-label {
  color: var(--text-secondary);
}

.token-stat-value {
  font-weight: 600;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.token-stat-total {
  color: #8b5cf6;
}

/* 总计行 */
.token-total-row {
  display: flex;
  gap: 16px;
  margin-top: 10px;
  padding: 10px 12px;
  background: linear-gradient(135deg, #f5f3ff, #ede9fe);
  border: 1px solid #ddd6fe;
  border-radius: 8px;
}

.token-total-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  font-size: 12px;
}

.token-total-sum {
  margin-left: auto;
  padding-left: 16px;
  border-left: 1px solid #ddd6fe;
}

.token-total-sum .token-stat-value {
  font-size: 15px;
  color: #7c3aed;
}

/* 空状态 */
.token-stats-empty {
  text-align: center;
  padding: 20px 0;
  font-size: 13px;
  color: var(--text-secondary);
}

/* 响应式：小屏幕下调整宽度 */
@media (max-width: 768px) {
  .token-stats-wrapper {
    left: 0;
  }

  .token-agent-card {
    min-width: 120px;
  }
}
</style>
