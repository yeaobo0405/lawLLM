"""
上下文管理模块
处理对话上下文的查询改写、指代消解、摘要压缩等功能
支持滑动窗口 + 滚动分层摘要策略
"""
import logging
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage

try:
    from ..config import settings
except ImportError:
    from config import settings

try:
    from .hierarchical_summary import (
        HierarchicalContextManager, 
        HierarchicalSummaryConfig,
        RollingSummarizer,
        SummaryLayer
    )
except ImportError:
    from modules.hierarchical_summary import (
        HierarchicalContextManager, 
        HierarchicalSummaryConfig,
        RollingSummarizer,
        SummaryLayer
    )

logger = logging.getLogger(__name__)


@dataclass
class ContextConfig:
    """上下文配置"""
    max_history_messages: int = 10
    max_context_tokens: int = 2000
    summary_threshold: int = 6
    recent_messages_keep: int = 2


class QueryRewriter:
    """
    查询改写器
    结合对话历史优化用户查询，解决代词指代问题
    """
    
    PRONOUNS = ["它", "他", "她", "这个", "那个", "这些", "那些", "其", "此", "该"]
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def has_pronoun(self, query: str) -> bool:
        """检查查询中是否包含代词"""
        for pronoun in self.PRONOUNS:
            if pronoun in query:
                return True
        return False
    
    def rewrite(self, query: str, conversation_history: List[Dict[str, str]]) -> str:
        """
        改写查询，解决代词指代问题
        
        Args:
            query: 原始查询
            conversation_history: 对话历史
            
        Returns:
            改写后的查询
        """
        if not conversation_history:
            return query
        
        has_pronoun = self.has_pronoun(query)
        
        if not has_pronoun and len(query) > 10:
            return query
        
        history_text = self._format_history(conversation_history)
        
        system_prompt = """你是一个法律咨询对话的查询改写助手。你的任务是根据对话历史，改写用户的当前问题，使其成为一个独立、完整的问题。

改写规则：
1. 如果用户问题中包含代词（它、他、她、这个、那个、这些、那些、其、此、该等），需要根据上下文替换为具体内容
2. 如果用户问题是追问或延续之前的话题，需要补充必要的背景信息
3. 保持问题的核心意图不变
4. 改写后的问题应该能够独立理解，不需要参考之前的对话
5. 直接输出改写后的问题，不要添加任何解释

示例：
历史：用户问"什么是正当防卫？"，助手回答了正当防卫的定义和条件。
当前问题："它的构成要件是什么？"
改写后："正当防卫的构成要件是什么？"

历史：用户问"民法典第几条规定了诉讼时效？"，助手回答"民法典第188条"。
当前问题："期限是多久？"
改写后："民法典第188条规定的诉讼时效期限是多久？"""

        user_message = f"""对话历史：
{history_text}

当前问题：{query}

请输出改写后的问题："""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ])
            
            rewritten = response.content.strip()
            
            if rewritten and len(rewritten) > 0:
                logger.info(f"查询改写: '{query}' -> '{rewritten}'")
                return rewritten
            return query
            
        except Exception as e:
            logger.error(f"查询改写失败: {str(e)}")
            return query
    
    def _format_history(self, history: List[Dict[str, str]], max_turns: int = 3) -> str:
        """格式化对话历史"""
        recent = history[-max_turns * 2:] if len(history) > max_turns * 2 else history
        lines = []
        for msg in recent:
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")[:200]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)


class ContextSummarizer:
    """
    上下文摘要器
    压缩长对话历史，保留关键信息
    """
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def summarize(self, conversation_history: List[Dict[str, str]]) -> str:
        """
        生成对话摘要
        
        Args:
            conversation_history: 对话历史
            
        Returns:
            对话摘要
        """
        if len(conversation_history) < 4:
            return ""
        
        history_text = self._format_history(conversation_history)
        
        system_prompt = """你是一个对话摘要助手。请将以下法律咨询对话历史压缩成一段简洁的摘要。

摘要要求：
1. 保留用户咨询的核心法律问题
2. 保留已经讨论过的关键法律概念和法条
3. 保留用户的关注点和疑问
4. 省略具体的解释和展开内容
5. 摘要长度控制在100字以内
6. 使用第三人称描述"""

        user_message = f"""对话历史：
{history_text}

请生成摘要："""

        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ])
            
            summary = response.content.strip()
            logger.info(f"生成对话摘要: {summary[:50]}...")
            return summary
            
        except Exception as e:
            logger.error(f"生成摘要失败: {str(e)}")
            return ""
    
    def _format_history(self, history: List[Dict[str, str]]) -> str:
        """格式化对话历史"""
        lines = []
        for msg in history:
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")[:300]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)


class SlidingWindowManager:
    """
    滑动窗口管理器
    管理对话历史的滑动窗口，平衡上下文长度和信息完整性
    """
    
    def __init__(self, config: ContextConfig = None):
        self.config = config or ContextConfig()
    
    def get_window(
        self, 
        conversation_history: List[Dict[str, str]],
        summary: str = ""
    ) -> Tuple[List[Dict[str, str]], Optional[str]]:
        """
        获取滑动窗口内的对话历史
        
        Args:
            conversation_history: 完整对话历史
            summary: 之前的对话摘要
            
        Returns:
            (窗口内的对话历史, 新摘要或None)
        """
        total_messages = len(conversation_history)
        
        if total_messages <= self.config.max_history_messages:
            return conversation_history, None
        
        messages_to_summarize = total_messages - self.config.recent_messages_keep
        
        if messages_to_summarize > self.config.summary_threshold:
            old_messages = conversation_history[:messages_to_summarize]
            recent_messages = conversation_history[messages_to_summarize:]
            
            return recent_messages, None
        else:
            return conversation_history[-self.config.max_history_messages:], None
    
    def estimate_tokens(self, messages: List[Dict[str, str]]) -> int:
        """估算消息的token数量（简单估算：中文约1.5字符/token）"""
        total_chars = sum(len(msg.get("content", "")) for msg in messages)
        return int(total_chars / 1.5)


class ContextManager:
    """
    上下文管理器
    整合查询改写、指代消解、滚动分层摘要等功能
    """
    
    def __init__(self, llm: ChatOpenAI = None, config: ContextConfig = None, use_hierarchical: bool = True):
        self.config = config or ContextConfig()
        self.use_hierarchical = use_hierarchical
        
        if llm is None:
            self.llm = ChatOpenAI(
                model=settings.LLM_MODEL_NAME,
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                temperature=0.3
            )
        else:
            self.llm = llm
        
        self.query_rewriter = QueryRewriter(self.llm)
        self.summarizer = ContextSummarizer(self.llm)
        self.sliding_window = SlidingWindowManager(self.config)
        
        if use_hierarchical:
            hierarchical_config = HierarchicalSummaryConfig(
                layer0_max_messages=self.config.recent_messages_keep * 2,
                layer1_max_messages=self.config.max_history_messages,
                layer1_max_tokens=300,
                layer2_max_tokens=150,
                min_messages_for_summary=self.config.summary_threshold
            )
            self.hierarchical_manager = HierarchicalContextManager(
                self.llm, 
                hierarchical_config,
                memory_store=None # 会在 process_query 中动态设置或初始化时传入
            )
        else:
            self.hierarchical_manager = None
        
        self.session_summaries: Dict[str, str] = {}
    
    def process_query(
        self, 
        query: str, 
        conversation_history: List[Dict[str, str]],
        session_id: str = "default"
    ) -> Tuple[str, List[Dict[str, str]], str]:
        """
        处理查询，返回改写后的查询和处理后的上下文
        
        Args:
            query: 原始查询
            conversation_history: 对话历史
            session_id: 会话ID
            
        Returns:
            (改写后的查询, 处理后的对话历史, 对话摘要)
        """
        rewritten_query = self.query_rewriter.rewrite(query, conversation_history)
        
        if self.use_hierarchical and self.hierarchical_manager:
            # 确保 hierarchical_manager 拥有 memory_store 的引用
            if not self.hierarchical_manager.memory_store and hasattr(self, 'memory_store'):
                self.hierarchical_manager.memory_store = self.memory_store

            user_id = getattr(self, 'user_id', 0) # 如果没有传 user_id，尝试从 self 中获取
            
            layer0, layer1, layer2 = self.hierarchical_manager.process(
                session_id, user_id, conversation_history
            )
            
            layer1_summary = layer1.summary
            layer2_summary = layer2.summary
            
            combined_summary = ""
            if layer2_summary:
                combined_summary = f"[历史]{layer2_summary}"
            if layer1_summary:
                if combined_summary:
                    combined_summary += f"\n[近期]{layer1_summary}"
                else:
                    combined_summary = layer1_summary
            
            return rewritten_query, layer0, combined_summary
        
        windowed_history, _ = self.sliding_window.get_window(conversation_history)
        
        summary = self.session_summaries.get(session_id, "")
        
        if len(conversation_history) > self.config.summary_threshold:
            messages_for_summary = conversation_history[:-self.config.recent_messages_keep]
            if messages_for_summary:
                new_summary = self.summarizer.summarize(messages_for_summary)
                if new_summary:
                    self.session_summaries[session_id] = new_summary
                    summary = new_summary
        
        return rewritten_query, windowed_history, summary
    
    def build_context_messages(
        self,
        query: str,
        conversation_history: List[Dict[str, str]],
        summary: str = ""
    ) -> List:
        """
        构建包含上下文的消息列表
        
        Args:
            query: 当前查询
            conversation_history: 对话历史
            summary: 对话摘要（支持分层格式：[历史]...[近期]...）
            
        Returns:
            LangChain消息列表
        """
        messages = []
        
        if summary:
            if "[历史]" in summary or "[近期]" in summary:
                parts = summary.split("\n")
                for part in parts:
                    if part.startswith("[历史]"):
                        messages.append(SystemMessage(
                            content=f"【历史对话背景】\n{part.replace('[历史]', '')}"
                        ))
                    elif part.startswith("[近期]"):
                        messages.append(SystemMessage(
                            content=f"【近期对话摘要】\n{part.replace('[近期]', '')}"
                        ))
            else:
                context_system = f"""以下是之前对话的摘要，供你参考：
{summary}

请继续回答用户的问题，保持对话的连贯性。"""
                messages.append(SystemMessage(content=context_system))
        
        for msg in conversation_history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))
        
        return messages
    
    def clear_session(self, session_id: str):
        """清除会话的摘要缓存"""
        if session_id in self.session_summaries:
            del self.session_summaries[session_id]
        
        if self.hierarchical_manager:
            self.hierarchical_manager.clear_session(session_id)
    
    def get_hierarchical_stats(self, session_id: str) -> Dict:
        """获取分层摘要统计信息"""
        if self.hierarchical_manager:
            return self.hierarchical_manager.get_compression_stats(session_id)
        return {}


class EnhancedMemoryManager:
    """
    增强的记忆管理器
    结合 ConversationMemory 和 ContextManager（支持滚动分层摘要）
    """
    
    def __init__(self, memory_store, llm: ChatOpenAI = None, config: ContextConfig = None, use_hierarchical: bool = True):
        self.memory_store = memory_store
        self.context_manager = ContextManager(llm, config, use_hierarchical)
        self.context_manager.memory_store = memory_store
    
    def get_processed_context(
        self,
        session_id: str,
        user_id: int,
        current_query: str
    ) -> Tuple[str, List[Dict[str, str]], str]:
        """
        获取处理后的上下文
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            current_query: 当前查询
            
        Returns:
            (改写后的查询, 对话历史, 摘要)
        """
        history = self.memory_store.get_history(
            session_id, 
            limit=self.context_manager.config.max_history_messages + 10,
            user_id=user_id
        )
        
        self.context_manager.user_id = user_id # 动态设置当前上下文的用户ID
        
        return self.context_manager.process_query(current_query, history, session_id)
    
    def add_message(self, session_id: str, role: str, content: str, user_id: int = 0):
        """添加消息到记忆存储"""
        self.memory_store.add_message(session_id, role, content, user_id)
    
    def clear_memory(self, session_id: str, user_id: int = 0):
        """清除记忆"""
        self.memory_store.clear_history(session_id, user_id)
        self.context_manager.clear_session(session_id)
    
    def get_hierarchical_stats(self, session_id: str) -> Dict:
        """获取分层摘要统计信息"""
        return self.context_manager.get_hierarchical_stats(session_id)
