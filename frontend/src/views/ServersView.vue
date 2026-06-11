<template>
  <div class="servers-container">
    <div class="page-header">
      <h2>服务器管理</h2>
      <button @click="showForm = true; editing = null; resetForm()" class="add-btn">添加服务器</button>
    </div>

    <!-- Server list -->
    <div class="table-container" v-if="!showForm">
      <table v-if="servers.length > 0">
        <thead>
          <tr>
            <th>ID</th><th>名称</th><th>地址</th><th>端口</th><th>系统</th>
            <th>用户</th><th>备注</th><th>状态</th><th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in servers" :key="s.id">
            <td>{{ s.id }}</td>
            <td>{{ s.name }}</td>
            <td>{{ s.host }}</td>
            <td>{{ s.port }}</td>
            <td>{{ s.os_type === 'linux' ? 'Linux' : 'Windows' }}</td>
            <td>{{ s.username }}</td>
            <td>{{ s.description || '-' }}</td>
            <td>
              <span :class="['badge', s.is_active ? 'badge-on' : 'badge-off']">
                {{ s.is_active ? '启用' : '禁用' }}
              </span>
            </td>
            <td class="actions">
              <button @click="handleTest(s.id)" class="btn-sm btn-outline" :disabled="testingId === s.id">
                {{ testingId === s.id ? '测试中' : '测试' }}
              </button>
              <button @click="editServer(s)" class="btn-sm btn-outline">编辑</button>
              <button @click="handleDelete(s.id)" class="btn-sm btn-danger">删除</button>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">
        <div class="empty-icon">🖥️</div>
        <p class="empty-title">还没有添加任何服务器</p>
        <p class="empty-desc">添加你要管理的 Linux 或 Windows 服务器</p>
        <button @click="showForm = true; editing = null; resetForm()" class="add-btn-empty">+ 添加服务器</button>
      </div>
    </div>

    <!-- Add/Edit form -->
    <div class="form-card" v-if="showForm">
      <h3>{{ editing ? '编辑服务器' : '添加服务器' }}</h3>
      <form @submit.prevent="handleSave">
        <div class="form-row">
          <label>名称</label>
          <input v-model="form.name" required placeholder="如：生产Web服务器" />
        </div>
        <div class="form-row">
          <label>IP地址</label>
          <input v-model="form.host" required placeholder="如：192.168.1.10" />
        </div>
        <div class="form-row cols-2">
          <div>
            <label>端口</label>
            <input v-model.number="form.port" type="number" required />
          </div>
          <div>
            <label>操作系统</label>
            <select v-model="form.os_type">
              <option value="linux">Linux</option>
              <option value="windows">Windows</option>
            </select>
          </div>
        </div>
        <div class="form-row cols-2">
          <div>
            <label>用户名</label>
            <input v-model="form.username" required placeholder="root / Administrator" />
          </div>
          <div>
            <label>密码</label>
            <input v-model="form.password" type="password" required />
          </div>
        </div>
        <div class="form-row">
          <label>备注</label>
          <input v-model="form.description" placeholder="可选" />
        </div>
        <div class="form-actions">
          <button type="button" @click="showForm = false" class="btn-cancel">取消</button>
          <button type="submit" class="btn-save" :disabled="saving">
            {{ saving ? '保存中...' : '保存' }}
          </button>
        </div>
      </form>
    </div>

    <!-- Test result -->
    <div v-if="testResult" class="test-result" :class="testResult.connected ? 'success' : 'fail'">
      {{ testResult.message || (testResult.connected ? '连接成功' : '连接失败') }}
      <button @click="testResult = null" class="close-btn">&times;</button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getServers, createServer, updateServer, deleteServer, testServer } from '../api'

const servers = ref([])
const showForm = ref(false)
const editing = ref(null)
const saving = ref(false)
const testingId = ref(null)
const testResult = ref(null)

const defaultForm = () => ({
  name: '', host: '', port: 22, os_type: 'linux',
  username: 'root', password: '', description: '',
})
const form = ref(defaultForm())

function resetForm() {
  form.value = defaultForm()
}

onMounted(async () => {
  try {
    const res = await getServers()
    servers.value = res.data
  } catch (e) {
    console.error(e)
  }
})

function editServer(s) {
  editing.value = s
  form.value = {
    name: s.name, host: s.host, port: s.port, os_type: s.os_type,
    username: s.username, password: '', description: s.description || '',
  }
  showForm.value = true
}

async function handleSave() {
  saving.value = true
  try {
    if (editing.value) {
      const data = { ...form.value }
      if (!data.password) delete data.password
      await updateServer(editing.value.id, data)
    } else {
      await createServer(form.value)
    }
    const res = await getServers()
    servers.value = res.data
    showForm.value = false
  } catch (e) {
    alert('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

async function handleTest(id) {
  testingId.value = id
  try {
    const res = await testServer(id)
    testResult.value = res.data
  } catch (e) {
    testResult.value = { connected: false, message: '测试失败' }
  } finally {
    testingId.value = null
  }
}

async function handleDelete(id) {
  if (!confirm('确定要删除这台服务器吗？')) return
  try {
    await deleteServer(id)
    servers.value = servers.value.filter(s => s.id !== id)
  } catch (e) {
    alert('删除失败')
  }
}
</script>

<style scoped>
.servers-container {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  height: 100vh;
  overflow-y: auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.add-btn {
  padding: 10px 20px;
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
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

.actions {
  display: flex;
  gap: 6px;
}

.btn-sm {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid #ddd;
  background: #fff;
}

.btn-danger {
  color: #e74c3c;
  border-color: #e74c3c;
}

.btn-danger:hover {
  background: #e74c3c;
  color: #fff;
}

.badge {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
}

.badge-on {
  background: #e6f7e6;
  color: #34a853;
}

.badge-off {
  background: #fce8e6;
  color: #ea4335;
}

.form-card {
  background: #fff;
  padding: 24px;
  border-radius: 8px;
  max-width: 600px;
}

.form-row {
  margin-bottom: 16px;
}

.form-row label {
  display: block;
  margin-bottom: 6px;
  font-weight: 500;
  font-size: 14px;
}

.form-row input,
.form-row select {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 6px;
  font-size: 14px;
}

.cols-2 {
  display: flex;
  gap: 16px;
}

.cols-2 > div {
  flex: 1;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
}

.btn-save {
  padding: 10px 24px;
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.btn-cancel {
  padding: 10px 24px;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
}

.empty {
  text-align: center;
  padding: 80px 20px;
  color: #999;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 20px;
  color: #333;
  font-weight: 600;
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: #999;
  margin-bottom: 24px;
}

.add-btn-empty {
  padding: 14px 36px;
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  font-weight: 600;
}

.add-btn-empty:hover {
  background: #1557b0;
}

.test-result {
  margin-top: 16px;
  padding: 12px 16px;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.test-result.success {
  background: #e6f7e6;
  color: #34a853;
}

.test-result.fail {
  background: #fce8e6;
  color: #ea4335;
}

.close-btn {
  background: none;
  border: none;
  font-size: 20px;
  cursor: pointer;
}
</style>
