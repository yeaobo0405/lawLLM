<template>
  <div class="file-list">
    <div class="list-header">
      <h3>文件列表</h3>
      <span class="file-count">共 {{ files.length }} 个文件</span>
    </div>
    
    <div class="list-container" v-if="!loading">
      <div v-if="files.length === 0" class="empty-list">
        <p>暂无文件</p>
      </div>
      
      <div 
        v-for="(file, index) in files" 
        :key="index"
        class="file-item"
        @click="$emit('preview', file.file_path)"
      >
        <div class="file-icon">
          {{ getFileIcon(file.doc_type) }}
        </div>
        <div class="file-info">
          <div class="file-name">{{ file.file_name }}</div>
          <div class="file-meta">
            <span v-if="file.law_name" class="meta-item">
              {{ file.law_name }}
            </span>
            <span v-if="file.case_type" class="meta-item">
              {{ file.case_type }}
            </span>
            <span v-if="file.article_number" class="meta-item">
              第{{ file.article_number }}条
            </span>
          </div>
        </div>
        <div class="file-action">
          <span class="action-text">查看</span>
        </div>
      </div>
    </div>
    
    <div v-else class="loading-state">
      <div class="loading-spinner"></div>
      <p>加载中...</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'FileList',
  props: {
    files: {
      type: Array,
      default: () => []
    },
    loading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['preview'],
  setup() {
    const getFileIcon = (docType) => {
      if (docType === 'law') {
        return '📜'
      } else if (docType === 'case') {
        return '📋'
      }
      return '📄'
    }

    return {
      getFileIcon
    }
  }
}
</script>

<style scoped>
.file-list {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 300px;
  overflow: hidden;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.list-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
}

.file-count {
  font-size: 12px;
  color: #a0aec0;
}

.list-container {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.empty-list {
  text-align: center;
  padding: 40px 20px;
  color: #a0aec0;
}

.file-item {
  display: flex;
  align-items: center;
  padding: 12px 15px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  gap: 12px;
}

.file-item:hover {
  background-color: #f7fafc;
}

.file-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.file-info {
  flex: 1;
  min-width: 0;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: #2d3748;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.meta-item {
  font-size: 12px;
  color: #718096;
  background-color: #edf2f7;
  padding: 2px 8px;
  border-radius: 3px;
}

.file-action {
  flex-shrink: 0;
}

.action-text {
  font-size: 12px;
  color: #3182ce;
  font-weight: 500;
}

.file-item:hover .action-text {
  text-decoration: underline;
}

.loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #a0aec0;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #e2e8f0;
  border-top-color: #3182ce;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
