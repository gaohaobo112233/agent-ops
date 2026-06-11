<template>
  <div class="login-container">
    <div class="login-card">
      <h1>自动化运维Agent</h1>
      <p class="subtitle">请登录以继续</p>
      <form @submit.prevent="handleLogin">
        <input v-model="username" type="text" placeholder="用户名" class="input" />
        <input v-model="password" type="password" placeholder="密码" class="input" />
        <p v-if="error" class="error">{{ error }}</p>
        <button type="submit" class="btn" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../api'

const router = useRouter()
const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    const res = await login(username.value, password.value)
    localStorage.setItem('token', res.data.token)
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.login-card {
  background: #fff;
  padding: 48px 40px;
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
  width: 400px;
}

.login-card h1 {
  font-size: 24px;
  text-align: center;
  margin-bottom: 8px;
}

.subtitle {
  text-align: center;
  color: #999;
  margin-bottom: 32px;
}

.input {
  width: 100%;
  padding: 12px 16px;
  margin-bottom: 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 15px;
}

.input:focus {
  outline: none;
  border-color: #1a73e8;
}

.error {
  color: #e74c3c;
  margin-bottom: 12px;
  font-size: 14px;
}

.btn {
  width: 100%;
  padding: 12px;
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
}

.btn:hover {
  background: #1557b0;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
