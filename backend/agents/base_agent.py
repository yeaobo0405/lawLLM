import os
import json
import logging
from typing import List, Dict, Any, Optional
import requests

try:
    from ..config import settings
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import settings

logger = logging.getLogger(__name__)

class BaseAgent:
    """
    智能体基类
    """
    def __init__(self, name: str, role: str, instruction: str):
        self.name = name
        self.role = role
        self.instruction = instruction
        self.api_key = settings.OPENAI_API_KEY
        self.api_base = settings.OPENAI_API_BASE
        self.model = settings.LLM_MODEL_NAME

    def call_llm(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3) -> str:
        """
        调用 LLM 接口
        """
        if not system_prompt:
            system_prompt = f"你是一个名为 {self.name} 的智能体。你的角色是：{self.role}。\n任务指南：{self.instruction}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature
        }
        
        try:
            response = requests.post(self.api_base + "/chat/completions", headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM 调用失败 ({self.name}): {e}")
            return f"Error: 无法从 LLM 获取响应。详情: {str(e)}"

    def call_llm_stream(self, prompt: str, system_prompt: Optional[str] = None, temperature: float = 0.3):
        """
        流式调用 LLM 接口
        """
        if not system_prompt:
            system_prompt = f"你是一个名为 {self.name} 的智能体。你的角色是：{self.role}。\n任务指南：{self.instruction}"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "stream": True # 开启流式
        }
        
        try:
            response = requests.post(self.api_base + "/chat/completions", headers=headers, json=payload, stream=True, timeout=60)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        data_content = decoded_line[6:]
                        if data_content == '[DONE]':
                            break
                        
                        try:
                            json_data = json.loads(data_content)
                            delta = json_data.get('choices', [{}])[0].get('delta', {})
                            if 'content' in delta:
                                yield delta['content']
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"LLM 流式调用失败 ({self.name}): {e}")
            yield f"Error: 无法从 LLM 获取响应。详情: {str(e)}"
