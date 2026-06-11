<template>
  <div class="monitor-container">
    <div class="page-header">
      <h2>监控仪表盘</h2>
      <span class="prom-status" :class="promConnected ? 'connected' : 'disconnected'">
        {{ promConnected ? 'Prometheus 已连接' : 'Prometheus 未连接' }}
      </span>
    </div>

    <!-- Quick metrics -->
    <div class="metric-cards">
      <div class="metric-card" v-for="m in quickMetrics" :key="m.title" @click="queryMetric(m)">
        <div class="card-title">{{ m.title }}</div>
        <div class="card-desc">{{ m.desc }}</div>
        <div class="card-loading" v-if="m.loading">查询中...</div>
        <div class="card-result" v-if="m.result !== null">
          <span class="card-value">{{ m.result }}</span>
          <span class="card-unit">{{ m.unit }}</span>
        </div>
        <div class="card-error" v-if="m.error">{{ m.error }}</div>
      </div>
    </div>

    <!-- Targets section -->
    <div class="section">
      <div class="section-header">
        <h3>监控目标 (Targets)</h3>
        <button @click="loadTargets" class="refresh-btn" :disabled="loadingTargets">
          {{ loadingTargets ? '加载中...' : '刷新' }}
        </button>
      </div>
      <div class="table-container" v-if="targets.length > 0">
        <table>
          <thead>
            <tr>
              <th>实例</th><th>地址</th><th>健康状态</th><th>最后采集</th><th>采集耗时</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in targets" :key="t.scrapeUrl">
              <td>{{ t.labels?.instance || t.scrapeUrl }}</td>
              <td>{{ t.scrapeUrl }}</td>
              <td>
                <span :class="['badge', t.health === 'up' ? 'badge-on' : 'badge-off']">
                  {{ t.health === 'up' ? '正常' : '异常' }}
                </span>
              </td>
              <td>{{ t.lastScrape || '-' }}</td>
              <td>{{ t.lastScrapeDuration ? (t.lastScrapeDuration * 1000).toFixed(0) + 'ms' : '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-hint">点击刷新加载监控目标</div>
    </div>

    <!-- Custom query -->
    <div class="section">
      <div class="section-header"><h3>自定义 PromQL 查询</h3></div>
      <div class="query-box">
        <textarea v-model="customQuery" placeholder="输入 PromQL，如: node_cpu_seconds_total" rows="2"></textarea>
        <button @click="runCustomQuery" class="query-btn" :disabled="queryLoading">
          {{ queryLoading ? '查询中...' : '查询' }}
        </button>
      </div>
      <pre class="query-result" v-if="customResult">{{ JSON.stringify(customResult, null, 2).slice(0, 2000) }}</pre>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const promConnected = ref(false)

// Quick metric cards
const quickMetrics = ref([
  { title: 'CPU 使用率', desc: '所有节点平均 CPU 使用率', promql: '100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)', unit: '%', loading: false, result: null, error: null },
  { title: '内存使用率', desc: '所有节点平均内存使用率', promql: '(1 - (avg(node_memory_MemAvailable_bytes) / avg(node_memory_MemTotal_bytes))) * 100', unit: '%', loading: false, result: null, error: null },
  { title: '磁盘使用率', desc: '根分区磁盘使用率', promql: '(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) * 100', unit: '%', loading: false, result: null, error: null },
  { title: '系统负载 (1m)', desc: '所有节点平均1分钟负载', promql: 'avg(node_load1)', unit: '', loading: false, result: null, error: null },
  { title: '在线节点数', desc: '当前 scrape 正常的节点数量', promql: 'count(up == 1)', unit: '台', loading: false, result: null, error: null },
  { title: '总内存', desc: '所有节点总内存', promql: 'sum(node_memory_MemTotal_bytes) / 1073741824', unit: 'GB', loading: false, result: null, error: null },
])

async function queryMetric(m) {
  m.loading = true
  m.error = null
  m.result = null
  try {
    const res = await api.post('/monitor/query', { query: m.promql, query_type: 'instant' })
    const data = res.data
    if (data.success && data.data?.data?.result?.length > 0) {
      const val = data.data.data.result[0].value?.[1]
      if (val !== undefined) {
        m.result = parseFloat(val).toFixed(1)
      } else {
        m.error = '无数据'
      }
    } else {
      m.error = data.error || '无数据'
    }
  } catch (e) {
    m.error = '连接失败'
  } finally {
    m.loading = false
  }
}

// Targets
const targets = ref([])
const loadingTargets = ref(false)

async function loadTargets() {
  loadingTargets.value = true
  try {
    const res = await api.get('/monitor/targets')
    if (res.data.success) {
      const allTargets = []
      for (const group of (res.data.data?.data?.activeTargets || [])) {
        allTargets.push(group)
      }
      targets.value = allTargets
      promConnected.value = true
    }
  } catch (e) {
    promConnected.value = false
  } finally {
    loadingTargets.value = false
  }
}

// Custom query
const customQuery = ref('')
const customResult = ref(null)
const queryLoading = ref(false)

async function runCustomQuery() {
  if (!customQuery.value.trim()) return
  queryLoading.value = true
  try {
    const res = await api.post('/monitor/query', { query: customQuery.value, query_type: 'instant' })
    customResult.value = res.data
  } catch (e) {
    customResult.value = { error: '查询失败: ' + e.message }
  } finally {
    queryLoading.value = false
  }
}

onMounted(() => {
  loadTargets()
})
</script>

<style scoped>
.monitor-container {
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

.prom-status {
  padding: 6px 14px;
  border-radius: 12px;
  font-size: 13px;
  font-weight: 500;
}

.prom-status.connected {
  background: #e6f7e6;
  color: #34a853;
}

.prom-status.disconnected {
  background: #fce8e6;
  color: #ea4335;
}

.metric-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.metric-card {
  background: #fff;
  border: 1px solid #eee;
  border-radius: 10px;
  padding: 20px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}

.metric-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}

.card-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 4px;
}

.card-desc {
  font-size: 12px;
  color: #999;
  margin-bottom: 12px;
}

.card-loading {
  color: #1a73e8;
  font-size: 13px;
}

.card-result {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.card-value {
  font-size: 32px;
  font-weight: 700;
  color: #1a73e8;
}

.card-unit {
  font-size: 14px;
  color: #999;
}

.card-error {
  color: #ea4335;
  font-size: 13px;
}

.section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.refresh-btn {
  padding: 6px 16px;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 6px;
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
  padding: 10px 14px;
  text-align: left;
  border-bottom: 1px solid #eee;
  font-size: 13px;
}

th {
  background: #f8f9fa;
  font-weight: 600;
  color: #666;
}

.badge {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 12px;
}

.badge-on { background: #e6f7e6; color: #34a853; }
.badge-off { background: #fce8e6; color: #ea4335; }

.empty-hint {
  text-align: center;
  padding: 40px;
  color: #999;
}

.query-box {
  display: flex;
  gap: 12px;
}

.query-box textarea {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  font-family: monospace;
  resize: none;
}

.query-btn {
  padding: 0 24px;
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
}

.query-result {
  background: #1a1a2e;
  color: #eee;
  padding: 14px;
  border-radius: 8px;
  margin-top: 12px;
  font-size: 12px;
  max-height: 300px;
  overflow-y: auto;
  white-space: pre-wrap;
}
</style>
