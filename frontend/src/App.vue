<template>
  <div class="app-container">
    <div v-if="!isAuthChecked" class="app-loading">
      <div class="loading-spinner"></div>
      <p>身份校验中...</p>
    </div>
    
    <LoginView 
      v-else-if="!isLoggedIn" 
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
          :class="['nav-btn', { active: activeTab === 'drafting' }]"
          @click="activeTab = 'drafting'"
        >
          文书生成
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
          
          <!-- 右侧对话与专家区域 -->
          <div class="assistant-panel">
            <AgentStatus :active="queryLoading" :agent="currentAgent" />
            <div class="assistant-body">
              <div class="chat-column">
                <AnswerDisplay 
                  :messages="messages"
                  :loading="queryLoading"
                  @jump="handleFilePreview"
                  @law-click="handleLawLinkClick"
                />
                <QueryInput 
                  :loading="queryLoading"
                  @submit="handleQuery"
                />
              </div>
              <div class="expert-column">
                <ExpertPanel 
                  ref="expertPanel"
                  :laws="retrievedLaws"
                  @preview="handleFilePreview"
                />
              </div>
            </div>
          </div>
        </div>
        
        <!-- 文书起草独立模块 -->
        <div v-else-if="activeTab === 'drafting'" class="assistant-layout drafting-layout-3col">
          <!-- 1. 历史文书侧边栏 -->
          <div class="sessions-sidebar drafts-sidebar">
            <div class="sidebar-header">
              <h3>我的文书</h3>
              <button class="new-chat-btn" @click="startNewDraft" title="新建文书">
                <span>+</span>
              </button>
            </div>
            <div class="sidebar-sessions" v-if="drafts.length > 0">
              <div 
                v-for="draft in drafts" 
                :key="draft.id"
                class="sidebar-session-item"
                :class="{ active: activeDraftId === draft.id }"
                @click="loadDraftDetail(draft.id)"
                :title="draft.doc_type"
              >
                <div class="session-content">
                  <div class="session-name">{{ draft.doc_type }}</div>
                  <div class="session-meta" style="font-size: 11px; margin-top:2px; color:#a0aec0;">
                    {{ formatSessionName(draft.updated_at) }}
                  </div>
                </div>
                <button 
                  class="delete-session-btn" 
                  @click.stop="deleteDraft(draft.id)"
                  title="删除记录"
                >
                  ×
                </button>
              </div>
            </div>
            <div v-else class="no-sessions-sidebar">
              暂无保存的文书
            </div>
          </div>

          <!-- 2. 表单区 -->
          <div class="drafting-form-container">
            <div class="drafting-form">
              <h3>文书生成参数</h3>
              
              <div class="form-group">
                <label>文书类型</label>
                <select v-model="draftForm.type" class="form-input">
                  <option value="民事起诉状">民事起诉状</option>
                  <option value="答辩状">答辩状</option>
                  <option value="上诉状">上诉状</option>
                  <option value="离婚协议书">离婚协议书</option>
                  <option value="劳动仲裁申请书">劳动仲裁申请书</option>
                  <option value="要求草拟其他涉法文件">其他自定义类型</option>
                </select>
              </div>
              
              <div class="form-group">
                <label>案情事实与诉求描述 <span class="required">*</span></label>
                <textarea 
                  v-model="draftForm.content" 
                  class="form-input"
                  placeholder="请您尽可能详细地描述案情事实和法律诉求，包括原告和被告的身份信息，事情发生的时间、地点、起因、经过和结果信息等。"
                  rows="12"
                ></textarea>
              </div>
              
              <button 
                class="generate-btn" 
                @click="generateDraft"
                :disabled="queryLoading || !draftForm.content.trim()"
              >
                {{ queryLoading ? '正在智能梳理并起草...' : '一键智能起草' }}
              </button>
            </div>
          </div>
          
          <div class="expert-column drafting-editor">
            <div v-if="currentDraft" class="draft-container">
              <div class="draft-toolbar">
                <span class="draft-title">起草的文书</span>
                <div class="draft-actions">
                  <button class="draft-btn save-btn" @click="saveDraft(false)">💾 保存</button>
                  <button class="draft-btn save-btn" @click="saveDraft(true)">📄 另存</button>
                  <button class="draft-btn copy-btn" @click="copyDraft">📋 复制</button>
                </div>
              </div>
              <div class="draft-preview markdown-body" v-html="renderedDraft"></div>
            </div>
            <div v-else class="empty-state">
              <div class="empty-icon">📝</div>
              <h3>文书智能生成中心</h3>
              <p>请在表单区选择文书类型并填写案情详后点击“一键智能起草”，<br>或者在左侧侧边栏中点击查看过往生成的历史记录。</p>
            </div>
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
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'
import { marked } from 'marked'
import QueryInput from './components/QueryInput.vue'
import AnswerDisplay from './components/AnswerDisplay.vue'
import FileFilter from './components/FileFilter.vue'
import FileList from './components/FileList.vue'
import LoginView from './components/LoginView.vue'
import AgentStatus from './components/AgentStatus.vue'
import ExpertPanel from './components/ExpertPanel.vue'

export default {
  name: 'App',
  components: {
    QueryInput,
    AnswerDisplay,
    FileFilter,
    FileList,
    LoginView,
    AgentStatus,
    ExpertPanel
  },
  setup() {
    const isLoggedIn = ref(false)
    const isAuthChecked = ref(false)
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

    // Multi-Agent State
    const currentAgent = ref('Supervisor')
    const retrievedLaws = ref([])
    const currentReasoning = ref(null)
    const currentDraft = ref('')
    
    const expertPanel = ref(null)
    const handleLawLinkClick = (articleNo) => {
      if (expertPanel.value) {
        expertPanel.value.scrollToLaw(articleNo)
      }
    }

    const draftForm = ref({
      type: '民事起诉状',
      content: ''
    })
    
    // Draft History State
    const drafts = ref([])
    const activeDraftId = ref('')

    // 辅助函数：合并并去重法条
    const mergeUniqueLaws = (newLaws, existingLaws) => {
      if (!newLaws) return existingLaws
      const existingKeys = new Set(existingLaws.map(l => `${l.law_name}-${l.article_number}`))
      const filtered = newLaws.filter(law => {
        const key = `${law.law_name}-${law.article_number}`
        if (!existingKeys.has(key)) {
          existingKeys.add(key)
          return true
        }
        return false
      })
      return [...existingLaws, ...filtered]
    }

    const loadDrafts = async () => {
      try {
        const response = await axios.get('/api/draft/list', { headers: authHeaders() })
        if (response.data.success) {
          drafts.value = response.data.drafts
        }
      } catch (e) {
        console.error('加载文书历史失败:', e)
      }
    }

    const loadDraftDetail = async (id) => {
      try {
        const response = await axios.get('/api/draft/detail', { 
          params: { draft_id: id },
          headers: authHeaders() 
        })
        if (response.data.success) {
          const draft = response.data.data
          activeDraftId.value = draft.id
          draftForm.value.type = draft.doc_type
          draftForm.value.content = draft.case_facts
          currentDraft.value = draft.content
        }
      } catch (e) {
        console.error('加载文书详情失败:', e)
      }
    }

    const startNewDraft = () => {
      activeDraftId.value = ''
      draftForm.value.type = '民事起诉状'
      draftForm.value.content = ''
      currentDraft.value = ''
    }

    const deleteDraft = async (id) => {
      if (!confirm('确定删除这份文书吗？')) return
      try {
        const response = await axios.delete('/api/draft/delete', {
          params: { draft_id: id },
          headers: authHeaders()
        })
        if (response.data.success) {
          await loadDrafts()
          if (activeDraftId.value === id) {
            startNewDraft()
          }
        }
      } catch (e) {
        console.error('删除文书失败:', e)
      }
    }

    const saveDraft = async (saveAsNew = false) => {
      if (!currentDraft.value) return
      try {
        const payload = {
          id: saveAsNew ? null : (activeDraftId.value || null),
          doc_type: draftForm.value.type,
          case_facts: draftForm.value.content,
          content: currentDraft.value
        }
        const response = await axios.post('/api/draft/save', payload, { headers: authHeaders() })
        if (response.data.success) {
          activeDraftId.value = response.data.draft_id
          await loadDrafts()
          alert('文书保存成功！')
        }
      } catch (e) {
        console.error('保存文书失败:', e)
        alert('保存文书失败')
      }
    }

    const generateDraft = () => {
      if (!draftForm.value.content.trim()) return
      const prompt = `我想写一份${draftForm.value.type}。以下是具体案情和诉求：\n${draftForm.value.content}`
      
      // 清空旧数据
      currentDraft.value = ''
      
      // 复用底层智能助理工作流，利用流式生成
      handleQuery(prompt)
    }

    const renderedDraft = computed(() => marked(currentDraft.value || ''))

    const copyDraft = () => {
      navigator.clipboard.writeText(currentDraft.value)
      alert('已复制到剪贴板')
    }

    const generateSessionId = () => {
      return 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9)
    }

    const authHeaders = () => ({
      'Authorization': `Bearer ${token.value}`
    })

    onMounted(async () => {
      const savedToken = localStorage.getItem('token')
      const savedUser = localStorage.getItem('username')
      const savedUserId = localStorage.getItem('user_id')
      
      if (savedToken && savedUser) {
        token.value = savedToken
        try {
          // 验证 Token 有效性
          const response = await axios.get('/api/auth/check', {
            headers: authHeaders()
          })
          
          if (response.data.success) {
            currentUser.value = savedUser
            currentUserId.value = parseInt(savedUserId) || 0
            isLoggedIn.value = true
            sessionId.value = generateSessionId()
            loadFiles()
            loadUserSessions()
            loadDrafts()
          } else {
            handleLogout()
          }
        } catch (error) {
          console.error('身份验证失败:', error)
          handleLogout()
        }
      }
      
      isAuthChecked.value = true
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
      loadDrafts()
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
          // 首次进入时默认展示法律法规
          filteredFiles.value = response.data.files.filter(f => f.doc_type === 'law')
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
      
      // 重置 Multi-Agent 状态
      queryLoading.value = true
      currentAgent.value = 'Supervisor'
      retrievedLaws.value = []
      currentReasoning.value = null
      currentDraft.value = ''
      
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
        let lineBuffer = ''
        let pendingResults = [] // 暂存检索结果，等到回答开始时显示
        
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          
          lineBuffer += decoder.decode(value, { stream: true })
          const lines = lineBuffer.split('\n')
          lineBuffer = lines.pop()
          
          for (const line of lines) {
            const trimmedLine = line.trim()
            if (!trimmedLine || !trimmedLine.startsWith('data: ')) continue
            
            try {
              const data = JSON.parse(trimmedLine.slice(6))
                
                if (data.type === 'answer') {
                  if (!assistantMessage) {
                    const newMsg = {
                      role: 'assistant',
                      content: '',
                      reasoning: '', // 确保有这个字段
                      searchResults: []
                    }
                    messages.value.push(newMsg)
                    assistantMessage = messages.value[messages.value.length - 1]
                    
                    // 回答开始，同步显示之前检索到的法条
                    if (pendingResults.length > 0) {
                      retrievedLaws.value = mergeUniqueLaws(pendingResults, retrievedLaws.value)
                      assistantMessage.searchResults = [...retrievedLaws.value]
                      pendingResults = []
                    }
                  }
                  assistantMessage.content += data.content
                } else if (data.type === 'agent_status') {
                  currentAgent.value = data.content
                } else if (data.type === 'results') {
                  const newLaws = data.content
                  if (data.overwrite) {
                    // 全量覆盖逻辑
                    retrievedLaws.value = newLaws
                    if (assistantMessage) {
                      assistantMessage.searchResults = [...newLaws]
                    }
                  } else {
                    // 如果回答还没开始，先暂存结果
                    if (!assistantMessage) {
                      pendingResults = newLaws
                    } else {
                      retrievedLaws.value = mergeUniqueLaws(newLaws, retrievedLaws.value)
                      assistantMessage.searchResults = [...retrievedLaws.value]
                    }
                  }
                } else if (data.type === 'reasoning') {
                  // 推理性回答的处理
                  if (!assistantMessage) {
                    const newMsg = {
                      role: 'assistant',
                      content: '',
                      reasoning: '',
                      searchResults: []
                    }
                    messages.value.push(newMsg)
                    assistantMessage = messages.value[messages.value.length - 1]
                    
                    // 当思考过程开始时，如果已经收到了检索结果，立即同步显示
                    if (pendingResults.length > 0) {
                      retrievedLaws.value = mergeUniqueLaws(pendingResults, retrievedLaws.value)
                      assistantMessage.searchResults = [...retrievedLaws.value]
                      pendingResults = []
                    }
                  }
                  assistantMessage.reasoning += data.content
                  currentReasoning.value = assistantMessage.reasoning
                } else if (data.type === 'draft') {
                  currentDraft.value += data.content
                  if (activeTab.value !== 'drafting') {
                    activeTab.value = 'drafting'
                  }
                } else if (data.type === 'replace') {
                  if (!assistantMessage) {
                    const newMsg = {
                      role: 'assistant',
                      content: '',
                      reasoning: '',
                      searchResults: []
                    }
                    messages.value.push(newMsg)
                    assistantMessage = messages.value[messages.value.length - 1]
                  }
                  assistantMessage.content = data.content
                } else if (data.type === 'disclaimer') {
                  if (assistantMessage) {
                    assistantMessage.disclaimer = data.content
                  }
                } else if (data.type === 'error') {
                  if (!assistantMessage) {
                    const newMsg = {
                      role: 'assistant',
                      content: '',
                      reasoning: '',
                      searchResults: []
                    }
                    messages.value.push(newMsg)
                    assistantMessage = messages.value[messages.value.length - 1]
                  }
                  assistantMessage.content = data.content
                  assistantMessage.isError = true
                }
              } catch (e) {
                console.error('解析数据失败:', e)
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
      retrievedLaws.value = [] // 切换会话时重置法条
      
      try {
        const response = await axios.get('/api/conversation/messages', {
          params: { session_id: sid },
          headers: authHeaders()
        })
        if (response.data.success) {
          messages.value = response.data.messages.map(msg => {
            const parsedMsg = {
              role: msg.role,
              content: msg.content,
              reasoning: msg.reasoning || '',
              searchResults: msg.search_results ? JSON.parse(msg.search_results) : []
            }
            
            // 从历史消息中恢复全局法条参考
            if (parsedMsg.searchResults && parsedMsg.searchResults.length > 0) {
              retrievedLaws.value = mergeUniqueLaws(parsedMsg.searchResults, retrievedLaws.value)
            }
            
            return parsedMsg
          })
        }
      } catch (error) {
        console.error('加载会话消息失败:', error)
      }
    }

    const startNewSession = () => {
      sessionId.value = generateSessionId()
      messages.value = []
      retrievedLaws.value = [] // 新会话法条为空
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
      isAuthChecked,
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
      currentAgent,
      retrievedLaws,
      currentReasoning,
      currentDraft,
      handleLoginSuccess,
      handleLogout,
      handleQuery,
      handleFilter,
      handleFilePreview,
      handleLawLinkClick,
      expertPanel,
      closePreview,
      downloadFile,
      loadUserSessions,
      loadSession,
      startNewSession,
      deleteSession,
      formatSessionName,
      renderedDraft,
      copyDraft,
      draftForm,
      generateDraft,
      drafts,
      activeDraftId,
      loadDraftDetail,
      startNewDraft,
      deleteDraft,
      saveDraft
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

.app-loading {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: #f7fafc;
}

.loading-spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #e2e8f0;
  border-top: 4px solid #2c5282;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
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

/* 右侧对话与专家区域 */
.assistant-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 15px;
  min-width: 0;
}

.assistant-body {
  display: flex;
  gap: 20px;
  flex: 1;
  min-height: 0;
}

.chat-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 20px;
  min-width: 400px;
}

.expert-column {
  width: 450px;
  min-width: 350px;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  max-height: 100%;
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

/* Markdown 样式记录 */
.markdown-body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 14px;
  line-height: 1.6;
  color: #24292e;
}

.markdown-body h1 { font-size: 1.5em; border-bottom: 1px solid #eaecef; padding-bottom: .3em; margin-top: 24px; margin-bottom: 16px; }
.markdown-body h2 { font-size: 1.25em; border-bottom: 1px solid #eaecef; padding-bottom: .3em; margin-top: 24px; margin-bottom: 16px; }
.markdown-body h3 { font-size: 1.1em; margin-top: 24px; margin-bottom: 16px; }
.markdown-body p { margin-top: 0; margin-bottom: 16px; }
.markdown-body b, .markdown-body strong { font-weight: 600; }
.markdown-body ul { padding-left: 2em; margin-bottom: 16px; }
.markdown-body li { margin-top: .25em; }

/* 文书起草独立布局相关样式 */
.drafting-form-container {
  flex: 0 0 35%;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.drafting-form {
  padding: 24px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.drafting-form h3 {
  font-size: 18px;
  color: #2d3748;
  margin-bottom: 24px;
  font-weight: 600;
  border-bottom: 2px solid #edf2f7;
  padding-bottom: 12px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group label {
  display: block;
  font-size: 14px;
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 8px;
}

.form-group .required {
  color: #e53e3e;
}

.form-input {
  width: 100%;
  padding: 12px;
  border: 1px solid #cbd5e0;
  border-radius: 6px;
  font-size: 14px;
  color: #2d3748;
  transition: all 0.2s;
  background: #f8fafc;
  resize: vertical;
}

.form-input:focus {
  outline: none;
  border-color: #2c5282;
  background: white;
  box-shadow: 0 0 0 3px rgba(44,82,130,0.1);
}

.form-input::placeholder {
  color: #cbd5e0;
  font-weight: 300; /* 变细一点，显得更轻 */
}

.generate-btn {
  margin-top: auto;
  width: 100%;
  padding: 14px;
  background: #2c5282;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 4px 6px rgba(44,82,130,0.2);
}

.generate-btn:hover:not(:disabled) {
  background: #1a365d;
  transform: translateY(-1px);
}

.generate-btn:disabled {
  background: #a0aec0;
  cursor: not-allowed;
  box-shadow: none;
}

.drafting-editor {
  flex: 1;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.draft-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.draft-toolbar {
  padding: 14px 20px;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
}

.draft-actions {
  display: flex;
  gap: 8px;
}

.draft-btn {
  padding: 6px 14px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.2s;
}

.save-btn {
  background: #edf2f7;
  color: #2d3748;
}

.save-btn:hover {
  background: #e2e8f0;
}

.copy-btn {
  background: #2c5282;
  color: white;
}

.copy-btn:hover {
  background: #1a365d;
}

.draft-preview {
  flex: 1;
  padding: 24px 30px;
  overflow-y: auto;
  font-size: 15px;
  line-height: 1.8;
}

.expert-column .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: #718096;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.empty-state h3 {
  color: #2d3748;
  margin-bottom: 12px;
}

.empty-state p {
  line-height: 1.6;
}
</style>
