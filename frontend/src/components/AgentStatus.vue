<template>
  <div v-if="active" class="agent-status-bar">
    <div class="status-icon">
      <div class="pulse"></div>
    </div>
    <div class="status-content">
      <span class="agent-name">{{ currentAgentName }}</span>
      <span class="status-desc">{{ statusText }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  active: Boolean,
  agent: {
    type: String,
    default: 'Supervisor'
  }
})

const agents = {
  'Supervisor': { name: '主控协调员', desc: '正在规划任务路径...' },
  'Researcher': { name: '法规研究员', desc: '正在检索相关法律法规...' },
  'Analyst': { name: '案情分析师', desc: '正在进行法律逻辑推演...' },
  'Drafter': { name: '文书代书员', desc: '正在为您起草法律文书...' },
  'Auditor': { name: '合规审计员', desc: '正在进行终审与风险检查...' }
}

const currentAgentName = computed(() => agents[props.agent]?.name || '法律助手')
const statusText = computed(() => agents[props.agent]?.desc || '正在处理中...')
</script>

<style scoped>
.agent-status-bar {
  display: flex;
  align-items: center;
  background: #ebf8ff;
  border: 1px solid #bee3f8;
  padding: 8px 16px;
  border-radius: 8px;
  margin-bottom: 12px;
  animation: fadeIn 0.3s ease-out;
}

.status-icon {
  margin-right: 12px;
}

.pulse {
  width: 10px;
  height: 10px;
  background: #3182ce;
  border-radius: 50%;
  box-shadow: 0 0 0 rgba(49, 130, 206, 0.4);
  animation: pulse 1.5s infinite;
}

.agent-name {
  font-weight: 600;
  color: #2c5282;
  font-size: 14px;
  margin-right: 8px;
}

.status-desc {
  color: #4a5568;
  font-size: 13px;
}

@keyframes pulse {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(49, 130, 206, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(49, 130, 206, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(49, 130, 206, 0); }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
