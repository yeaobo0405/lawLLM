"""
LangGraph工作流模块
编排意图识别→查询改写→混合检索→rerank重排→回答生成→免责声明→输出全流程
"""
import logging
from typing import Dict, Any, List, Optional, TypedDict, Annotated
from dataclasses import dataclass
import operator

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph, END

from config import settings
from modules.rag_retriever import HybridRetriever, SearchResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversationState(TypedDict):
    """对话状态"""
    query: str
    rewritten_query: str
    intent: str
    is_valid: bool
    search_results: List[SearchResult]
    answer: str
    disclaimer: str
    messages: Annotated[List[Dict[str, str]], operator.add]
    session_id: str


@dataclass
class IntentResult:
    """意图识别结果"""
    intent: str
    is_valid: bool
    reason: str


class IntentRecognizer:
    """
    意图识别器
    判断用户提问是否合规，识别提问意图
    """
    
    ILLEGAL_KEYWORDS = [
        "如何犯罪", "逃避法律", "规避法律", "违法", "犯罪方法",
        "如何偷税", "如何逃税", "如何洗钱", "如何诈骗"
    ]
    
    LEGAL_INTENTS = [
        "法律咨询", "法条查询", "案例分析", "法律解释", 
        "诉讼指导", "合同审查", "法律建议"
    ]
    
    def __init__(self, llm: ChatOpenAI):
        """
        初始化意图识别器
        
        Args:
            llm: 大语言模型实例
        """
        self.llm = llm
    
    def recognize(self, query: str) -> IntentResult:
        """
        识别用户意图
        
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
        
        system_prompt = """你是一个法律咨询意图识别助手。请分析用户的问题，判断其意图是否合法合规。
        
合法的法律咨询包括：
- 法律条文查询和解释
- 案例分析和参考
- 法律程序咨询
- 合同法律问题
- 权益保护咨询

不合规的请求包括：
- 询问如何违法或犯罪
- 询问如何逃避法律制裁
- 询问非法操作方法
- 其他违反法律道德的问题

请以JSON格式返回结果：
{"intent": "意图类型", "is_valid": true/false, "reason": "判断理由"}"""
        
        try:
            response = self.llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=query)
            ])
            
            import json
            result = json.loads(response.content)
            
            return IntentResult(
                intent=result.get("intent", "法律咨询"),
                is_valid=result.get("is_valid", True),
                reason=result.get("reason", "")
            )
            
        except Exception as e:
            logger.error(f"意图识别失败: {str(e)}")
            return IntentResult(
                intent="法律咨询",
                is_valid=True,
                reason="默认通过"
            )


class QueryRewriter:
    """
    查询改写器
    优化用户提问，提升检索准确率
    """
    
    def __init__(self, llm: ChatOpenAI):
        """
        初始化查询改写器
        
        Args:
            llm: 大语言模型实例
        """
        self.llm = llm
    
    def rewrite(self, query: str, conversation_history: List[Dict[str, str]] = None) -> str:
        """
        改写查询
        
        Args:
            query: 原始查询
            conversation_history: 对话历史
            
        Returns:
            改写后的查询
        """
        system_prompt = """你是一个法律查询优化助手。请根据用户的原始问题和对话历史，优化查询语句，使其更适合在法律知识库中检索。

优化原则：
1. 补充必要的法律术语
2. 明确查询的法律领域
3. 保持查询的核心意图
4. 去除无关的口语化表达

请直接返回优化后的查询语句，不要添加任何解释。"""
        
        messages = [SystemMessage(content=system_prompt)]
        
        if conversation_history:
            for msg in conversation_history[-3:]:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))
        
        messages.append(HumanMessage(content=f"请优化以下查询：{query}"))
        
        try:
            response = self.llm.invoke(messages)
            rewritten = response.content.strip()
            logger.info(f"查询改写: {query} -> {rewritten}")
            return rewritten
        except Exception as e:
            logger.error(f"查询改写失败: {str(e)}")
            return query


class AnswerGenerator:
    """
    回答生成器
    根据检索结果生成法律回答，添加法条跳转标识
    """
    
    DISCLAIMER = """
【免责声明】
本系统提供的法律信息仅供参考，不构成法律意见或建议。具体法律问题请咨询专业律师。
本系统基于公开法律文献和案例，不保证信息的完整性和时效性。
"""
    
    def __init__(self, llm: ChatOpenAI):
        """
        初始化回答生成器
        
        Args:
            llm: 大语言模型实例
        """
        self.llm = llm
    
    def generate(
        self, 
        query: str, 
        search_results: List[SearchResult],
        conversation_history: List[Dict[str, str]] = None
    ) -> str:
        """
        生成回答
        
        Args:
            query: 用户提问
            search_results: 检索结果
            conversation_history: 对话历史
            
        Returns:
            生成的回答
        """
        context = self._build_context(search_results)
        
        system_prompt = """你是一个专业的法律咨询助手。请根据提供的法律条文和案例，回答用户的问题。

要求：
1. 回答要准确、专业、有法律依据
2. 引用具体的法律条文时，标注【法条跳转】标识
3. 引用案例时，简要说明案例要点
4. 如果检索结果与问题不相关，请诚实说明
5. 回答要简洁明了，避免冗长

回答格式：
- 先给出直接回答
- 然后列出相关法律依据
- 最后提供相关案例参考（如有）"""
        
        messages = [SystemMessage(content=system_prompt)]
        
        if conversation_history:
            for msg in conversation_history[-3:]:
                if msg.get("role") == "user":
                    messages.append(HumanMessage(content=msg.get("content", "")))
                elif msg.get("role") == "assistant":
                    messages.append(AIMessage(content=msg.get("content", "")))
        
        user_message = f"""用户问题：{query}

参考法律条文和案例：
{context}

请根据以上信息回答用户问题，并在引用法条时添加【法条跳转】标识。"""
        
        messages.append(HumanMessage(content=user_message))
        
        try:
            response = self.llm.invoke(messages)
            answer = response.content
            
            answer = self._add_jump_links(answer, search_results)
            
            return answer
            
        except Exception as e:
            logger.error(f"回答生成失败: {str(e)}")
            return "抱歉，回答生成过程中出现错误，请稍后重试。"
    
    def _build_context(self, search_results: List[SearchResult]) -> str:
        """
        构建上下文
        
        Args:
            search_results: 检索结果
            
        Returns:
            上下文字符串
        """
        context_parts = []
        
        for i, result in enumerate(search_results, 1):
            if result.doc_type == "law":
                context_parts.append(
                    f"【法条{i}】{result.law_name} - {result.chapter} - 第{result.article_number}条\n"
                    f"内容：{result.content}\n"
                    f"来源文件：{result.file_name}"
                )
            else:
                context_parts.append(
                    f"【案例{i}】{result.case_type}案件 - {result.case_number}\n"
                    f"判决日期：{result.judgment_date}\n"
                    f"内容：{result.content}\n"
                    f"来源文件：{result.file_name}"
                )
        
        return "\n\n".join(context_parts)
    
    def _add_jump_links(self, answer: str, search_results: List[SearchResult]) -> str:
        """
        在回答中添加法条跳转链接
        
        Args:
            answer: 原始回答
            search_results: 检索结果
            
        Returns:
            添加跳转链接后的回答
        """
        for result in search_results:
            if result.doc_type == "law" and result.article_number:
                pattern = f"第{result.article_number}条"
                if pattern in answer and result.file_path:
                    jump_link = f"[第{result.article_number}条](file://{result.file_path})"
                    answer = answer.replace(pattern, jump_link, 1)
        
        return answer
    
    def get_disclaimer(self) -> str:
        """
        获取免责声明
        
        Returns:
            免责声明文本
        """
        return self.DISCLAIMER


class LegalWorkflow:
    """
    法律咨询工作流
    使用LangGraph编排完整的对话流程
    """
    
    def __init__(self, hybrid_retriever: HybridRetriever):
        """
        初始化工作流
        
        Args:
            hybrid_retriever: 混合检索器
        """
        self.hybrid_retriever = hybrid_retriever
        
        self.llm = ChatOpenAI(
            model=settings.LLM_MODEL_NAME,
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_API_BASE,
            temperature=0.7
        )
        
        self.intent_recognizer = IntentRecognizer(self.llm)
        self.query_rewriter = QueryRewriter(self.llm)
        self.answer_generator = AnswerGenerator(self.llm)
        
        self.graph = self._build_graph()
        
        self.conversation_memory: Dict[str, List[Dict[str, str]]] = {}
    
    def _build_graph(self) -> StateGraph:
        """
        构建工作流图
        
        Returns:
            StateGraph实例
        """
        workflow = StateGraph(ConversationState)
        
        workflow.add_node("intent_recognition", self._intent_recognition_node)
        workflow.add_node("query_rewrite", self._query_rewrite_node)
        workflow.add_node("hybrid_search", self._hybrid_search_node)
        workflow.add_node("answer_generation", self._answer_generation_node)
        workflow.add_node("reject_response", self._reject_response_node)
        
        workflow.set_entry_point("intent_recognition")
        
        workflow.add_conditional_edges(
            "intent_recognition",
            self._route_by_intent,
            {
                "valid": "query_rewrite",
                "invalid": "reject_response"
            }
        )
        
        workflow.add_edge("query_rewrite", "hybrid_search")
        workflow.add_edge("hybrid_search", "answer_generation")
        workflow.add_edge("answer_generation", END)
        workflow.add_edge("reject_response", END)
        
        return workflow.compile()
    
    def _intent_recognition_node(self, state: ConversationState) -> Dict[str, Any]:
        """
        意图识别节点
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        query = state["query"]
        result = self.intent_recognizer.recognize(query)
        
        return {
            "intent": result.intent,
            "is_valid": result.is_valid
        }
    
    def _query_rewrite_node(self, state: ConversationState) -> Dict[str, Any]:
        """
        查询改写节点
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        query = state["query"]
        session_id = state.get("session_id", "default")
        history = self.conversation_memory.get(session_id, [])
        
        rewritten = self.query_rewriter.rewrite(query, history)
        
        return {"rewritten_query": rewritten}
    
    def _hybrid_search_node(self, state: ConversationState) -> Dict[str, Any]:
        """
        混合检索节点
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        query = state.get("rewritten_query", state["query"])
        
        results = self.hybrid_retriever.hybrid_search(query)
        
        return {"search_results": results}
    
    def _answer_generation_node(self, state: ConversationState) -> Dict[str, Any]:
        """
        回答生成节点
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        query = state["query"]
        search_results = state["search_results"]
        session_id = state.get("session_id", "default")
        history = self.conversation_memory.get(session_id, [])
        
        answer = self.answer_generator.generate(query, search_results, history)
        disclaimer = self.answer_generator.get_disclaimer()
        
        self._update_memory(session_id, "user", query)
        self._update_memory(session_id, "assistant", answer)
        
        return {
            "answer": answer,
            "disclaimer": disclaimer,
            "messages": [
                {"role": "user", "content": query},
                {"role": "assistant", "content": answer}
            ]
        }
    
    def _reject_response_node(self, state: ConversationState) -> Dict[str, Any]:
        """
        拒答响应节点
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        intent = state.get("intent", "")
        
        reject_message = f"""抱歉，我无法回答这个问题。

检测到您的请求可能涉及不合规内容。本系统仅提供合法的法律咨询服务。

如果您有其他法律问题，欢迎继续咨询。"""
        
        return {
            "answer": reject_message,
            "disclaimer": self.answer_generator.get_disclaimer()
        }
    
    def _route_by_intent(self, state: ConversationState) -> str:
        """
        根据意图路由
        
        Args:
            state: 当前状态
            
        Returns:
            下一个节点名称
        """
        if state.get("is_valid", True):
            return "valid"
        return "invalid"
    
    def _update_memory(self, session_id: str, role: str, content: str):
        """
        更新对话记忆
        
        Args:
            session_id: 会话ID
            role: 角色（user/assistant）
            content: 内容
        """
        if session_id not in self.conversation_memory:
            self.conversation_memory[session_id] = []
        
        self.conversation_memory[session_id].append({
            "role": role,
            "content": content
        })
        
        if len(self.conversation_memory[session_id]) > 20:
            self.conversation_memory[session_id] = self.conversation_memory[session_id][-20:]
    
    def run(self, query: str, session_id: str = "default") -> Dict[str, Any]:
        """
        运行工作流
        
        Args:
            query: 用户提问
            session_id: 会话ID
            
        Returns:
            工作流执行结果
        """
        initial_state: ConversationState = {
            "query": query,
            "rewritten_query": "",
            "intent": "",
            "is_valid": True,
            "search_results": [],
            "answer": "",
            "disclaimer": "",
            "messages": [],
            "session_id": session_id
        }
        
        try:
            result = self.graph.invoke(initial_state)
            
            return {
                "success": True,
                "answer": result.get("answer", ""),
                "disclaimer": result.get("disclaimer", ""),
                "search_results": [
                    {
                        "content": r.content,
                        "score": r.score,
                        "law_name": r.law_name,
                        "chapter": r.chapter,
                        "article_number": r.article_number,
                        "file_path": r.file_path,
                        "file_name": r.file_name,
                        "doc_type": r.doc_type
                    }
                    for r in result.get("search_results", [])
                ]
            }
            
        except Exception as e:
            logger.error(f"工作流执行失败: {str(e)}")
            return {
                "success": False,
                "answer": "抱歉，系统处理过程中出现错误，请稍后重试。",
                "disclaimer": self.answer_generator.get_disclaimer(),
                "search_results": []
            }
    
    def clear_memory(self, session_id: str = "default"):
        """
        清除对话记忆
        
        Args:
            session_id: 会话ID
        """
        if session_id in self.conversation_memory:
            del self.conversation_memory[session_id]


if __name__ == "__main__":
    from modules.rag_retriever import MilvusManager, EmbeddingGenerator
    
    milvus_manager = MilvusManager()
    milvus_manager.connect()
    
    embedding_generator = EmbeddingGenerator()
    hybrid_retriever = HybridRetriever(milvus_manager, embedding_generator)
    
    workflow = LegalWorkflow(hybrid_retriever)
    
    result = workflow.run("什么是正当防卫？")
    print("回答:", result["answer"])
    print("\n免责声明:", result["disclaimer"])
