<template>
  <div class="app-container">
    <header class="app-header">
      <h1>法律智能问答系统</h1>
      <p class="subtitle">基于RAG的法律知识检索与问答</p>
    </header>
    
    <nav class="app-nav">
      <button 
        :class="['nav-btn', { active: activeTab === 'assistant' }]"
        @click="activeTab = 'assistant'"
      >
        智能助手
      </button>
      <button 
        :class="['nav-btn', { active: activeTab === 'files' }]"
        @click="activeTab = 'files'"
      >
        文件检索
      </button>
    </nav>
    
    <main class="app-main">
      <div v-if="activeTab === 'assistant'" class="assistant-panel">
        <AnswerDisplay 
          :messages="messages"
          :loading="queryLoading"
          @jump="handleFilePreview"
        />
        <QueryInput 
          :loading="queryLoading"
          @submit="handleQuery"
        />
      </div>
      
      <div v-else class="files-panel">
        <FileFilter @filter="handleFilter" />
        <FileList 
          :files="filteredFiles" 
          :loading="filesLoading"
          @preview="handleFilePreview"
        />
      </div>
    </main>
    
    <footer class="app-footer">
      <p>本系统提供的法律信息仅供参考，不构成法律意见或建议</p>
    </footer>
    
    <div v-if="showPreview" class="preview-modal" @click.self="closePreview">
      <div class="preview-content">
        <div class="preview-header">
          <h3>{{ previewFileName }}</h3>
          <div class="preview-actions">
            <button class="download-btn" @click="downloadFile">
              下载文件
            </button>
            <button class="close-btn" @click="closePreview">×</button>
          </div>
        </div>
        <div class="preview-body">
          <pre v-if="previewContent">{{ previewContent }}</pre>
          <p v-else class="loading-text">加载中...</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import QueryInput from './components/QueryInput.vue'
import AnswerDisplay from './components/AnswerDisplay.vue'
import FileFilter from './components/FileFilter.vue'
import FileList from './components/FileList.vue'

export default {
  name: 'App',
  components: {
    QueryInput,
    AnswerDisplay,
    FileFilter,
    FileList
  },
  setup() {
    const activeTab = ref('assistant')
    const messages = ref([])
    const queryLoading = ref(false)
    const files = ref([])
    const filteredFiles = ref([])
    const filesLoading = ref(false)
    const sessionId = ref('')
    const showPreview = ref(false)
    const previewContent = ref('')
    const previewFileName = ref('')
    const previewFilePath = ref('')

    const generateSessionId = () => {
      return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
    }

    onMounted(() => {
      sessionId.value = generateSessionId()
      loadFiles()
    })

    const loadFiles = async () => {
      filesLoading.value = true
      try {
        const response = await axios.get('/api/file/list')
        if (response.data.success) {
          files.value = response.data.files
          filteredFiles.value = response.data.files
        }
      } catch (error) {
        console.error('加载文件列表失败:', error)
      } finally {
        filesLoading.value = false
      }
    }

    const handleQuery = async (query) => {
      if (!query.trim()) return
      
      messages.value.push({
        role: 'user',
        content: query
      })
      
      const assistantMessage = {
        role: 'assistant',
        content: '',
        searchResults: []
      }
      messages.value.push(assistantMessage)
      
      queryLoading.value = true
      
      try {
        const response = await fetch('/api/legal/query/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            query: query,
            session_id: sessionId.value
          })
        })
        
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          
          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                
                if (data.type === 'answer') {
                  assistantMessage.content += data.content
                } else if (data.type === 'replace') {
                  assistantMessage.content = data.content
                } else if (data.type === 'results') {
                  assistantMessage.searchResults = data.content
                } else if (data.type === 'disclaimer') {
                  assistantMessage.disclaimer = data.content
                } else if (data.type === 'error') {
                  assistantMessage.content = data.content
                  assistantMessage.isError = true
                }
              } catch (e) {
                console.error('解析数据失败:', e)
              }
            }
          }
        }
        
      } catch (error) {
        console.error('查询失败:', error)
        assistantMessage.content = '网络错误，请检查您的网络连接后重试。'
        assistantMessage.isError = true
      } finally {
        queryLoading.value = false
      }
    }

    const handleFilter = async (filters) => {
      filesLoading.value = true
      try {
        const response = await axios.post('/api/file/filter', filters)
        if (response.data.success) {
          filteredFiles.value = response.data.files
        }
      } catch (error) {
        console.error('筛选失败:', error)
        filteredFiles.value = []
      } finally {
        filesLoading.value = false
      }
    }

    const handleFilePreview = async (filePath) => {
      previewFilePath.value = filePath
      previewFileName.value = filePath.split(/[/\\]/).pop()
      showPreview.value = true
      previewContent.value = ''
      
      try {
        const response = await axios.get('/api/file/content', {
          params: { file_path: filePath }
        })
        
        if (response.data.success) {
          previewContent.value = response.data.content
        } else {
          previewContent.value = '无法加载文件内容: ' + (response.data.message || '未知错误')
        }
      } catch (error) {
        console.error('加载文件内容失败:', error)
        previewContent.value = '加载失败，请稍后重试'
      }
    }

    const closePreview = () => {
      showPreview.value = false
      previewContent.value = ''
      previewFilePath.value = ''
    }

    const downloadFile = () => {
      if (previewFilePath.value) {
        window.open(`/api/file/download?file_path=${encodeURIComponent(previewFilePath.value)}`, '_blank')
      }
    }

    return {
      activeTab,
      messages,
      queryLoading,
      filteredFiles,
      filesLoading,
      showPreview,
      previewContent,
      previewFileName,
      handleQuery,
      handleFilter,
      handleFilePreview,
      closePreview,
      downloadFile
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  background-color: #f5f5f5;
  color: #333;
  line-height: 1.6;
}

.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: linear-gradient(135deg, #1a365d 0%, #2c5282 100%);
  color: white;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.app-header h1 {
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 5px;
}

.app-header .subtitle {
  font-size: 14px;
  opacity: 0.9;
}

.app-nav {
  display: flex;
  justify-content: center;
  gap: 10px;
  padding: 15px;
  background-color: white;
  border-bottom: 1px solid #e2e8f0;
}

.nav-btn {
  padding: 10px 30px;
  border: none;
  background-color: #edf2f7;
  color: #4a5568;
  border-radius: 8px;
  cursor: pointer;
  font-size: 15px;
  font-weight: 500;
  transition: all 0.3s ease;
}

.nav-btn:hover {
  background-color: #e2e8f0;
}

.nav-btn.active {
  background-color: #2c5282;
  color: white;
}

.app-main {
  flex: 1;
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

.assistant-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
  height: calc(100vh - 250px);
  min-height: 500px;
}

.files-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.app-footer {
  background-color: #2d3748;
  color: #a0aec0;
  text-align: center;
  padding: 15px;
  font-size: 12px;
}

.preview-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.preview-content {
  background: white;
  border-radius: 12px;
  width: 90%;
  max-width: 900px;
  max-height: 80vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #e2e8f0;
  background-color: #f7fafc;
  border-radius: 12px 12px 0 0;
}

.preview-header h3 {
  font-size: 16px;
  color: #2d3748;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  margin-right: 15px;
}

.preview-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

.download-btn {
  padding: 8px 16px;
  background-color: #2c5282;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

.download-btn:hover {
  background-color: #1a365d;
}

.close-btn {
  width: 32px;
  height: 32px;
  border: none;
  background-color: #e2e8f0;
  color: #4a5568;
  border-radius: 50%;
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
  transition: all 0.3s;
}

.close-btn:hover {
  background-color: #cbd5e0;
  color: #2d3748;
}

.preview-body {
  flex: 1;
  overflow: auto;
  padding: 20px;
}

.preview-body pre {
  white-space: pre-wrap;
  word-wrap: break-word;
  font-family: 'Microsoft YaHei', sans-serif;
  font-size: 14px;
  line-height: 1.8;
  color: #2d3748;
  margin: 0;
}

.loading-text {
  text-align: center;
  color: #a0aec0;
  padding: 40px;
}
</style>
