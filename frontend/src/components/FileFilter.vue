<template>
  <div class="file-filter">
    <div class="filter-header">
      <h3>文件筛选</h3>
      <button class="reset-btn" @click="handleReset">重置</button>
    </div>
    
    <div class="filter-form">
      <div class="filter-item">
        <label>法律名称</label>
        <input 
          type="text" 
          v-model="filters.lawName"
          placeholder="请输入法律名称"
          @input="debounceFilter"
        />
      </div>
      
      <div class="filter-item">
        <label>案件类型</label>
        <select v-model="filters.caseType" @change="handleFilter">
          <option value="">全部</option>
          <option value="民事">民事</option>
          <option value="刑事">刑事</option>
          <option value="行政">行政</option>
          <option value="经济">经济</option>
          <option value="知识产权">知识产权</option>
          <option value="劳动争议">劳动争议</option>
        </select>
      </div>
      
      <div class="filter-item">
        <label>法条编号</label>
        <input 
          type="text" 
          v-model="filters.articleNumber"
          placeholder="请输入法条编号"
          @input="debounceFilter"
        />
      </div>
      
      <button class="filter-btn" @click="handleFilter">筛选</button>
    </div>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'

export default {
  name: 'FileFilter',
  emits: ['filter'],
  setup(props, { emit }) {
    const filters = reactive({
      lawName: '',
      caseType: '',
      articleNumber: ''
    })

    let debounceTimer = null

    const debounceFilter = () => {
      if (debounceTimer) {
        clearTimeout(debounceTimer)
      }
      debounceTimer = setTimeout(() => {
        handleFilter()
      }, 500)
    }

    const handleFilter = () => {
      const filterParams = {}
      
      if (filters.lawName.trim()) {
        filterParams.law_name = filters.lawName.trim()
      }
      if (filters.caseType) {
        filterParams.case_type = filters.caseType
      }
      if (filters.articleNumber.trim()) {
        filterParams.article_number = filters.articleNumber.trim()
      }
      
      emit('filter', filterParams)
    }

    const handleReset = () => {
      filters.lawName = ''
      filters.caseType = ''
      filters.articleNumber = ''
      emit('filter', {})
    }

    return {
      filters,
      debounceFilter,
      handleFilter,
      handleReset
    }
  }
}
</script>

<style scoped>
.file-filter {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid #e2e8f0;
}

.filter-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #2d3748;
}

.reset-btn {
  background: none;
  border: 1px solid #e2e8f0;
  color: #718096;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.reset-btn:hover {
  background-color: #f7fafc;
  border-color: #cbd5e0;
}

.filter-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.filter-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-item label {
  font-size: 13px;
  font-weight: 500;
  color: #4a5568;
}

.filter-item input,
.filter-item select {
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  transition: border-color 0.2s;
}

.filter-item input:focus,
.filter-item select:focus {
  outline: none;
  border-color: #3182ce;
}

.filter-item input::placeholder {
  color: #a0aec0;
}

.filter-btn {
  background: linear-gradient(135deg, #2c5282 0%, #1a365d 100%);
  color: white;
  border: none;
  padding: 12px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 5px;
}

.filter-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(44, 82, 130, 0.3);
}
</style>
