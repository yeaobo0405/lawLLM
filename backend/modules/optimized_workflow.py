"""
优化的法律咨询工作流
支持流式输出，简化流程，增强上下文处理
"""
import logging
from typing import Dict, Any, List, Optional, Generator
from dataclasses import dataclass
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage

try:
    from ..config import settings
except ImportError:
    from config import settings

try:
    from .rag_retriever import HybridRetriever, SearchResult
except ImportError:
    from modules.rag_retriever import HybridRetriever, SearchResult

try:
    from .memory_store import ConversationMemory
except ImportError:
    from modules.memory_store import ConversationMemory

try:
    from .context_manager import EnhancedMemoryManager, ContextConfig
except ImportError:
    from modules.context_manager import EnhancedMemoryManager, ContextConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: str
    is_valid: bool
    reason: str


class OptimizedLegalWorkflow:
    """
    优化的法律咨询工作流
    简化流程，支持流式输出
    """
    
    ILLEGAL_KEYWORDS = [
        "如何犯罪", "逃避法律", "规避法律", "违法", "犯罪方法",
        "如何偷税", "如何逃税", "如何洗钱", "如何诈骗"
    ]
    
    DISCLAIMER = """
【免责声明】
本系统提供的法律信息仅供参考，不构成法律意见或建议。具体法律问题请咨询专业律师。
本系统基于公开法律文献和案例，不保证信息的完整性和时效性。
"""
    
    # 检索结果相关度阈值
    RELEVANCE_THRESHOLD = 0.3
    
    def __init__(self, hybrid_retriever: HybridRetriever, context_config: ContextConfig = None):
        """
        初始化工作流
        
        Args:
            hybrid_retriever: 混合检索器
            context_config: 上下文配置
        """
        self.hybrid_retriever = hybrid_retriever
        
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL_NAME,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
            temperature=0.7,
            streaming=True
        )
        
        self.memory_store = ConversationMemory()
        
        self.context_config = context_config or ContextConfig(
            max_history_messages=10,
            max_context_tokens=2000,
            summary_threshold=6,
            recent_messages_keep=2
        )
        
        self.enhanced_memory = EnhancedMemoryManager(
            self.memory_store, 
            self.llm, 
            self.context_config
        )
    
    def _check_intent_fast(self, query: str) -> IntentResult:
        """
        快速意图检查（不调用LLM）
        
        Args:
            query: 用户提问
            
        Returns:
            IntentResult对象
        """
        for keyword in self.ILLEGAL_KEYWORDS:
            if keyword in query:
                return IntentResult(
                    intent="非法请求",
                    is_valid=False,
                    reason=f"检测到敏感关键词：{keyword}"
                )
        
        return IntentResult(
            intent="法律咨询",
            is_valid=True,
            reason="通过"
        )
    
    def _check_search_quality(self, search_results: List[SearchResult]) -> tuple[bool, str]:
        """
        检查检索结果质量
        
        Args:
            search_results: 检索结果
            
        Returns:
            (是否质量合格, 原因说明)
        """
        if not search_results:
            return False, "未检索到相关文档"
        
        # 检查最高相关度分数
        max_score = max(r.score for r in search_results) if search_results else 0
        
        if max_score < self.RELEVANCE_THRESHOLD:
            return False, f"检索结果相关度过低（最高{max_score:.2f}，阈值{self.RELEVANCE_THRESHOLD}）"
        
        return True, "检索结果质量合格"
    
    def _build_context(self, search_results: List[SearchResult]) -> str:
        """
        构建上下文
        
        Args:
            search_results: 检索结果
            
        Returns:
            上下文字符串
        """
        context_parts = []
        
        for i, result in enumerate(search_results[:5], 1):
            if result.doc_type == "law":
                context_parts.append(
                    f"【法条{i}】{result.law_name} - 第{result.article_number}条\n"
                    f"文件路径：{result.file_path}\n"
                    f"内容：{result.content[:500]}..."
                )
            else:
                context_parts.append(
                    f"【案例{i}】{result.case_type}案件\n"
                    f"文件路径：{result.file_path}\n"
                    f"内容：{result.content[:500]}..."
                )
        
        return "\n\n".join(context_parts)
    
    def _add_source_buttons(self, answer: str, search_results: List[SearchResult]) -> str:
        """
        在回答中添加查看原文按钮
        
        Args:
            answer: 原始回答
            search_results: 检索结果
            
        Returns:
            添加按钮后的回答
        """
        import json
        import re
        
        for result in search_results:
            if result.doc_type == "law" and result.article_number:
                patterns = [
                    f"第{result.article_number}条",
                    f"第 {result.article_number} 条",
                    f"第{result.article_number} 条",
                    f"第 {result.article_number}条"
                ]
                
                for pattern in patterns:
                    if pattern in answer and result.file_path:
                        source_data = {
                            "type": "law",
                            "law_name": result.law_name,
                            "article_number": result.article_number,
                            "content": result.content,
                            "file_path": result.file_path,
                            "chapter": result.chapter or ""
                        }
                        json_data = json.dumps(source_data, ensure_ascii=False)
                        button = f'<span class="source-btn" data-source=\'{json_data}\'>📄查看原文</span>'
                        answer = answer.replace(pattern, f"{pattern}{button}", 1)
                        break
        
        return answer
    
    def run_fast(self, query: str, session_id: str = "default", user_id: int = 0) -> Dict[str, Any]:
        """
        快速运行工作流（非流式）
        
        Args:
            query: 用户提问
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            工作流执行结果
        """
        rewritten_query, history, summary = self.enhanced_memory.get_processed_context(
            session_id, user_id, query
        )
        
        if rewritten_query != query:
            logger.info(f"查询改写: '{query}' -> '{rewritten_query}'")
        
        intent_result = self._check_intent_fast(rewritten_query)
        
        if not intent_result.is_valid:
            return {
                "success": False,
                "answer": "抱歉，我无法回答这个问题。检测到您的请求可能涉及不合规内容。",
                "disclaimer": self.DISCLAIMER,
                "search_results": []
            }
        
        search_results = self.hybrid_retriever.hybrid_search(rewritten_query)
        
        is_quality_ok, quality_reason = self._check_search_quality(search_results)
        
        if not is_quality_ok:
            logger.info(f"检索结果质量不佳，使用基座模型回答: {quality_reason}")
            
            system_prompt_general = """你是一个专业的法律咨询助手。请基于你的法律知识回答用户的问题。

要求：
1. 回答要准确、专业
2. 如果不确定，请明确告知用户
3. 建议用户咨询专业律师获取具体法律意见
4. 回答要简洁明了"""

            messages = [SystemMessage(content=system_prompt_general)]
            
            if summary:
                messages.append(SystemMessage(content=f"之前的对话摘要：{summary}"))
            
            for msg in history:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))
            
            messages.append(HumanMessage(content=f"用户问题：{query}"))
            
            try:
                @retry(
                    stop=stop_after_attempt(3),
                    wait=wait_exponential(multiplier=1, min=4, max=10),
                    retry=retry_if_exception_type(Exception)
                )
                def invoke_llm(msgs):
                    return self.llm.invoke(msgs)
                
                response = invoke_llm(messages)
                answer = response.content
                
                self.memory_store.add_message(session_id, "user", query, user_id)
                self.memory_store.add_message(session_id, "assistant", answer, user_id)
                
                return {
                    "success": True,
                    "answer": answer,
                    "disclaimer": self.DISCLAIMER,
                    "search_results": []
                }
                
            except Exception as e:
                logger.error(f"生成回答失败: {str(e)}")
                return {
                    "success": False,
                    "answer": "抱歉，系统处理过程中出现错误，请稍后重试。",
                    "disclaimer": self.DISCLAIMER,
                    "search_results": []
                }
        
        context = self._build_context(search_results)
        
        system_prompt = """你是一个专业的法律咨询助手。请根据系统检索到的法律条文和案例，回答用户的问题。

要求：
1. 回答要准确、专业、有法律依据
2. 引用具体的法律条文时，直接写"第X条"
3. 回答要简洁明了，避免冗长
4. 禁止说"根据您提供的"，直接陈述法律内容即可"""

        messages = [SystemMessage(content=system_prompt)]
        
        if summary:
            messages.append(SystemMessage(content=f"之前的对话摘要：{summary}"))
        
        for msg in history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))
        
        user_message = f"""用户问题：{query}

参考法律条文和案例：
{context}

请根据以上信息回答用户问题。"""
        
        messages.append(HumanMessage(content=user_message))
        
        try:
            @retry(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=1, min=4, max=10),
                retry=retry_if_exception_type(Exception)
            )
            def invoke_llm(msgs):
                return self.llm.invoke(msgs)
            
            response = invoke_llm(messages)
            answer = response.content
            
            answer = self._add_source_buttons(answer, search_results)
            
            self.memory_store.add_message(session_id, "user", query, user_id)
            self.memory_store.add_message(session_id, "assistant", answer, user_id)
            
            return {
                "success": True,
                "answer": answer,
                "disclaimer": self.DISCLAIMER,
                "search_results": []
            }
            
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}")
            return {
                "success": False,
                "answer": "抱歉，系统处理过程中出现错误，请稍后重试。",
                "disclaimer": self.DISCLAIMER,
                "search_results": []
            }
    
    def run_stream(self, query: str, session_id: str = "default", user_id: int = 0) -> Generator[str, None, None]:
        """
        流式运行工作流
        
        Args:
            query: 用户提问
            session_id: 会话ID
            user_id: 用户ID
            
        Yields:
            流式输出的文本块
        """
        import json
        
        rewritten_query, history, summary = self.enhanced_memory.get_processed_context(
            session_id, user_id, query
        )
        
        if rewritten_query != query:
            logger.info(f"查询改写: '{query}' -> '{rewritten_query}'")
        
        intent_result = self._check_intent_fast(rewritten_query)
        
        if not intent_result.is_valid:
            yield f"data: {json.dumps({'type': 'answer', 'content': '抱歉，我无法回答这个问题。检测到您的请求可能涉及不合规内容。'}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            return
        
        yield f"data: {json.dumps({'type': 'status', 'content': '正在检索相关法律条文...'}, ensure_ascii=False)}\n\n"
        
        search_results = self.hybrid_retriever.hybrid_search(rewritten_query)
        
        is_quality_ok, quality_reason = self._check_search_quality(search_results)
        
        if not is_quality_ok:
            logger.info(f"检索结果质量不佳，使用基座模型回答: {quality_reason}")
            
            system_prompt_general = """你是一个专业的法律咨询助手。请基于你的法律知识回答用户的问题。

要求：
1. 回答要准确、专业
2. 如果不确定，请明确告知用户
3. 建议用户咨询专业律师获取具体法律意见
4. 回答要简洁明了"""

            messages = [SystemMessage(content=system_prompt_general)]
            
            if summary:
                messages.append(SystemMessage(content=f"之前的对话摘要：{summary}"))
            
            for msg in history:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))
            
            messages.append(HumanMessage(content=f"用户问题：{query}"))
            
            try:
                full_answer = ""
                for chunk in self.llm.stream(messages):
                    if chunk.content:
                        full_answer += chunk.content
                        yield f"data: {json.dumps({'type': 'answer', 'content': chunk.content}, ensure_ascii=False)}\n\n"
                
                self.memory_store.add_message(session_id, "user", query, user_id)
                self.memory_store.add_message(session_id, "assistant", full_answer, user_id)
                
                yield f"data: {json.dumps({'type': 'disclaimer', 'content': self.DISCLAIMER}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                logger.error(f"生成回答失败: {str(e)}")
                yield f"data: {json.dumps({'type': 'error', 'content': '抱歉，系统处理过程中出现错误，请稍后重试。'}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            
            return
        
        yield f"data: {json.dumps({'type': 'status', 'content': '正在生成回答...'}, ensure_ascii=False)}\n\n"
        
        context = self._build_context(search_results)
        
        system_prompt = """你是一个专业的法律咨询助手。请根据系统检索到的法律条文和案例，回答用户的问题。

要求：
1. 回答要准确、专业、有法律依据
2. 引用具体的法律条文时，直接写"第X条"
3. 回答要简洁明了，避免冗长
4. 禁止说"根据您提供的"，直接陈述法律内容即可"""

        messages = [SystemMessage(content=system_prompt)]
        
        if summary:
            messages.append(SystemMessage(content=f"之前的对话摘要：{summary}"))
        
        for msg in history:
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))
        
        user_message = f"""用户问题：{query}

参考法律条文和案例：
{context}

请根据以上信息回答用户问题。"""
        
        messages.append(HumanMessage(content=user_message))
        
        try:
            full_answer = ""
            for chunk in self.llm.stream(messages):
                if chunk.content:
                    full_answer += chunk.content
                    yield f"data: {json.dumps({'type': 'answer', 'content': chunk.content}, ensure_ascii=False)}\n\n"
            
            full_answer = self._add_source_buttons(full_answer, search_results)
            
            self.memory_store.add_message(session_id, "user", query, user_id)
            self.memory_store.add_message(session_id, "assistant", full_answer, user_id)
            
            yield f"data: {json.dumps({'type': 'replace', 'content': full_answer}, ensure_ascii=False)}\n\n"
            
            yield f"data: {json.dumps({'type': 'disclaimer', 'content': self.DISCLAIMER}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
            
        except Exception as e:
            logger.error(f"流式工作流执行失败: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'content': '抱歉，系统处理过程中出现错误，请稍后重试。'}, ensure_ascii=False)}\n\n"
    
    def clear_memory(self, session_id: str = "default", user_id: int = 0):
        """
        清除对话记忆
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
        """
        self.enhanced_memory.clear_memory(session_id, user_id)
        logger.info(f"已清除会话记忆: {session_id}")
