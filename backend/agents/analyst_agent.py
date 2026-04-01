import logging
from typing import List, Dict, Any, Optional
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)

class AnalystAgent(BaseAgent):
    """
    案情分析师 Agent
    负责应用法律三段论进行逻辑推演。
    """
    def __init__(self):
        super().__init__(
            name="Analyst",
            role="案情分析师",
            instruction="""你的任务是使用法律三段论（IRAC/法条+核心事实=法律评价）进行法律推理。
你需要结合用户提供的事实和 Researcher 提供的法条，给出专业的分析结论、责任分配及初步法律建议。"""
        )

    def analyze(self, user_fact: str, law_context: str) -> str:
        """
        案情分析逻辑
        """
        prompt = f"""以下是用户描述的案件事实：
{user_fact}

以下是相关法条及其具体内容：
{law_context}

请严格按照以下格式提供深度分析：
1. **涉及法律问题 (Issue)**：概括核心法律矛盾。
2. **规则适用 (Rule)**：引用具体适用的法条。
3. **案情解析 (Analysis)**：详细论述法条如何适用于该事实。
4. **法律结论 (Conclusion)**：胜算评估、损失计算或初步建议。
"""
        return self.call_llm(prompt, temperature=0.3)
    def stream_analyze(self, user_fact: str, law_context: str):
        """
        流式案情分析
        """
        prompt = f"""以下是用户描述的案件事实：
{user_fact}

以下是相关法条及其具体内容：
{law_context}

请严格按照以下格式提供深度分析：
1. **涉及法律问题 (Issue)**：概括核心法律矛盾。
2. **规则适用 (Rule)**：引用具体适用的法条。
3. **案情解析 (Analysis)**：详细论述法条如何适用于该事实。
4. **法律结论 (Conclusion)**：胜算评估、损失计算或初步建议。
"""
        return self.call_llm_stream(prompt, temperature=0.3)
