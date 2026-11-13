<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { getHealth, uploadDocument, updateMetadata, sendChat } from './api'

const USE_BACKEND = true
const POLL_INTERVAL = 5000

const selectedFile = ref(null)
const importing = ref(false)
const importNotice = ref('')
let noticeTimer = null
const fileInputEl = ref(null)

const showDetail = ref(false)
const detailDoc = ref({
  document_id: '',
  metadata: {},
  chunks: [],
})
const metaDraft = ref({})
const customMeta = ref([])
const savingMeta = ref(false)
const chunksExpanded = ref(false)
const CHUNK_PREVIEW = 5

const visibleChunks = computed(() => {
  const list = detailDoc.value.chunks || []
  return chunksExpanded.value ? list : list.slice(0, CHUNK_PREVIEW)
})

const connected = ref(true)
const modelInfo = ref({
  model: 'deepseek-v4.1-flash',
  embedding: 'text-embedding-3-small',
  embedding_dim: 1024,
  collection_count: 2,
})

async function checkBackend() {
  if (!USE_BACKEND) return
  try {
    const { data } = await getHealth()
    modelInfo.value = data
    connected.value = true
  } catch {
    connected.value = false
  }
}

let pollTimer = null

const topK = ref(4)
const threshold = ref(0.3)

const messages = ref([])
const inputText = ref('')
const sending = ref(false)
const chatListEl = ref(null)

const quickQuestions = [
  '介绍一下 RAG 检索增强生成的原理',
  '如何使用向量数据库做相似度检索？',
  '知识库的文档是如何切分和入库的？',
]

const typing = ref(false)

function triggerFilePick() {
  if (fileInputEl.value) fileInputEl.value.click()
}

function onFileChange(event) {
  const file = event.target.files && event.target.files[0]
  if (!file) return
  if (!file.name.toLowerCase().endsWith('.md')) {
    importNotice.value = '仅支持 .md 格式的 Markdown 文件'
    setTimeout(() => {
      importNotice.value = ''
    }, 3000)
    event.target.value = ''
    return
  }
  selectedFile.value = file
}

function clearFile() {
  selectedFile.value = null
  if (fileInputEl.value) fileInputEl.value.value = ''
}

function buildMockDetail(file) {
  const name = file ? file.name : 'manual.md'
  return {
    document_id: 'mock_doc_001',
    metadata: {
      source_name: name,
      filename: name,
      size: file ? file.size : 2048,
      chunk_count: 4,
      created_at: new Date().toISOString(),
    },
    chunks: [
      { index: 0, text: `【切片 0】这是从 ${name} 中切分出的第一段内容，用于向量化后入库。` },
      { index: 1, text: '【切片 1】这是第二段切片内容，通常按段落或固定长度切分。' },
      { index: 2, text: '【切片 2】这是第三段切片，包含知识库中的主体信息。' },
      { index: 3, text: '【切片 3】这是最后一段切片，用于补充说明与总结。' },
    ],
  }
}

function openDetail(doc) {
  detailDoc.value = doc
  metaDraft.value = { ...doc.metadata }
  customMeta.value = Object.entries(doc.metadata.extras || {}).map(([key, value]) => ({
    key,
    value,
  }))
  chunksExpanded.value = false
  showDetail.value = true
}

function closeDetail() {
  showDetail.value = false
}

function addCustomMeta() {
  customMeta.value.push({ key: '', value: '' })
}

function removeCustomMeta(index) {
  customMeta.value.splice(index, 1)
}

async function saveMetadata() {
  if (savingMeta.value) return
  const merged = { ...metaDraft.value }
  const extras = {}
  for (const item of customMeta.value) {
    if (item.key.trim()) extras[item.key.trim()] = item.value
  }
  if (Object.keys(extras).length) merged.extras = extras
  savingMeta.value = true
  try {
    if (USE_BACKEND && detailDoc.value.document_id) {
      await updateMetadata(detailDoc.value.document_id, merged)
    }
    detailDoc.value.metadata = merged
    metaDraft.value = { ...merged }
    importNotice.value = ''
    showDetail.value = false
  } catch {
    detailDoc.value.metadata = merged
    metaDraft.value = { ...merged }
    showDetail.value = false
  } finally {
    savingMeta.value = false
  }
}

async function importDoc() {
  if (!selectedFile.value || importing.value) return
  importing.value = true
  const file = selectedFile.value
  try {
    let doc
    if (USE_BACKEND) {
      const { data } = await uploadDocument(file)
      doc = data
      if (data.metadata && typeof data.metadata.collection_count === 'number') {
        modelInfo.value.collection_count = data.metadata.collection_count
      } else {
        modelInfo.value.collection_count += 1
      }
    } else {
      doc = buildMockDetail(file)
      modelInfo.value.collection_count += 1
    }
    clearFile()
    openDetail(doc)
    importNotice.value = '文档已成功导入知识库'
    clearTimeout(noticeTimer)
    noticeTimer = setTimeout(() => {
      importNotice.value = ''
    }, 3000)
  } catch {
    importNotice.value = '导入失败，请稍后重试'
    setTimeout(() => {
      importNotice.value = ''
    }, 3000)
  } finally {
    importing.value = false
  }
}

function useQuestion(q) {
  inputText.value = q
  document.getElementById('chat-input').focus()
}

function clearChat() {
  messages.value = []
}

const answered = computed(() =>
  messages.value.some((m) => m.role === 'assistant')
)

async function send() {
  const text = inputText.value.trim()
  if (!text || sending.value) return
  messages.value.push({ role: 'user', content: text })
  inputText.value = ''
  typing.value = true
  sending.value = true
  scrollBottom()
  if (USE_BACKEND) {
    if (!messages.value.some((m) => m.role === 'assistant')) {
      messages.value.push({ role: 'assistant', content: '' })
    }
    const last = () => messages.value[messages.value.length - 1]
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: text,
          top_k: topK.value,
          threshold: threshold.value,
        }),
      })
      if (!res.ok || !res.body) throw new Error('request failed')
      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let done = false
      while (!done) {
        const { value, done: d } = await reader.read()
        done = d
        buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
        let sep
        while ((sep = buffer.indexOf('\n\n')) !== -1) {
          const raw = buffer.slice(0, sep)
          buffer = buffer.slice(sep + 2)
          const payload = raw.replace(/^data:\s*/, '').trim()
          if (!payload || payload === '[DONE]') break
          try {
            const obj = JSON.parse(payload)
            if (obj.token !== undefined) last().content += obj.token
          } catch {}
          scrollBottom()
        }
      }
    } catch {
      last().content = '抱歉，后端暂时无法连接，请稍后重试。'
    } finally {
      typing.value = false
      sending.value = false
      scrollBottom()
    }
    return
  }
  const reply = buildReply(text)
  let i = 0
  function tick() {
    if (i >= reply.length) {
      typing.value = false
      sending.value = false
      return
    }
    const current = messages.value[messages.value.length - 1]
    if (!current || current.role !== 'assistant') {
      messages.value.push({ role: 'assistant', content: '' })
    }
    const last = messages.value[messages.value.length - 1]
    last.content = reply.slice(0, i + 1)
    i += 1
    scrollBottom()
    setTimeout(tick, 30)
  }
  setTimeout(tick, 400)
}

function buildReply(q) {
  const base = [
    '从知识库检索到的相关内容来看，',
    'RAG（检索增强生成）会把你的问题先做向量化，然后在 Milvus 中做相似度检索，',
    '再把命中的文档片段拼接到提示词里交给大模型生成回答。',
    '整个过程通常包含文档加载、文本切分、向量入库，以及检索、重排、生成这几个环节。',
  ]
  return `针对“${q}”，` + base.join('') + '\n\n你可以在左侧调整 TopK 和相似度阈值来控制召回的质量与数量。'
}

function onInput(event) {
  inputText.value = event.target.value
}

function onKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    send()
  }
}

function scrollBottom() {
  nextTick(() => {
    if (chatListEl.value) {
      chatListEl.value.scrollTop = chatListEl.value.scrollHeight
    }
  })
}

onMounted(() => {
  scrollBottom()
  checkBackend()
  if (USE_BACKEND) pollTimer = setInterval(checkBackend, POLL_INTERVAL)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  clearTimeout(noticeTimer)
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <div class="brand">
        <span class="brand-logo">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/></svg>
        </span>
        <span class="brand-name">RAG 知识库问答系统</span>
      </div>
      <div class="meta">
        <template v-if="connected">
          <span class="meta-item">
            <span class="meta-circle blue"></span>
            模型 {{ modelInfo.model }}
          </span>
          <span class="meta-item">
            <span class="meta-circle purple"></span>
            Embedding {{ modelInfo.embedding }} ({{ modelInfo.embedding_dim }}维)
          </span>
          <span class="meta-item">
            <span class="meta-circle green"></span>
            Milvus 已连接 · {{ modelInfo.collection_count }} 条
          </span>
        </template>
        <span v-else class="meta-item offline">
          <span class="meta-circle gray"></span>
          正在连接后端…
        </span>
      </div>
    </header>

    <main class="layout">
      <aside class="sidebar">
        <section class="card">
          <div class="card-title">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 3v12"/><path d="m7 8 5-5 5 5"/><path d="M5 21h14"/></svg>
            文档入库
          </div>
          <p class="card-desc">将知识文档加入向量库，供问答检索使用</p>
          <input
            ref="fileInputEl"
            type="file"
            accept=".md"
            class="file-hidden"
            @change="onFileChange"
          />
          <div class="file-drop" @click="triggerFilePick">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8Z"/><path d="M14 3v5h5"/><path d="M12 11v6M9.5 13.5 12 11l2.5 2.5"/></svg>
            <div class="file-drop-text">
              <strong v-if="selectedFile">{{ selectedFile.name }}</strong>
              <strong v-else>选择 Markdown 文件</strong>
              <span>{{ selectedFile ? selectedFile.size + ' 字节' : '仅支持 .md 格式，单文件上传' }}</span>
            </div>
          </div>
          <button
            v-if="selectedFile"
            class="file-clear"
            @click="clearFile"
          >
            移除文件
          </button>
          <button
            class="btn-primary"
            :disabled="importing || !selectedFile"
            @click="importDoc"
          >
            {{ importing ? '导入中…' : '导入知识库' }}
          </button>
          <p v-if="importNotice" class="import-notice">{{ importNotice }}</p>
        </section>

        <section class="card">
          <div class="card-title">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12h4l3-8 4 16 3-8h4"/></svg>
            检索参数
          </div>
          <div class="slider-field">
            <div class="slider-head">
              <label>TopK</label>
              <span class="slider-value">{{ topK }}</span>
            </div>
            <input type="range" v-model.number="topK" min="1" max="20" step="1" />
          </div>
          <div class="slider-field">
            <div class="slider-head">
              <label>相似度阈值</label>
              <span class="slider-value">{{ threshold.toFixed(2) }}</span>
            </div>
            <input type="range" v-model.number="threshold" min="0" max="1" step="0.01" />
          </div>
        </section>
      </aside>

      <section class="chat">
        <div class="chat-head">
          <div class="chat-head-left">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12 2a9 9 0 0 0-9 9c0 1.7.5 3.3 1.4 4.7L3 20l4.4-1.2A9 9 0 1 0 12 2Z"/><rect x="8" y="10" width="1.6" height="4" rx="0.8"/><rect x="11.2" y="10" width="1.6" height="4" rx="0.8"/><rect x="14.4" y="10" width="1.6" height="4" rx="0.8"/></svg>
            智能问答
          </div>
          <button class="btn-ghost" @click="clearChat">
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg>
            清空对话
          </button>
        </div>

        <div ref="chatListEl" class="chat-list">
          <div v-if="!answered" class="empty">
            <div class="empty-icon">
              <svg viewBox="0 0 24 24" width="40" height="40" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.5"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/></svg>
            </div>
            <h3>开始知识库问答</h3>
            <p class="empty-tips">输入问题，或从下方选择一个常见问题开始</p>
            <div class="quick">
              <button
                v-for="q in quickQuestions"
                :key="q"
                class="quick-item"
                @click="useQuestion(q)"
              >
                {{ q }}
              </button>
            </div>
          </div>

          <div
            v-for="(m, idx) in messages"
            :key="idx"
            class="msg-row"
            :class="m.role"
          >
            <div class="msg-bubble">{{ m.content }}</div>
            <div v-if="m.role === 'assistant' && typing && idx === messages.length - 1" class="cursor"></div>
          </div>
          <div v-if="sending" class="msg-row assistant">
            <div class="typing" v-show="typing && messages[messages.length - 1]?.role !== 'assistant'">
              <span></span><span></span><span></span>
            </div>
          </div>
        </div>

        <div class="input-area">
          <div class="input-box">
            <textarea
              id="chat-input"
              v-model="inputText"
              rows="1"
              placeholder="Enter 发送，Shift + Enter 换行"
              @input="onInput"
              @keydown="onKeydown"
            ></textarea>
            <button
              class="send-btn"
              :disabled="!inputText.trim() || sending"
              @click="send"
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>
            </button>
          </div>
        </div>
      </section>
    </main>

    <div v-if="showDetail" class="modal-mask" @click.self="closeDetail">
      <div class="modal">
        <div class="modal-head">
          <h3>导入结果</h3>
          <button class="modal-close" @click="closeDetail">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="modal-section">
            <div class="modal-section-head">
              <span>文档元数据</span>
              <span class="modal-doc-id">ID：{{ detailDoc.document_id }}</span>
            </div>
            <div class="meta-edit">
              <div
                v-for="(value, key) in metaDraft"
                :key="key"
                class="meta-row"
              >
                <span class="meta-key">{{ key }}</span>
                <input v-model="metaDraft[key]" class="meta-input" />
              </div>
              <div
                v-for="(item, idx) in customMeta"
                :key="'custom-' + idx"
                class="meta-row"
              >
                <input v-model="item.key" class="meta-input meta-key-input" placeholder="字段名" />
                <input v-model="item.value" class="meta-input" placeholder="值" />
                <button class="meta-remove" @click="removeCustomMeta(idx)">
                  <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
                </button>
              </div>
            </div>
            <button class="meta-add" @click="addCustomMeta">+ 添加自定义字段</button>
          </div>

          <div class="modal-section">
            <div class="modal-section-head">
              <span>切片内容</span>
              <span class="modal-doc-id">共 {{ detailDoc.chunks.length }} 个切片</span>
            </div>
            <div class="chunk-list" :class="{ expanded: chunksExpanded }">
              <div
                v-for="(chunk, idx) in visibleChunks"
                :key="idx"
                class="chunk-item"
              >
                <span class="chunk-index">#{{ chunk.index !== undefined ? chunk.index : idx }}</span>
                <p class="chunk-text">{{ chunk.text }}</p>
              </div>
              <p v-if="!detailDoc.chunks.length" class="chunk-empty">暂无切片数据</p>
            </div>
            <button
              v-if="detailDoc.chunks.length > CHUNK_PREVIEW"
              class="chunk-toggle"
              @click="chunksExpanded = !chunksExpanded"
            >
              {{ chunksExpanded ? '收起切片' : `展开全部（共 ${detailDoc.chunks.length} 个切片）` }}
            </button>
          </div>
        </div>
        <div class="modal-foot">
          <button class="btn-ghost" @click="closeDetail">取消</button>
          <button class="btn-primary modal-save" :disabled="savingMeta" @click="saveMetadata">
            {{ savingMeta ? '保存中…' : '保存元数据' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>