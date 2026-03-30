<template>
  <div class="app-container">
    <LoginView 
      v-if="!isLoggedIn" 
      @login-success="handleLoginSuccess"
    />
    
    <template v-else>
      <header class="app-header">
        <h1>法律智能问答系统</h1>
        <p class="subtitle">基于RAG的法律知识检索与问答</p>
        <div class="user-info">
          <span>欢迎，{{ currentUser }}</span>
          <button class="logout-btn" @click="handleLogout">退出</button>
        </div>
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
        <div v-if="activeTab === 'assistant'" class="assistant-layout">
          <!-- 左侧历史会话侧边栏 -->
          <div class="sessions-sidebar">
            <div class="sidebar-header">
              <h3>历史会话</h3>
              <button class="new-chat-btn" @click="startNewSession" title="新建会话">
                <span>+</span>
              </button>
            </div>
            <div class="sidebar-sessions" v-if="sessions.length > 0">
              <div 
                v-for="session in sessions" 
                :key="session.session_id"
                class="sidebar-session-item"
                :class="{ active: sessionId === session.session_id }"
                @click="loadSession(session.session_id)"
                :title="formatSessionName(session.last_updated)"
              >
                <div class="session-content">
                  <div class="session-name">{{ formatSessionName(session.last_updated) }}</div>
                  <div class="session-meta">{{ session.message_count }} 条消息</div>
                </div>
                <button 
                  class="delete-session-btn" 
                  @click.stop="deleteSession(session.session_id)"
                  title="删除会话"
                >
                  ×
                </button>
              </div>
            </div>
            <div v-else class="no-sessions-sidebar">
              暂无历史会话
            </div>
          </div>
          
          <!-- 右侧对话区域 -->
          <div class="assistant-panel">
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
    </template>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import QueryInput from './components/QueryInput.vue'
import AnswerDisplay from './components/AnswerDisplay.vue'
import FileFilter from './components/FileFilter.vue'
import FileList from './components/FileList.vue'
import LoginView from './components/LoginView.vue'

export default {
  name: 'App',
  components: {
    QueryInput,
    AnswerDisplay,
    FileFilter,
    FileList,
    LoginView
  },
  setup() {
    const isLoggedIn = ref(false)
    const token = ref('')
    const currentUser = ref('')
    const currentUserId = ref(0)
    
    const activeTab = ref('assistant')
    const messages = ref([])
    const queryLoading = ref(false)
    const files = ref([])
    const filteredFiles = ref([])
    const filesLoading = ref(false)
    const sessionId = ref('')
    const sessions = ref([])
    const showPreview = ref(false)
    const previewContent = ref('')
    const previewFileName = ref('')
    const previewFilePath = ref('')

    const generateSessionId = () => {
      return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
    }

    const authHeaders = () => ({
      'Authorization': `Bearer ${token.value}`
    })

    onMounted(() => {
      const savedToken = localStorage.getItem('token')
      const savedUser = localStorage.getItem('username')
      const savedUserId = localStorage.getItem('user_id')
      
      if (savedToken && savedUser) {
        token.value = savedToken
        currentUser.value = savedUser
        currentUserId.value = parseInt(savedUserId) || 0
        isLoggedIn.value = true
        sessionId.value = generateSessionId()
        loadFiles()
        loadUserSessions()
      }
    })

    const handleLoginSuccess = (data) => {
      token.value = data.token
      currentUser.value = data.username
      currentUserId.value = data.user_id
      isLoggedIn.value = true
      
      localStorage.setItem('token', data.token)
      localStorage.setItem('username', data.username)
      localStorage.setItem('user_id', data.user_id)
      
      sessionId.value = generateSessionId()
      loadFiles()
      loadUserSessions()
    }

    const handleLogout = async () => {
      try {
        await axios.post('/api/auth/logout', {}, {
          headers: authHeaders()
        })
      } catch (error) {
        console.error('登出失败:', error)
      }
      
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      localStorage.removeItem('user_id')
      
      isLoggedIn.value = false
      token.value = ''
      currentUser.value = ''
      currentUserId.value = 0
      messages.value = []
      sessions.value = []
    }

    const loadFiles = async () => {
      filesLoading.value = true
      try {
        const response = await axios.get('/api/file/list', {
          headers: authHeaders()
        })
        if (response.data.success) {
          files.value = response.data.files
          filteredFiles.value = response.data.files
        }
      } catch (error) {
        console.error('加载文件列表失败:', error)
        if (error.response?.status === 401) {
          handleLogout()
        }
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
      
      queryLoading.value = true
      
      try {
        const response = await fetch('/api/legal/query/stream', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...authHeaders()
          },
          body: JSON.stringify({
            query: query,
            session_id: sessionId.value
          })
        })
        
        if (response.status === 401) {
          handleLogout()
          return
        }
        
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        
        let assistantMessage = null
        
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
                  if (!assistantMessage) {
                    assistantMessage = {
                      role: 'assistant',
                      content: '',
                      searchResults: []
                    }
                    messages.value.push(assistantMessage)
                  }
                  assistantMessage.content += data.content
                } else if (data.type === 'replace') {
                  if (!assistantMessage) {
                    assistantMessage = {
                      role: 'assistant',
                      content: '',
                      searchResults: []
                    }
                    messages.value.push(assistantMessage)
                  }
                  assistantMessage.content = data.content
                } else if (data.type === 'results') {
                  if (assistantMessage) {
                    assistantMessage.searchResults = data.content
                  }
                } else if (data.type === 'disclaimer') {
                  if (assistantMessage) {
                    assistantMessage.disclaimer = data.content
                  }
                } else if (data.type === 'error') {
                  if (!assistantMessage) {
                    assistantMessage = {
                      role: 'assistant',
                      content: '',
                      searchResults: []
                    }
                    messages.value.push(assistantMessage)
                  }
                  assistantMessage.content = data.content
                  assistantMessage.isError = true
                }
              } catch (e) {
                console.error('解析数据失败:', e)
              }
            }
          }
        }
        
        // 对话完成后刷新会话列表
        await loadUserSessions()
        
      } catch (error) {
        console.error('查询失败:', error)
        messages.value.push({
          role: 'assistant',
          content: '网络错误，请检查您的网络连接后重试。',
          isError: true
        })
      } finally {
        queryLoading.value = false
      }
    }

    const handleFilter = async (filters) => {
      filesLoading.value = true
      try {
        const response = await axios.post('/api/file/filter', filters, {
          headers: authHeaders()
        })
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
          params: { file_path: filePath },
          headers: authHeaders()
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

    const loadUserSessions = async () => {
      try {
        const response = await axios.get('/api/conversation/sessions', {
          headers: authHeaders()
        })
        if (response.data.success) {
          sessions.value = response.data.sessions
        }
      } catch (error) {
        console.error('加载会话列表失败:', error)
      }
    }

    const loadSession = async (sid) => {
      sessionId.value = sid
      messages.value = []
      
      try {
        const response = await axios.get('/api/conversation/messages', {
          params: { session_id: sid },
          headers: authHeaders()
        })
        if (response.data.success) {
          messages.value = response.data.messages.map(msg => ({
            role: msg.role,
            content: msg.content
          }))
        }
      } catch (error) {
        console.error('加载会话消息失败:', error)
      }
    }

    const startNewSession = () => {
      sessionId.value = generateSessionId()
      messages.value = []
    }

    const deleteSession = async (sid) => {
      if (!confirm('确定要删除这个会话吗？删除后无法恢复。')) {
        return
      }
      
      try {
        const response = await axios.delete('/api/conversation/session', {
          params: { session_id: sid },
          headers: authHeaders()
        })
        
        if (response.data.success) {
          // 如果删除的是当前会话，清空消息
          if (sessionId.value === sid) {
            messages.value = []
            sessionId.value = generateSessionId()
          }
          // 刷新会话列表
          await loadUserSessions()
        } else {
          alert('删除失败：' + response.data.message)
        }
      } catch (error) {
        console.error('删除会话失败:', error)
        alert('删除失败，请稍后重试')
      }
    }

    const formatSessionName = (timeStr) => {
      if (!timeStr) return '新会话'
      const date = new Date(timeStr)
      const now = new Date()
      const isToday = date.toDateString() === now.toDateString()
      const isYesterday = new Date(now - 86400000).toDateString() === date.toDateString()
      
      const timePart = date.toLocaleString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit'
      })
      
      if (isToday) {
        return `今天 ${timePart}`
      } else if (isYesterday) {
        return `昨天 ${timePart}`
      } else {
        return date.toLocaleString('zh-CN', {
          month: '2-digit',
          day: '2-digit',
          hour: '2-digit',
          minute: '2-digit'
        })
      }
    }

    return {
      isLoggedIn,
      currentUser,
      activeTab,
      messages,
      queryLoading,
      filteredFiles,
      filesLoading,
      sessionId,
      sessions,
      showPreview,
      previewContent,
      previewFileName,
      handleLoginSuccess,
      handleLogout,
      handleQuery,
      handleFilter,
      handleFilePreview,
      closePreview,
      downloadFile,
      loadUserSessions,
      loadSession,
      startNewSession,
      deleteSession,
      formatSessionName
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
  position: relative;
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

.user-info {
  position: absolute;
  top: 15px;
  right: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  font-size: 14px;
}

.logout-btn {
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  border: 1px solid rgba(255, 255, 255, 0.3);
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.3s;
}

.logout-btn:hover {
  background: rgba(255, 255, 255, 0.3);
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
  max-width: 1400px;
  margin: 0 auto;
  width: 100%;
}

/* 智能助手布局 - 左右分栏 */
.assistant-layout {
  display: flex;
  gap: 20px;
  height: calc(100vh - 250px);
  min-height: 500px;
}

/* 左侧历史会话侧边栏 */
.sessions-sidebar {
  width: 260px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.sidebar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
}

.sidebar-header h3 {
  font-size: 16px;
  color: #2d3748;
  font-weight: 600;
}

.new-chat-btn {
  width: 32px;
  height: 32px;
  border: none;
  background: #2c5282;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  font-size: 20px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
}

.new-chat-btn:hover {
  background: #1a365d;
  transform: scale(1.05);
}

.sidebar-sessions {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.sidebar-session-item {
  padding: 12px 14px;
  margin-bottom: 6px;
  background: #f7fafc;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid transparent;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-session-item:hover {
  background: #edf2f7;
  border-color: #cbd5e0;
}

.sidebar-session-item.active {
  background: #e6f0ff;
  border-color: #2c5282;
}

.session-content {
  flex: 1;
  min-width: 0;
}

.session-name {
  font-size: 14px;
  color: #2d3748;
  font-weight: 500;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-meta {
  font-size: 12px;
  color: #718096;
}

.delete-session-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: #a0aec0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: all 0.2s;
  margin-left: 8px;
}

.sidebar-session-item:hover .delete-session-btn {
  opacity: 1;
}

.delete-session-btn:hover {
  background: #fed7d7;
  color: #e53e3e;
}

.no-sessions-sidebar {
  padding: 40px 20px;
  text-align: center;
  color: #a0aec0;
  font-size: 14px;
}

/* 右侧对话区域 */
.assistant-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 0;
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
