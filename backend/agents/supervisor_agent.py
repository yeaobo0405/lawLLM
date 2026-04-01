import logging
import json
from typing import List, Dict, Any, Optional
from .base_agent import BaseAgent
from .researcher_agent import ResearcherAgent
from .analyst_agent import AnalystAgent
from .drafter_agent import DrafterAgent
from .auditor_agent import AuditorAgent

logger = logging.getLogger(__name__)

class SupervisorAgent(BaseAgent):
    """
    主控协调员 Agent
    负责识别意图并路由至特定专家 Agent。
    """
    def __init__(self):
        super().__init__(
            name="Supervisor",
            role="主控协调员",
            instruction="""你的任务是：
1. 识别用户的输入意图：法律咨询（Consulting）还是文书起草（Drafting）。
2. 调用合适的专家智能体完成任务。
3. 整合专家意见输出完整回复。"""
        )
        self.researcher = ResearcherAgent()
        self.analyst = AnalystAgent()
        self.drafter = DrafterAgent()
        self.auditor = AuditorAgent()

    def determine_intent(self, user_query: str) -> str:
        """
        判断意图
        """
        prompt = f"以下是用户的输入：{user_query}。\n请判断用户的意图是法律咨询（CONSULTING）还是法律文书起草（DRAFTING）。\n直接输出大写单词，不要包含其他文字。"
        intent = self.call_llm(prompt, temperature=0.1).strip().upper()
        if "CONSULTING" in intent:
            return "CONSULTING"
        if "DRAFTING" in intent:
            return "DRAFTING"
        return "CONSULTING" # 默认咨询

    def run_workflow(self, user_query: str) -> str:
        """
        全量工作流
        """
        intent = self.determine_intent(user_query)
        logger.info(f"检测到意图: {intent}")
        
        # 1. 法律检索 (共通)
        logger.info("正在调用 Researcher...")
        research_result = self.researcher.run(user_query)
        
        # 2. 法律分析 (共通)
        logger.info("正在调用 Analyst...")
        analysis_result = self.analyst.analyze(user_fact=user_query, law_context=research_result)
        
        final_output = f"{research_result}\n\n### [Analyst 专业分析]\n\n{analysis_result}"
        
        # 3. 文书起草 (仅 Drafting)
        if intent == "DRAFTING":
             logger.info("正在调用 Drafter...")
             # 自动选择模板（简化逻辑：通过 LLM 选一个最合适的）
             templates = self.drafter.get_available_templates()
             if not templates:
                 final_output += "\n\n### [Drafter 代书系统提示]\n未发现可用模板，无法生成文书。"
             else:
                 template_list_str = "\n".join(templates)
                 chosen_template = self.call_llm(
                     f"根据用户需求：{user_query}\n以下为可用模板列表：\n{template_list_str}\n请从中选择一个最合适的模板文件名。直接输出文件名，不需要其他描述。",
                     temperature=0.1
                 ).strip()
                 
                 draft_result = self.drafter.draft(
                     user_fact=user_query,
                     analysis_result=analysis_result,
                     template_name=chosen_template
                 )
                 final_output += f"\n\n### [Drafter 生成文书预览]\n\n{draft_result}"

        # 4. 合规审计 (共通)
        logger.info("正在调用 Auditor...")
        audited_output = self.auditor.audit(task_output=final_output, original_query=user_query)
        
        return audited_output
