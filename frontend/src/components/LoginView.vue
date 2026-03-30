<template>
  <div class="login-overlay">
    <div class="login-card">
      <h2 class="login-title">法律智能问答系统</h2>
      
      <form @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label>用户名</label>
          <input 
            type="text" 
            v-model="username" 
            placeholder="请输入用户名"
            :disabled="loading"
          />
        </div>
        
        <div class="form-group">
          <label>密码</label>
          <input 
            type="password" 
            v-model="password" 
            placeholder="请输入密码"
            :disabled="loading"
          />
        </div>
        
        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
        
        <button type="submit" class="login-btn" :disabled="loading">
          {{ loading ? '登录中...' : '登录' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import axios from 'axios'

export default {
  name: 'LoginView',
  emits: ['login-success'],
  setup(props, { emit }) {
    const username = ref('')
    const password = ref('')
    const loading = ref(false)
    const errorMsg = ref('')
    
    const handleLogin = async () => {
      if (!username.value.trim() || !password.value.trim()) {
        errorMsg.value = '请输入用户名和密码'
        return
      }
      
      loading.value = true
      errorMsg.value = ''
      
      try {
        const response = await axios.post('/api/auth/login', {
          username: username.value,
          password: password.value
        })
        
        if (response.data.success) {
          emit('login-success', {
            token: response.data.token,
            user_id: response.data.user_id,
            username: response.data.username
          })
        } else {
          errorMsg.value = response.data.message || '登录失败'
        }
      } catch (error) {
        errorMsg.value = '网络错误，请稍后重试'
      } finally {
        loading.value = false
      }
    }
    
    return {
      username,
      password,
      loading,
      errorMsg,
      handleLogin
    }
  }
}
</script>

<style scoped>
.login-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.login-card {
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  width: 100%;
  max-width: 400px;
}

.login-title {
  text-align: center;
  color: #333;
  margin-bottom: 30px;
  font-size: 24px;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-group label {
  color: #666;
  font-size: 14px;
}

.form-group input {
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 16px;
  transition: border-color 0.3s;
}

.form-group input:focus {
  outline: none;
  border-color: #667eea;
}

.form-group input:disabled {
  background: #f5f5f5;
}

.error-msg {
  color: #e74c3c;
  font-size: 14px;
  text-align: center;
}

.login-btn {
  padding: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  transition: opacity 0.3s;
}

.login-btn:hover:not(:disabled) {
  opacity: 0.9;
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
