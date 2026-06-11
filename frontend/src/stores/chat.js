import { defineStore } from 'pinia'
import { ref } from 'vue'
import { sendMessage, executeMessage } from '../api'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const loading = ref(false)

  function addMessage(role, content, toolCalls = [], needsApproval = false, msgId = null, taskId = null) {
    messages.value.push({
      id: msgId || Date.now(),
      role,
      content,
      toolCalls,
      needsApproval,
      taskId,
      time: new Date().toLocaleTimeString(),
    })
  }

  async function send(msg) {
    addMessage('user', msg)
    loading.value = true
    try {
      const res = await sendMessage(msg) // default: preview mode
      const data = res.data
      addMessage('assistant', data.reply, data.tool_calls || [], data.needs_approval, null, data.task_id)
      return data
    } catch (e) {
      addMessage('assistant', '请求失败: ' + (e.response?.data?.detail || e.message))
    } finally {
      loading.value = false
    }
  }

  async function approve(msgId) {
    // Find the user message that triggered this preview
    const idx = messages.value.findIndex(m => m.id === msgId)
    if (idx < 0) return

    const userMsg = messages.value[idx - 1] // User's original request
    if (!userMsg || userMsg.role !== 'user') return

    loading.value = true
    try {
      const res = await executeMessage(userMsg.content) // action: "execute"
      addMessage('assistant', res.data.reply, res.data.tool_calls || [], false, null, res.data.task_id)
      return res.data
    } catch (e) {
      addMessage('assistant', '执行失败: ' + (e.response?.data?.detail || e.message))
    } finally {
      loading.value = false
    }
  }

  function clearMessages() {
    messages.value = []
  }

  return { messages, loading, send, approve, addMessage, clearMessages }
})
