import { defineStore } from 'pinia'
import { ref } from 'vue'
import { sendMessage } from '../api'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const loading = ref(false)

  function addMessage(role, content, toolCalls = []) {
    messages.value.push({
      id: Date.now(),
      role,
      content,
      toolCalls,
      time: new Date().toLocaleTimeString(),
    })
  }

  async function send(msg) {
    addMessage('user', msg)
    loading.value = true
    try {
      const res = await sendMessage(msg)
      addMessage('assistant', res.data.reply, res.data.tool_calls || [])
      return res.data
    } catch (e) {
      addMessage('assistant', `请求失败: ${e.response?.data?.detail || e.message}`)
    } finally {
      loading.value = false
    }
  }

  function clearMessages() {
    messages.value = []
  }

  return { messages, loading, send, addMessage, clearMessages }
})
