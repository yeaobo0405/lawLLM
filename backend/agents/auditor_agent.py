import logging
from typing import List, Dict, Any, Optional
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class AuditorAgent(BaseAgent):
    """
    合规审计员 Agent
    负责对整个工作链进行最终审查。
    """
    def __init__(self):
        super().__init__(
            name="Auditor",
            role="合规审计员",
            instruction="""你的任务是：
1. 审核输出内容是否包含非法、误导性或煽动性的建议。
2. 强制性在文末添加法律风险提示语。
3. 检查生成内容中的法条引用准确性。"""
        )

    def audit(self, task_output: str, original_query: str) -> str:
        """
        审计内容并添加提示。
        """
        prompt = f"""以下是 AI 生成的法律回答（包含事实、分析及建议等）：
{task_output}

原始用户问题：
{original_query}

你的任务：
1. 是否存在严重的合规风险？
2. 是否对法律程序给出了误导性建议？
3. 在结尾处补充一段通用的“特别风险提示”，强调 AI 建议仅供参考。

输出审计后的完整内容（必须是合并全文和风险提示后的成品）。"""
        
        return self.call_llm(prompt, temperature=0.1)
