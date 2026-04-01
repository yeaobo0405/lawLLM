import logging
from typing import List, Dict, Any, Optional
from .base_agent import BaseAgent

try:
    from ..modules.rag_retriever import HybridRetriever, MilvusManager, EmbeddingGenerator
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from modules.rag_retriever import HybridRetriever, MilvusManager, EmbeddingGenerator

logger = logging.getLogger(__name__)

class ResearcherAgent(BaseAgent):
    """
    法规研究员 Agent
    负责执行海量法律数据检索并结构化返回。
    """
    def __init__(self):
        super().__init__(
            name="Researcher",
            role="法规研究员",
            instruction="你负责根据用户需求，在法律数据库中检索最相关的法条。你需要精准提取核心关键词，并对检索结果进行初步筛选。"
        )
        # 初始化检索器
        self.milvus_manager = MilvusManager()
        self.embedding_generator = EmbeddingGenerator()
        if self.milvus_manager.connect():
             self.retriever = HybridRetriever(self.milvus_manager, self.embedding_generator)
             # 这里假设索引已经构建
             # self.retriever.build_bm25_index()
        else:
            logger.error("ResearcherAgent 无法连接 Milvus")
            self.retriever = None

    def retrieve(self, query: str, top_k: int = 5) -> str:
        """
        根据 query 检索法条，并返回格式化字符串
        """
        if not self.retriever:
            return "检索服务暂不可用。"
        
        # 实际调用检索逻辑
        try:
             results = self.retriever.search(query)
             return results
        except Exception as e:
             logger.error(f"检索失败: {e}")
             return f"检索发生错误: {str(e)}"

    def run(self, user_query: str) -> str:
        """
        Agent 主流程：生成检索 query 并执行
        """
        # 1. 提取关键词
        search_query = self.call_llm(
            f"以下是用户需求：{user_query}。\n请为我提取法律检索关键词，直接输出关键词，不要包含其他文字。",
            temperature=0.1
        )
        
        # 2. 执行检索
        retrieval_raw = self.retrieve(search_query)
        
        return f"### [Researcher 检索结果]\n\n{retrieval_raw}"
