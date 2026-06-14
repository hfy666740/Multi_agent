<template>
  <div class="login-container">
    <div class="login-card">
      <h1 class="login-title">AI智能客服</h1>
      
      <div class="login-tabs">
        <button 
          class="tab-btn" 
          :class="{ active: mode === 'login' }"
          @click="mode = 'login'"
        >登录</button>
        <button 
          class="tab-btn" 
          :class="{ active: mode === 'register' }"
          @click="mode = 'register'"
        >注册</button>
      </div>

      <form @submit.prevent="handleSubmit">
        <div class="form-group">
          <input 
            v-model="username"
            class="input"
            type="text"
            placeholder="用户名"
            required
          />
        </div>

        <div v-if="mode === 'register'" class="form-group">
          <input 
            v-model="email"
            class="input"
            type="email"
            placeholder="邮箱"
            required
          />
        </div>

        <div class="form-group">
          <input 
            v-model="password"
            class="input"
            type="password"
            placeholder="密码"
            required
          />
        </div>

        <div v-if="error" class="error-message">{{ error }}</div>

        <button class="btn btn-primary login-btn" type="submit" :disabled="loading">
          {{ loading ? '处理中...' : (mode === 'login' ? '登录' : '注册') }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const mode = ref('login')
const username = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleSubmit() {
  error.value = ''
  loading.value = true

  try {
    let res
    if (mode.value === 'login') {
      res = await authStore.login(username.value, password.value)
    } else {
      res = await authStore.register(username.value, email.value, password.value)
    }

    if (res.success) {
      if (mode.value === 'register') {
        mode.value = 'login'
        error.value = '注册成功，请登录'
      } else {
        router.push('/')
      }
    } else {
      error.value = res.message || '操作失败'
    }
  } catch (err) {
    error.value = err.detail || '网络错误'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background: var(--bg-secondary);
}

.login-card {
  width: 400px;
  padding: 32px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
}

.login-title {
  text-align: center;
  font-size: 24px;
  margin-bottom: 24px;
}

.login-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
}

.tab-btn {
  flex: 1;
  padding: 10px;
  border: none;
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.tab-btn:hover {
  background: var(--bg-hover);
}

.tab-btn.active {
  background: var(--text-primary);
  color: var(--bg-primary);
}

.form-group {
  margin-bottom: 16px;
}

.error-message {
  color: #ef4444;
  font-size: 14px;
  margin-bottom: 16px;
  text-align: center;
}

.login-btn {
  width: 100%;
}
</style>