<template>
  <div class="query-input">
    <div class="input-wrapper">
      <textarea
        v-model="inputText"
        placeholder="请输入您的法律问题..."
        :disabled="loading"
        @keydown.enter.exact.prevent="handleSubmit"
        rows="3"
      ></textarea>
      <button 
        class="submit-btn" 
        @click="handleSubmit"
        :disabled="loading || !inputText.trim()"
      >
        <span v-if="!loading">提交问题</span>
        <span v-else>处理中...</span>
      </button>
    </div>
    <div class="input-hint">
      <span>按 Enter 键快速提交</span>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'

export default {
  name: 'QueryInput',
  props: {
    loading: {
      type: Boolean,
      default: false
    }
  },
  emits: ['submit'],
  setup(props, { emit }) {
    const inputText = ref('')

    const handleSubmit = () => {
      if (inputText.value.trim() && !props.loading) {
        emit('submit', inputText.value)
        inputText.value = ''
      }
    }

    return {
      inputText,
      handleSubmit
    }
  }
}
</script>

<style scoped>
.query-input {
  background: white;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.input-wrapper {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

textarea {
  width: 100%;
  padding: 15px;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 14px;
  resize: vertical;
  min-height: 80px;
  font-family: inherit;
  transition: border-color 0.2s;
}

textarea:focus {
  outline: none;
  border-color: #3182ce;
}

textarea:disabled {
  background-color: #f7fafc;
  cursor: not-allowed;
}

.submit-btn {
  background: linear-gradient(135deg, #2c5282 0%, #1a365d 100%);
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  align-self: flex-end;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(44, 82, 130, 0.3);
}

.submit-btn:disabled {
  background: #a0aec0;
  cursor: not-allowed;
  transform: none;
}

.input-hint {
  text-align: right;
  color: #a0aec0;
  font-size: 12px;
  margin-top: 5px;
}
</style>
