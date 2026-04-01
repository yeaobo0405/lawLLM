import os
import logging
import yaml
from typing import List, Dict, Any, Optional
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class DrafterAgent(BaseAgent):
    """
    文书代书员 Agent
    负责自动化填充法律文书模板。
    """
    def __init__(self, template_dir: str = "./backend/data/templates"):
        super().__init__(
            name="Drafter",
            role="文书代书员",
            instruction="""你的任务是根据分析师 (Analyst) 得到的结论和案情事实，生成标准法律文书。
你需要保持文书的严谨性，确保所有占位符如 {{原告姓名}} 得到正确填充。"""
        )
        self.template_dir = template_dir

    def get_available_templates(self) -> List[str]:
        """
        获取可选模板列表
        """
        if not os.path.exists(self.template_dir):
            return []
        return [f for f in os.listdir(self.template_dir) if f.endswith('.md')]

    def draft(self, user_fact: str, analysis_result: str, template_name: str) -> str:
        """
        生成文书内容
        """
        template_path = os.path.join(self.template_dir, template_name)
        if not os.path.exists(template_path):
             return f"Error: 找不到指定的模板 {template_name}。"
             
        with open(template_path, 'r', encoding='utf-8') as f:
             template_content = f.read()
             
        # 分离 YAML 头部（如果有）
        # if template_content.startswith('---'):
        #     # 处理 YAML
        #     pass

        prompt = f"""以下是可用的法律文书模板：
---
{template_content}
---

以下是本案的案情事实：
{user_fact}

以下是分析师的专业意见：
{analysis_result}

请根据以上信息，将模板中的占位符填充完整，输出完整的文书 Markdown。不要包含任何说明性文字。"""
        
        return self.call_llm(prompt, temperature=0.3)
    def stream_draft(self, user_fact: str, analysis_result: str, template_name: str):
        """
        流式生成文书内容
        """
        template_path = os.path.join(self.template_dir, template_name)
        template_content = ""
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

        prompt = f"""以下是可用的法律文书模板：
---
{template_content}
---

以下是本案的案情事实：
{user_fact}

以下是分析师的专业意见：
{analysis_result}

请根据以上信息，将模板中的占位符填充完整，输出完整的文书 Markdown。不要包含任何说明性文字。"""
        
        return self.call_llm_stream(prompt, temperature=0.3)
