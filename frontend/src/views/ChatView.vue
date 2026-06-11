<template>
  <div class="chat-container">
    <div class="chat-header">
      <h2>智能运维对话</h2>
      <button @click="store.clearMessages()" class="clear-btn">清空对话</button>
    </div>

    <div class="chat-messages" ref="msgContainer">
      <div v-if="store.messages.length === 0" class="welcome">
        <div class="welcome-icon">&#9881;</div>
        <h3>你好，我是运维智能助手</h3>
        <p>你可以用自然语言给我下达运维指令，例如：</p>
        <div class="examples">
          <div v-for="ex in examples" :key="ex" class="example-item" @click="sendExample(ex)">
            {{ ex }}
          </div>
        </div>
      </div>

      <div v-for="msg in store.messages" :key="msg.id"
           :class="['message', msg.role === 'user' ? 'msg-user' : 'msg-assistant']">
        <div class="msg-avatar">{{ msg.role === 'user' ? 'U' : 'AI' }}</div>
        <div class="msg-body">
          <div class="msg-content" v-html="renderContent(msg.content)"></div>
          <div v-if="msg.toolCalls && msg.toolCalls.length > 0" class="tool-calls">
            <div v-for="(tc, i) in msg.toolCalls" :key="i" class="tool-call">
              <div class="tc-header">
                <span class="tc-tool">{{ tc.tool }}</span>
                <span v-if="tc.blocked" class="tc-blocked">已拦截</span>
              </div>
              <div class="tc-args">
                <strong>参数:</strong> {{ formatArgs(tc.args) }}
              </div>
              <div class="tc-result" v-if="tc.result">
                <strong>结果:</strong>
                <pre>{{ formatResult(tc.result) }}</pre>
              </div>
            </div>
          </div>
          <div class="msg-time">{{ msg.time }}</div>
        </div>
      </div>

      <div v-if="store.loading" class="message msg-assistant">
        <div class="msg-avatar">AI</div>
        <div class="msg-body">
          <div class="typing">正在思考中...</div>
        </div>
      </div>
    </div>

    <div class="chat-input">
      <textarea
        v-model="inputText"
        @keydown.enter.exact.prevent="handleSend"
        placeholder="输入运维指令，如：检查 192.168.1.10 服务器磁盘空间"
        rows="2"
        :disabled="store.loading"
      ></textarea>
      <button @click="handleSend" :disabled="store.loading || !inputText.trim()" class="send-btn">
        发送
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted } from 'vue'
import { useChatStore } from '../stores/chat'

const store = useChatStore()
const inputText = ref('')
const msgContainer = ref(null)

const examples = [
  '帮我检查本地服务器 CPU 和内存使用情况',
  '巡检所有磁盘空间，超过 80% 的告警',
  '检查 80 和 443 端口是否开放',
]

function scrollBottom() {
  nextTick(() => {
    if (msgContainer.value) {
      msgContainer.value.scrollTop = msgContainer.value.scrollHeight
    }
  })
}

watch(() => store.messages.length, scrollBottom)

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || store.loading) return
  inputText.value = ''
  await store.send(text)
  scrollBottom()
}

function sendExample(text) {
  inputText.value = text
  handleSend()
}

function renderContent(text) {
  if (!text) return ''
  return text
    .replace(/\n/g, '<br>')
    .replace(/`{3}(\w*)\n?([\s\S]*?)`{3}/g, '<pre><code>$2</code></pre>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
}

function formatArgs(args) {
  if (!args) return ''
  if (typeof args === 'string') return args
  return Object.entries(args)
    .map(([k, v]) => `${k}=${v}`)
    .join(', ')
}

function formatResult(result) {
  if (!result) return ''
  if (typeof result === 'string') return result
  const r = { ...result }
  delete r.success
  if (r.stdout) return r.stdout.slice(0, 500)
  return JSON.stringify(r, null, 2).slice(0, 500)
}
</script>

<style scoped>
.chat-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #fff;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 24px;
  border-bottom: 1px solid #eee;
}

.chat-header h2 {
  font-size: 18px;
}

.clear-btn {
  padding: 6px 16px;
  border: 1px solid #ddd;
  background: #fff;
  border-radius: 6px;
  cursor: pointer;
}

.clear-btn:hover {
  background: #f5f5f5;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

.welcome {
  text-align: center;
  margin-top: 80px;
}

.welcome-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.welcome h3 {
  font-size: 22px;
  margin-bottom: 8px;
}

.welcome p {
  color: #888;
  margin-bottom: 20px;
}

.examples {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.example-item {
  background: #f0f7ff;
  color: #1a73e8;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.example-item:hover {
  background: #dceeff;
}

.message {
  display: flex;
  margin-bottom: 20px;
}

.msg-user {
  flex-direction: row-reverse;
}

.msg-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  flex-shrink: 0;
}

.msg-assistant .msg-avatar {
  background: #1a73e8;
  color: #fff;
  margin-right: 12px;
}

.msg-user .msg-avatar {
  background: #34a853;
  color: #fff;
  margin-left: 12px;
}

.msg-body {
  max-width: 75%;
}

.msg-user .msg-body {
  text-align: right;
}

.msg-content {
  display: inline-block;
  background: #f0f2f5;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 15px;
  line-height: 1.6;
}

.msg-user .msg-content {
  background: #1a73e8;
  color: #fff;
}

.msg-content :deep(code) {
  background: rgba(0, 0, 0, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.msg-content :deep(pre) {
  background: #1a1a2e;
  color: #eee;
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 8px 0;
  font-size: 13px;
}

.tool-calls {
  margin-top: 8px;
}

.tool-call {
  background: #fffbf0;
  border: 1px solid #f0d060;
  border-radius: 8px;
  padding: 10px 14px;
  margin-bottom: 6px;
  text-align: left;
}

.tc-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.tc-tool {
  font-weight: 600;
  color: #b8860b;
  font-size: 13px;
}

.tc-blocked {
  background: #e74c3c;
  color: #fff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.tc-args,
.tc-result {
  font-size: 13px;
  color: #666;
  margin-top: 4px;
}

.tc-result pre {
  background: #f8f8f8;
  padding: 8px;
  border-radius: 4px;
  font-size: 12px;
  max-height: 150px;
  overflow-y: auto;
  white-space: pre-wrap;
}

.msg-time {
  font-size: 12px;
  color: #bbb;
  margin-top: 4px;
}

.typing {
  background: #f0f2f5;
  padding: 12px 16px;
  border-radius: 12px;
  color: #999;
  font-size: 14px;
}

.chat-input {
  display: flex;
  padding: 16px 24px;
  border-top: 1px solid #eee;
  gap: 12px;
}

.chat-input textarea {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 15px;
  resize: none;
  font-family: inherit;
}

.chat-input textarea:focus {
  outline: none;
  border-color: #1a73e8;
}

.send-btn {
  padding: 0 28px;
  background: #1a73e8;
  color: #fff;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  cursor: pointer;
  white-space: nowrap;
}

.send-btn:hover {
  background: #1557b0;
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
