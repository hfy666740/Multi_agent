<template>
  <div class="knowledge-container">
    <div class="knowledge-header">
      <h1>知识库管理</h1>
      <button class="btn btn-primary" @click="reloadKnowledge" :disabled="loading">
        {{ loading ? '加载中...' : '重新加载知识库' }}
      </button>
    </div>

    <div class="knowledge-content">
      <div class="knowledge-list">
        <div class="knowledge-title">知识库文件列表</div>
        
        <div v-if="files.length === 0" class="empty-state">
          暂无知识库文件
        </div>

        <div 
          v-for="file in files" 
          :key="file"
          class="card knowledge-item"
        >
          <div class="file-info">
            <span class="file-name">{{ file }}</span>
          </div>
          <button class="btn btn-danger" @click="deleteFile(file)">删除</button>
        </div>
      </div>

      <div class="upload-section">
        <div class="knowledge-title">上传新文件</div>
        <div class="upload-area">
          <input 
            type="file" 
            ref="fileInput"
            @change="handleFileSelect"
            accept=".txt,.pdf,.csv"
            style="display: none"
          />
          <button class="btn" @click="$refs.fileInput.click()">选择文件</button>
          <span v-if="selectedFile" class="selected-file">{{ selectedFile.name }}</span>
        </div>
        <button 
          class="btn btn-primary" 
          @click="uploadFile" 
          :disabled="!selectedFile || uploading"
        >
          {{ uploading ? '上传中...' : '上传文件' }}
        </button>
      </div>
    </div>

    <div v-if="message" class="message-toast" :class="messageType">
      {{ message }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { knowledgeApi } from '../api'

const files = ref([])
const loading = ref(false)
const uploading = ref(false)
const selectedFile = ref(null)
const message = ref('')
const messageType = ref('success')

onMounted(async () => {
  await loadFiles()
})

async function loadFiles() {
  try {
    const res = await knowledgeApi.getFiles()
    files.value = res.files || []
  } catch (err) {
    showMessage('加载文件列表失败', 'error')
  }
}

async function reloadKnowledge() {
  loading.value = true
  try {
    await knowledgeApi.reload()
    showMessage('知识库重新加载成功', 'success')
  } catch (err) {
    showMessage('重新加载失败', 'error')
  } finally {
    loading.value = false
  }
}

async function deleteFile(filename) {
  if (!confirm(`确定删除文件 ${filename}？`)) return
  
  try {
    await knowledgeApi.deleteFile(filename)
    showMessage('文件删除成功', 'success')
    await loadFiles()
  } catch (err) {
    showMessage('删除失败', 'error')
  }
}

function handleFileSelect(event) {
  selectedFile.value = event.target.files[0]
}

async function uploadFile() {
  if (!selectedFile.value) return
  
  uploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    
    await fetch('/api/knowledge/upload', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      },
      body: formData
    })
    
    showMessage('文件上传成功', 'success')
    selectedFile.value = null
    await loadFiles()
  } catch (err) {
    showMessage('上传失败', 'error')
  } finally {
    uploading.value = false
  }
}

function showMessage(text, type) {
  message.value = text
  messageType.value = type
  setTimeout(() => {
    message.value = ''
  }, 3000)
}
</script>

<style scoped>
.knowledge-container {
  padding: 24px;
  max-width: 800px;
  margin: 0 auto;
}

.knowledge-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.knowledge-header h1 {
  font-size: 24px;
}

.knowledge-content {
  display: flex;
  gap: 24px;
}

.knowledge-list {
  flex: 1;
}

.knowledge-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.knowledge-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-name {
  font-size: 14px;
}

.upload-section {
  width: 300px;
  padding: 24px;
  background: var(--bg-secondary);
  border-radius: 8px;
}

.upload-area {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.selected-file {
  font-size: 14px;
  color: var(--text-secondary);
}

.empty-state {
  color: var(--text-secondary);
  text-align: center;
  padding: 24px;
}

.message-toast {
  position: fixed;
  top: 24px;
  right: 24px;
  padding: 12px 24px;
  border-radius: 6px;
  animation: fadeIn 0.3s ease;
}

.message-toast.success {
  background: #10a37f;
  color: white;
}

.message-toast.error {
  background: #ef4444;
  color: white;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>