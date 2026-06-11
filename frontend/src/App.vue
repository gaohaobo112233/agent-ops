<template>
  <div id="app-container">
    <nav class="sidebar" v-if="isLoggedIn">
      <div class="logo">运维Agent</div>
      <router-link to="/" class="nav-item">
        <span>&#128172;</span> 智能对话
      </router-link>
      <router-link to="/servers" class="nav-item">
        <span>&#128421;</span> 服务器管理
      </router-link>
      <router-link to="/monitor" class="nav-item">
        <span>&#128200;</span> 监控仪表盘
      </router-link>
      <router-link to="/tasks" class="nav-item">
        <span>&#128337;</span> 任务历史
      </router-link>
      <div class="nav-bottom">
        <button @click="logout" class="logout-btn">退出登录</button>
      </div>
    </nav>
    <main :class="{ 'with-sidebar': isLoggedIn }">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const isLoggedIn = computed(() => !!localStorage.getItem('token'))

function logout() {
  localStorage.removeItem('token')
  router.push('/login')
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
    'Helvetica Neue', Arial, sans-serif;
  background: #f0f2f5;
  color: #333;
}

#app-container {
  display: flex;
  height: 100vh;
}

.sidebar {
  width: 220px;
  background: #1a1a2e;
  color: #eee;
  display: flex;
  flex-direction: column;
  padding: 20px 0;
}

.logo {
  font-size: 20px;
  font-weight: 700;
  padding: 0 20px 24px;
  border-bottom: 1px solid #333;
  margin-bottom: 12px;
}

.nav-item {
  color: #ccc;
  text-decoration: none;
  padding: 12px 20px;
  font-size: 15px;
  transition: background 0.2s;
}

.nav-item:hover,
.nav-item.router-link-active {
  background: #16213e;
  color: #fff;
}

.nav-bottom {
  margin-top: auto;
  padding: 0 20px;
}

.logout-btn {
  width: 100%;
  padding: 10px;
  border: 1px solid #555;
  background: transparent;
  color: #ccc;
  border-radius: 6px;
  cursor: pointer;
}

.logout-btn:hover {
  background: #333;
  color: #fff;
}

main {
  flex: 1;
  overflow: hidden;
}

main.with-sidebar {
  padding: 0;
}
</style>
