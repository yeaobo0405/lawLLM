<template>
  <div class="file-filter">
    <div class="filter-header">
      <h3>文件筛选</h3>
      <button class="reset-btn" @click="handleReset">重置</button>
    </div>
    
    <!-- 文档类型选择 -->
    <div class="doc-type-tabs">
      <button 
        :class="['tab-btn', { active: docType === 'law' }]"
        @click="docType = 'law'; handleFilter()"
      >
        📖 法律法规
      </button>
      <button 
        :class="['tab-btn', { active: docType === 'case' }]"
        @click="docType = 'case'; handleFilter()"
      >
        ⚖️ 案例文书
      </button>
    </div>
    
    <!-- 法律法规筛选 -->
    <div v-if="docType === 'law'" class="filter-form">
      <div class="filter-item">
        <label>法律名称</label>
        <input 
          type="text" 
          v-model="lawFilters.lawName"
          placeholder="请输入法律名称"
          @input="debounceFilter"
        />
      </div>
      
      <div class="filter-item">
        <label>法条编号</label>
        <input 
          type="text" 
          v-model="lawFilters.articleNumber"
          placeholder="请输入法条编号"
          @input="debounceFilter"
        />
      </div>
      
      <button class="filter-btn" @click="handleFilter">筛选</button>
    </div>
    
    <!-- 案例文书筛选 -->
    <div v-if="docType === 'case'" class="filter-form">
      <div class="filter-item">
        <label>案件类型</label>
        <select v-model="caseFilters.caseType" @change="handleFilter">
          <option value="">全部</option>
          <option value="民事">民事</option>
          <option value="刑事">刑事</option>
          <option value="行政">行政</option>
          <option value="知识产权">知识产权</option>
          <option value="劳动">劳动</option>
          <option value="公司">公司</option>
        </select>
      </div>
      
      <div class="filter-item">
        <label>案号</label>
        <input 
          type="text" 
          v-model="caseFilters.caseNumber"
          placeholder="请输入案号"
          @input="debounceFilter"
        />
      </div>
      
      <div class="filter-item">
        <label>涉及法律</label>
        <input 
          type="text" 
          v-model="caseFilters.relatedLaw"
          placeholder="请输入涉及的法律名称"
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
    // 文档类型：law-法律法规, case-案例文书
    const docType = ref('law')
    
    // 法律法规筛选条件
    const lawFilters = reactive({
      lawName: '',
      articleNumber: ''
    })
    
    // 案例文书筛选条件
    const caseFilters = reactive({
      caseType: '',
      caseNumber: '',
      relatedLaw: ''
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
      const filterParams = {
        doc_type: docType.value
      }
      
      if (docType.value === 'law') {
        // 法律法规筛选
        if (lawFilters.lawName.trim()) {
          filterParams.law_name = lawFilters.lawName.trim()
        }
        if (lawFilters.articleNumber.trim()) {
          filterParams.article_number = lawFilters.articleNumber.trim()
        }
      } else {
        // 案例文书筛选
        if (caseFilters.caseType) {
          filterParams.case_type = caseFilters.caseType
        }
        if (caseFilters.caseNumber.trim()) {
          filterParams.case_number = caseFilters.caseNumber.trim()
        }
        if (caseFilters.relatedLaw.trim()) {
          filterParams.law_name = caseFilters.relatedLaw.trim()
        }
      }
      
      emit('filter', filterParams)
    }

    const handleReset = () => {
      // 重置法律法规筛选
      lawFilters.lawName = ''
      lawFilters.articleNumber = ''
      
      // 重置案例文书筛选
      caseFilters.caseType = ''
      caseFilters.caseNumber = ''
      caseFilters.relatedLaw = ''
      
      emit('filter', { doc_type: docType.value })
    }

    return {
      docType,
      lawFilters,
      caseFilters,
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
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.filter-header h3 {
  font-size: 18px;
  color: #2d3748;
  margin: 0;
}

.reset-btn {
  padding: 6px 12px;
  background: #edf2f7;
  border: none;
  border-radius: 4px;
  color: #4a5568;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.3s;
}

.reset-btn:hover {
  background: #e2e8f0;
}

.doc-type-tabs {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.tab-btn {
  flex: 1;
  padding: 12px 20px;
  border: 2px solid #e2e8f0;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: #4a5568;
  transition: all 0.3s;
}

.tab-btn:hover {
  border-color: #cbd5e0;
  background: #f7fafc;
}

.tab-btn.active {
  border-color: #2c5282;
  background: #2c5282;
  color: white;
}

.filter-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  transition: all 0.3s;
}

.filter-item input:focus,
.filter-item select:focus {
  outline: none;
  border-color: #2c5282;
  box-shadow: 0 0 0 3px rgba(44, 82, 130, 0.1);
}

.filter-btn {
  padding: 12px 24px;
  background: #2c5282;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.3s;
  margin-top: 8px;
}

.filter-btn:hover {
  background: #1a365d;
}
</style>
