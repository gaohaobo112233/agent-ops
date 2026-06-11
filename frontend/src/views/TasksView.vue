<template>
  <div class="tasks-container">
    <h2>任务历史</h2>

    <div class="table-container" v-if="tasks.length > 0">
      <table>
        <thead>
          <tr>
            <th>ID</th><th>用户输入</th><th>状态</th><th>时间</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="t in tasks" :key="t.id">
            <td>{{ t.id }}</td>
            <td class="input-cell">{{ t.user_input }}</td>
            <td>
              <span :class="['badge', statusClass(t.status)]">{{ statusLabel(t.status) }}</span>
            </td>
            <td>{{ formatTime(t.created_at) }}</td>
            <td>
              <button @click="viewDetail(t)" class="btn-sm">详情</button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="pager">
        <button @click="changePage(-1)" :disabled="page <= 1">上一页</button>
        <span>第 {{ page }} 页</span>
        <button @click="changePage(1)" :disabled="tasks.length < pageSize">下一页</button>
      </div>
    </div>

    <div v-else class="empty">暂无任务记录</div>

    <!-- Detail dialog -->
    <div v-if="detail" class="modal-mask" @click.self="detail = null">
      <div class="modal">
        <h3>任务详情 #{{ detail.id }}</h3>
        <div class="detail-section">
          <strong>用户输入</strong>
          <p>{{ detail.user_input }}</p>
        </div>
        <div class="detail-section">
          <strong>AI 回复</strong>
          <p>{{ detail.llm_response || '(无)' }}</p>
        </div>
        <div class="detail-section" v-if="detail.tool_calls && detail.tool_calls.length">
          <strong>工具调用</strong>
          <pre>{{ JSON.stringify(detail.tool_calls, null, 2) }}</pre>
        </div>
        <div class="detail-section" v-if="detail.error_message">
          <strong>错误信息</strong>
          <p class="error-msg">{{ detail.error_message }}</p>
        </div>
        <button @click="detail = null" class="btn-close">关闭</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getTasks } from '../api'

const tasks = ref([])
const page = ref(1)
const pageSize = 20
const detail = ref(null)

onMounted(() => loadTasks())

async function loadTasks() {
  try {
    const res = await getTasks(page.value, pageSize)
    tasks.value = res.data
  } catch (e) {
    console.error(e)
  }
}

function changePage(delta) {
  page.value += delta
  loadTasks()
}

function statusClass(s) {
  const map = { completed: 'badge-ok', failed: 'badge-err', running: 'badge-run',
                pending: 'badge-pen', approval_required: 'badge-warn' }
  return map[s] || ''
}

function statusLabel(s) {
  const map = { completed: '成功', failed: '失败', running: '运行中',
                pending: '等待中', approval_required: '需审批' }
  return map[s] || s
}

function formatTime(t) {
  if (!t) return '-'
  return new Date(t).toLocaleString('zh-CN')
}

function viewDetail(t) {
  detail.value = t
}
</script>

<style scoped>
.tasks-container {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  height: 100vh;
  overflow-y: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
}

th, td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid #eee;
}

th {
  background: #f8f9fa;
  font-weight: 600;
  font-size: 13px;
  color: #666;
}

.input-cell {
  max-width: 300px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.badge {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
}

.badge-ok { background: #e6f7e6; color: #34a853; }
.badge-err { background: #fce8e6; color: #ea4335; }
.badge-run { background: #e8f0fe; color: #1a73e8; }
.badge-pen { background: #fef7e0; color: #f9ab00; }
.badge-warn { background: #fce8e6; color: #e67e22; }

.btn-sm {
  padding: 4px 12px;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}

.pager {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
  margin-top: 20px;
}

.pager button {
  padding: 6px 16px;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
}

.pager button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.empty {
  text-align: center;
  padding: 60px;
  color: #999;
}

.modal-mask {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  max-width: 640px;
  width: 90%;
  max-height: 80vh;
  overflow-y: auto;
}

.detail-section {
  margin-bottom: 16px;
}

.detail-section strong {
  display: block;
  margin-bottom: 4px;
  font-size: 13px;
  color: #888;
}

.detail-section pre {
  background: #f8f8f8;
  padding: 12px;
  border-radius: 6px;
  font-size: 12px;
  overflow-x: auto;
}

.error-msg { color: #e74c3c; }

.btn-close {
  padding: 8px 24px;
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  margin-top: 12px;
}
</style>
