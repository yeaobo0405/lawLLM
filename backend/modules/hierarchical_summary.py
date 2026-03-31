"""
滚动分层摘要模块
实现滑动窗口 + 滚动分层摘要策略
"""
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
import tiktoken
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

try:
    from ..config import settings
except ImportError:
    from config import settings

logger = logging.getLogger(__name__)


@dataclass
class SummaryLayer:
    """
    摘要层级
    
    Layer 0: 最近消息（完整保留）
    Layer 1: 短期摘要（近期对话压缩）
    Layer 2: 长期摘要（历史对话高度压缩）
    """
    level: int
    summary: str = ""
    message_count: int = 0
    last_updated: str = ""
    covered_message_ids: List[int] = field(default_factory=list)
    
    def is_empty(self) -> bool:
        return not self.summary
    
    def token_count(self) -> int:
        if not self.summary:
            return 0
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(self.summary))
        except Exception:
            return int(len(self.summary) / 1.5)


@dataclass
class HierarchicalSummaryConfig:
    """分层摘要配置"""
    layer0_max_messages: int = 4
    layer1_max_messages: int = 8
    layer1_max_tokens: int = 300
    layer2_max_tokens: int = 150
    min_messages_for_summary: int = 4


class RollingSummarizer:
    """
    滚动摘要器
    实现增量更新和分层压缩
    """
    
    def __init__(self, llm: ChatOpenAI, config: HierarchicalSummaryConfig = None):
        self.llm = llm
        self.config = config or HierarchicalSummaryConfig()
        
        self.session_layers: Dict[str, Dict[int, SummaryLayer]] = {}
        self.session_processed_count: Dict[str, int] = {}
    
    def _get_session_layers(self, session_id: str) -> Dict[int, SummaryLayer]:
        """获取或创建会话的分层结构"""
        if session_id not in self.session_layers:
            self.session_layers[session_id] = {
                0: SummaryLayer(level=0),
                1: SummaryLayer(level=1),
                2: SummaryLayer(level=2)
            }
            self.session_processed_count[session_id] = 0
        return self.session_layers[session_id]
    
    def update(
        self,
        session_id: str,
        user_id: int,
        new_messages: List[Dict[str, str]],
        all_messages: List[Dict[str, str]],
        memory_store = None
    ) -> Tuple[SummaryLayer, SummaryLayer, List[Dict[str, str]]]:
        """
        增量更新分层摘要
        
        Args:
            session_id: 会话ID
            new_messages: 新增的消息列表（未处理的消息）
            all_messages: 所有消息列表
            
        Returns:
            (Layer1摘要, Layer2摘要, Layer0完整消息)
        """
        layers = self._get_session_layers(session_id)
        
        layer0_messages = all_messages[-self.config.layer0_max_messages:]
        
        remaining_messages = all_messages[:-self.config.layer0_max_messages] if len(all_messages) > self.config.layer0_max_messages else []
        
        if len(remaining_messages) >= self.config.min_messages_for_summary:
            total_remaining = len(remaining_messages)
            layer1_capacity = self.config.layer1_max_messages
            
            if total_remaining <= layer1_capacity:
                layer1_messages = remaining_messages
                older_messages = []
            else:
                layer1_messages = remaining_messages[-layer1_capacity:]
                older_messages = remaining_messages[:-layer1_capacity]
            
            if layer1_messages:
                new_layer1 = self._update_layer1_incremental(session_id, layers[1], layer1_messages)
                layers[1] = new_layer1
            
            if older_messages:
                new_layer2 = self._update_layer2_incremental(session_id, layers[2], older_messages)
                layers[2] = new_layer2
        elif len(remaining_messages) > 0:
            new_layer1 = self._update_layer1_incremental(session_id, layers[1], remaining_messages)
            layers[1] = new_layer1
        
        self.session_processed_count[session_id] = len(all_messages)
        
        # 如果提供了 memory_store，则持久化摘要
        if memory_store:
            memory_store.save_summary(
                session_id, user_id,
                layers[1].summary, layers[2].summary,
                layers[1].message_count, layers[2].message_count
            )
        
        return layers[1], layers[2], layer0_messages
    
    def _update_layer1_incremental(
        self,
        session_id: str,
        current_layer: SummaryLayer,
        messages: List[Dict[str, str]]
    ) -> SummaryLayer:
        """
        增量更新Layer1
        """
        if current_layer.is_empty():
            summary = self._generate_summary(messages, max_length=150)
        else:
            processed_count = current_layer.message_count
            if len(messages) > processed_count:
                new_messages = messages[processed_count:]
                new_content = self._format_messages(new_messages)
                summary = self._merge_summaries(
                    current_layer.summary,
                    new_content,
                    max_length=self.config.layer1_max_tokens
                )
            else:
                summary = current_layer.summary
        
        return SummaryLayer(
            level=1,
            summary=summary,
            message_count=len(messages),
            last_updated=datetime.now().isoformat()
        )
    
    def _update_layer2_incremental(
        self,
        session_id: str,
        current_layer: SummaryLayer,
        messages: List[Dict[str, str]]
    ) -> SummaryLayer:
        """
        增量更新Layer2
        """
        if current_layer.is_empty():
            summary = self._generate_summary(messages, max_length=100, focus="核心要点")
        else:
            processed_count = current_layer.message_count
            if len(messages) > processed_count:
                new_messages = messages[processed_count:]
                new_summary = self._generate_summary(new_messages, max_length=80, focus="关键信息")
                summary = self._merge_summaries(
                    current_layer.summary,
                    new_summary,
                    max_length=self.config.layer2_max_tokens
                )
            else:
                summary = current_layer.summary
        
        return SummaryLayer(
            level=2,
            summary=summary,
            message_count=len(messages),
            last_updated=datetime.now().isoformat()
        )
    
    def _generate_summary(
        self,
        messages: List[Dict[str, str]],
        max_length: int = 150,
        focus: str = "重要内容"
    ) -> str:
        """
        使用LLM生成摘要
        """
        if not messages:
            return ""
        
        history_text = self._format_messages(messages)
        
        system_prompt = f"""你是一个对话摘要专家。请将以下法律咨询对话压缩成简洁的摘要。

要求：
1. 提取{focus}：核心法律问题、相关法条、用户关注点
2. 控制在{max_length}字以内
3. 使用第三人称
4. 保留关键实体名称（如法条编号、法律名称）
5. 省略详细解释和展开内容"""

        user_message = f"对话内容：\n{history_text}\n\n请生成摘要："

        try:
            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=4, max=10),
                retry=retry_if_exception_type(Exception)
            )
            def invoke_llm(msgs):
                return self.llm.invoke(msgs)
            
            response = invoke_llm([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ])
            
            summary = response.content.strip()
            logger.info(f"生成摘要(L{max_length}字): {summary[:50]}...")
            return summary
            
        except Exception as e:
            logger.error(f"生成摘要失败: {str(e)}")
            return ""
    
    def _merge_summaries(
        self,
        old_summary: str,
        new_content: str,
        max_length: int = 300
    ) -> str:
        """
        合并旧摘要和新内容，生成新的压缩摘要
        """
        system_prompt = f"""你是一个对话摘要合并专家。请将旧摘要和新对话内容合并成一个新的摘要。

要求：
1. 保留旧摘要中的关键信息
2. 整合新内容中的重要信息
3. 去除重复内容
4. 控制在{max_length}字以内
5. 保持时间顺序的逻辑性"""

        user_message = f"""旧摘要：
{old_summary}

新对话内容：
{new_content}

请生成合并后的摘要："""

        try:
            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=4, max=10),
                retry=retry_if_exception_type(Exception)
            )
            def invoke_llm(msgs):
                return self.llm.invoke(msgs)
            
            response = invoke_llm([
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_message)
            ])
            
            merged = response.content.strip()
            logger.info(f"合并摘要: {merged[:50]}...")
            return merged
            
        except Exception as e:
            logger.error(f"合并摘要失败: {str(e)}")
            return old_summary
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """格式化消息列表"""
        lines = []
        for msg in messages:
            role = "用户" if msg.get("role") == "user" else "助手"
            content = msg.get("content", "")[:200]
            lines.append(f"{role}: {content}")
        return "\n".join(lines)
    
    def get_context(
        self,
        session_id: str
    ) -> Tuple[SummaryLayer, SummaryLayer, List[Dict[str, str]]]:
        """
        获取分层上下文
        
        Returns:
            (layer1, layer2, layer0消息列表占位)
        """
        layers = self._get_session_layers(session_id)
        return (
            layers[1],
            layers[2],
            []
        )
    
    def clear_session(self, session_id: str):
        """清除会话的分层摘要"""
        if session_id in self.session_layers:
            del self.session_layers[session_id]
        if session_id in self.session_processed_count:
            del self.session_processed_count[session_id]
    
    def get_stats(self, session_id: str) -> Dict:
        """获取分层摘要统计信息"""
        layers = self._get_session_layers(session_id)
        return {
            "layer1_tokens": layers[1].token_count(),
            "layer2_tokens": layers[2].token_count(),
            "layer1_messages": layers[1].message_count,
            "layer2_messages": layers[2].message_count,
            "total_summary_tokens": layers[1].token_count() + layers[2].token_count()
        }


class HierarchicalContextManager:
    """
    分层上下文管理器
    整合滑动窗口和滚动分层摘要
    """
    
    def __init__(self, llm: ChatOpenAI = None, config: HierarchicalSummaryConfig = None, memory_store = None):
        self.config = config or HierarchicalSummaryConfig()
        self.memory_store = memory_store
        
        if llm is None:
            self.llm = ChatOpenAI(
                model=settings.LLM_MODEL_NAME,
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_API_BASE,
                temperature=0.3
            )
        else:
            self.llm = llm
        
        self.rolling_summarizer = RollingSummarizer(self.llm, self.config)
        
        self.session_last_count: Dict[str, int] = {}
    
    def process(
        self,
        session_id: str,
        user_id: int,
        conversation_history: List[Dict[str, str]]
    ) -> Tuple[List[Dict[str, str]], SummaryLayer, SummaryLayer]:
        """
        处理对话历史，返回分层压缩后的上下文
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            conversation_history: 完整对话历史
            
        Returns:
            (Layer0完整消息, Layer1摘要, Layer2摘要)
        """
        layers = self.rolling_summarizer._get_session_layers(session_id)
        
        # 尝试从数据库加载摘要（如果内存中没有）
        if self.memory_store and layers[1].is_empty() and layers[2].is_empty():
            db_summary = self.memory_store.get_summary(session_id, user_id)
            if db_summary:
                layers[1].summary = db_summary["layer1_summary"]
                layers[1].message_count = db_summary["layer1_msg_count"]
                layers[2].summary = db_summary["layer2_summary"]
                layers[2].message_count = db_summary["layer2_msg_count"]
                logger.info(f"从数据库加载了会话 {session_id} 的分层摘要")

        last_count = self.session_last_count.get(session_id, 0)
        current_count = len(conversation_history)
        
        new_messages = conversation_history[last_count:] if current_count > last_count else []
        
        if new_messages:
            layer1, layer2, layer0 = self.rolling_summarizer.update(
                session_id, user_id, new_messages, conversation_history, self.memory_store
            )
        else:
            layer1, layer2, layer0 = self.rolling_summarizer.get_context(session_id)
            layer0 = conversation_history[-self.config.layer0_max_messages:] if conversation_history else []
        
        self.session_last_count[session_id] = current_count
        
        return layer0, layer1, layer2
    
    def build_messages(
        self,
        layer0: List[Dict[str, str]],
        layer1_summary: str,
        layer2_summary: str,
        current_query: str
    ) -> List:
        """
        构建LLM消息列表
        
        Args:
            layer0: Layer0完整消息
            layer1_summary: Layer1摘要
            layer2_summary: Layer2摘要
            current_query: 当前查询
            
        Returns:
            LangChain消息列表
        """
        messages = []
        
        if layer2_summary:
            messages.append(SystemMessage(
                content=f"【历史背景】\n{layer2_summary}\n"
            ))
        
        if layer1_summary:
            messages.append(SystemMessage(
                content=f"【近期对话摘要】\n{layer1_summary}\n"
            ))
        
        for msg in layer0:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))
        
        return messages
    
    def get_compression_stats(self, session_id: str) -> Dict:
        """获取压缩统计信息"""
        return self.rolling_summarizer.get_stats(session_id)
    
    def clear_session(self, session_id: str):
        """清除会话"""
        self.rolling_summarizer.clear_session(session_id)
        if session_id in self.session_last_count:
            del self.session_last_count[session_id]
