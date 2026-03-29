<template>
  <div class="answer-display">
    <div class="messages-container" ref="messagesContainer">
      <div v-if="messages.length === 0" class="empty-state">
        <div class="empty-icon">⚖️</div>
        <h3>欢迎使用法律智能问答系统</h3>
        <p>请在下方输入您的法律问题，系统将为您提供专业的法律咨询服务</p>
      </div>
      
      <div 
        v-for="(message, index) in messages" 
        :key="index"
        :class="['message', message.role]"
      >
        <div class="message-header">
          <span class="role-label">{{ message.role === 'user' ? '用户' : '法律助手' }}</span>
        </div>
        <div class="message-content" v-html="formatContent(message.content)" @click="handleContentClick"></div>
        
        <div v-if="message.disclaimer" class="disclaimer">
          {{ message.disclaimer }}
        </div>
      </div>
      
      <div v-if="loading" class="message assistant loading">
        <div class="message-header">
          <span class="role-label">法律助手</span>
        </div>
        <div class="message-content">
          <div class="typing-indicator">
            <span></span>
            <span></span>
            <span></span>
          </div>
          正在思考中...
        </div>
      </div>
    </div>
    
    <div v-if="showSourceModal" class="source-modal-overlay" @click="closeSourceModal">
      <div class="source-modal" @click.stop>
        <div class="modal-header">
          <h3>{{ sourceData.law_name }}</h3>
          <button class="close-btn" @click="closeSourceModal">&times;</button>
        </div>
        <div class="modal-body">
          <div class="source-meta">
            <span v-if="sourceData.chapter" class="meta-item">章节：{{ sourceData.chapter }}</span>
            <span v-if="sourceData.article_number" class="meta-item">法条：第{{ sourceData.article_number }}条</span>
          </div>
          <div class="source-content">
            <h4>法条原文：</h4>
            <div class="content-text">{{ sourceData.content }}</div>
          </div>
          <div class="source-actions">
            <button class="action-btn download-btn" @click="downloadFile">
              📥 下载原文件
            </button>
            <button class="action-btn open-btn" @click="openFile">
              📂 打开原文件
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, watch, nextTick } from 'vue'
import { marked } from 'marked'

export default {
  name: 'AnswerDisplay',
  props: {
    messages: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['jump'],
  setup(props, { emit }) {
    const messagesContainer = ref(null)
    const showSourceModal = ref(false)
    const sourceData = ref({
      type: '',
      law_name: '',
      article_number: '',
      content: '',
      file_path: '',
      chapter: ''
    })

    watch(() => props.messages.length, () => {
      nextTick(() => {
        if (messagesContainer.value) {
          messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
        }
      })
    })

    const formatContent = (content) => {
      if (!content) return ''
      const placeholders = []
      const placeholderPrefix = 'SOURCE_BTN_PH_'
      let index = 0
      let processedContent = content.replace(/<span class="source-btn"[^>]*>[\s\S]*?<\/span>/g, (match) => {
        const placeholder = `${placeholderPrefix}${index}`
        placeholders.push({ placeholder, match })
        index++
        return placeholder
      })
      let html = marked.parse(processedContent, { gfm: true, breaks: true })
      placeholders.forEach(({ placeholder, match }) => {
        html = html.replace(placeholder, match)
      })
      return html
    }

    const handleContentClick = (event) => {
      const target = event.target
      if (target.classList.contains('source-btn')) {
        const sourceJson = target.getAttribute('data-source')
        if (sourceJson) {
          try {
            sourceData.value = JSON.parse(sourceJson)
            showSourceModal.value = true
          } catch (e) {
            console.error('解析来源数据失败:', e)
          }
        }
      }
    }

    const closeSourceModal = () => {
      showSourceModal.value = false
    }

    const downloadFile = () => {
      if (sourceData.value.file_path) {
        emit('jump', sourceData.value.file_path)
      }
    }

    const openFile = () => {
      if (sourceData.value.file_path) {
        emit('jump', sourceData.value.file_path)
      }
    }

    return {
      messagesContainer,
      showSourceModal,
      sourceData,
      formatContent,
      handleContentClick,
      closeSourceModal,
      downloadFile,
      openFile
    }
  }
}
</script>

<style scoped>
.answer-display {
  flex: 1;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  min-height: 400px;
  overflow: hidden;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #a0aec0;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 20px;
}

.empty-state h3 {
  font-size: 20px;
  color: #4a5568;
  margin-bottom: 10px;
}

.empty-state p {
  font-size: 14px;
}

.message {
  margin-bottom: 20px;
  padding: 15px;
  border-radius: 8px;
  max-width: 90%;
}

.message.user {
  background-color: #ebf8ff;
  margin-left: auto;
  border: 1px solid #bee3f8;
}

.message.assistant {
  background-color: #f7fafc;
  border: 1px solid #e2e8f0;
}

.message.loading {
  opacity: 0.8;
}

.message-header {
  margin-bottom: 10px;
}

.role-label {
  font-size: 12px;
  font-weight: 600;
  color: #718096;
  text-transform: uppercase;
}

.message-content {
  font-size: 14px;
  line-height: 1.8;
  color: #2d3748;
}

.message-content :deep(p) {
  margin-bottom: 10px;
}

.message-content :deep(ul), .message-content :deep(ol) {
  margin-left: 20px;
  margin-bottom: 10px;
}

.message-content :deep(.source-btn) {
  display: inline-block;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  margin-left: 4px;
  transition: all 0.2s;
  border: none;
  vertical-align: middle;
}

.message-content :deep(.source-btn:hover) {
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.4);
}

.typing-indicator {
  display: inline-flex;
  gap: 4px;
  margin-right: 10px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background-color: #a0aec0;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) { animation-delay: 0s; }
.typing-indicator span:nth-child(2) { animation-delay: 0.2s; }
.typing-indicator span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
  0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

.disclaimer {
  margin-top: 15px;
  padding: 12px;
  background-color: #fffaf0;
  border-left: 3px solid #ed8936;
  font-size: 12px;
  color: #744210;
  white-space: pre-line;
}

.source-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.source-modal {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
  opacity: 0.8;
  transition: opacity 0.2s;
}

.close-btn:hover {
  opacity: 1;
}

.modal-body {
  padding: 20px;
  overflow-y: auto;
  max-height: calc(80vh - 60px);
}

.source-meta {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e2e8f0;
}

.meta-item {
  font-size: 13px;
  color: #718096;
  background: #f7fafc;
  padding: 4px 10px;
  border-radius: 4px;
}

.source-content {
  margin-bottom: 20px;
}

.source-content h4 {
  font-size: 14px;
  color: #4a5568;
  margin-bottom: 10px;
}

.content-text {
  background: #f7fafc;
  padding: 16px;
  border-radius: 8px;
  font-size: 14px;
  line-height: 1.8;
  color: #2d3748;
  border-left: 3px solid #667eea;
}

.source-actions {
  display: flex;
  gap: 12px;
  padding-top: 16px;
  border-top: 1px solid #e2e8f0;
}

.action-btn {
  flex: 1;
  padding: 10px 16px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.download-btn {
  background: #48bb78;
  color: white;
}

.download-btn:hover {
  background: #38a169;
}

.open-btn {
  background: #4299e1;
  color: white;
}

.open-btn:hover {
  background: #3182ce;
}
</style>
