<template>
  <div class="expert-panel">
    <div class="panel-header">
      <div class="header-title">
        法条参考
        <span v-if="displayedLaws.length > 0" class="badge">{{ displayedLaws.length }}</span>
      </div>
    </div>
    
    <div class="panel-content" ref="scrollContainer">
      <!-- 法条参考 -->
      <div class="tab-pane">
        <div v-if="displayedLaws.length > 0" class="laws-list">
          <div 
            v-for="(law, index) in displayedLaws" 
            :key="index" 
            :ref="el => { if (el) lawRefs[law.article_number] = el }"
            :class="['law-item clickable', { 'highlighted': highlightedLaw === law.article_number }]"
            @click="handleLawClick(law)"
            :title="law.file_path ? '点击查看源文件' : ''"
          >
            <div class="law-title">《{{ law.law_name }}》 第 {{ law.article_number }} 条</div>
            <div class="law-text">{{ law.content }}</div>
          </div>
        </div>
        <div v-else class="empty-state">
          检索到的法条将在此显示
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUpdate, nextTick } from 'vue'

const emit = defineEmits(['preview'])

const props = defineProps({
  laws: {
    type: Array,
    default: () => []
  }
})

const displayedLaws = ref([])
const lawRefs = ref({})
const highlightedLaw = ref(null)
const scrollContainer = ref(null)

// 确保引用在更新前重置
onBeforeUpdate(() => {
  lawRefs.value = {}
})

// 转换中文字符为数字 (如: 十八 -> 18)
const chineseToNumber = (cn) => {
  const charMap = { '零': 0, '一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10 }
  if (!cn) return ''
  if (/^\d+$/.test(cn)) return cn
  
  if (cn.length === 1) return String(charMap[cn] || cn)
  if (cn.length === 2 && cn[0] === '十') return String(10 + charMap[cn[1]])
  if (cn.length === 2 && cn[1] === '十') return String(charMap[cn[0]] * 10)
  if (cn.length === 3 && cn[1] === '十') return String(charMap[cn[0]] * 10 + charMap[cn[2]])
  
  return cn
}

// 监听 laws 的变化，实现“一条一条弹出”的效果
watch(() => props.laws, async (newLaws) => {
  // 如果新法律列表比显示的少（说明切换了会话或清空了），则重置
  if (newLaws.length < displayedLaws.value.length) {
    displayedLaws.value = []
    return
  }

  // 找出还未显示的法律
  const currentLawIds = new Set(displayedLaws.value.map(l => `${l.law_name}-${l.article_number}`))
  const pendingLaws = newLaws.filter(l => !currentLawIds.has(`${l.law_name}-${l.article_number}`))

  if (pendingLaws.length > 0) {
    // 渐进式逐条添加
    for (const law of pendingLaws) {
      displayedLaws.value.push(law)
      // 稍微延迟一下，营造“一条条跳出”的感觉
      await new Promise(resolve => setTimeout(resolve, 300))
    }
  }
}, { deep: true, immediate: true })

const handleLawClick = (law) => {
  if (law.file_path) {
    emit('preview', law.file_path)
  }
}

// 暴露给父组件的方法：定位并高亮某条法条
const scrollToLaw = (articleNumber) => {
  // 统一转为数字字符串进行匹配
  const normalizedKey = chineseToNumber(String(articleNumber).replace(/第|条/g, ''))
  
  // 在已显示的法律中寻找匹配项
  let matchedKey = null
  for (const key in lawRefs.value) {
    if (chineseToNumber(key) === normalizedKey) {
      matchedKey = key
      break
    }
  }

  const target = matchedKey ? lawRefs.value[matchedKey] : null

  if (target) {
    highlightedLaw.value = matchedKey
    target.scrollIntoView({ behavior: 'smooth', block: 'center' })
    
    // 3秒后取消高亮
    setTimeout(() => {
      if (highlightedLaw.value === matchedKey) {
        highlightedLaw.value = null
      }
    }, 3000)
  }
}

// 定义暴露给外部的 API
defineExpose({
  scrollToLaw
})
</script>

<style scoped>
.expert-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  overflow: hidden;
}

.panel-header {
  padding: 12px 16px;
  background: #f7fafc;
  border-bottom: 1px solid #e2e8f0;
}

.header-title {
  font-size: 15px;
  font-weight: 600;
  color: #2d3748;
  display: flex;
  align-items: center;
}

.badge {
  background: #2c5282;
  color: white;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 10px;
  margin-left: 4px;
}

.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  scroll-behavior: smooth;
}

.tab-pane {
  height: 100%;
}

.law-item {
  margin-bottom: 16px;
  padding: 12px;
  background: #f8fafc;
  border-left: 3px solid #2c5282;
  border-radius: 4px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: fadeInRight 0.5s ease-out;
}

@keyframes fadeInRight {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.law-item.clickable {
  cursor: pointer;
}

.law-item.clickable:hover {
  background: #edf2f7;
  transform: translateX(2px);
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.law-item.highlighted {
  background: #fffaf0;
  border-left-color: #ed8936;
  border-left-width: 5px;
  transform: scale(1.02);
  box-shadow: 0 0 10px rgba(237, 137, 54, 0.2);
}

.law-title {
  font-weight: 600;
  font-size: 14px;
  margin-bottom: 6px;
}

.law-text {
  font-size: 13px;
  color: #4a5568;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
  color: #a0aec0;
  font-size: 14px;
}
</style>
