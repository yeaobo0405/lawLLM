"""
RAG检索模块
使用Milvus向量数据库、混合查询（向量+BM25）、rerank重排实现
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import jieba
import numpy as np

from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility
)
from rank_bm25 import BM25Okapi

try:
    from ..config import settings
except ImportError:
    from config import settings

try:
    from .document_processor import EmbeddingGenerator
except ImportError:
    from modules.document_processor import EmbeddingGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """检索结果数据结构"""
    content: str
    score: float
    law_name: str
    chapter: str
    article_number: str
    case_number: str
    judgment_date: str
    case_type: str
    file_path: str
    file_name: str
    doc_type: str


class MilvusManager:
    """
    Milvus向量数据库管理器
    负责连接管理、集合创建、数据插入、向量检索
    """
    
    def __init__(self):
        """
        初始化Milvus管理器
        """
        self.host = settings.MILVUS_HOST
        self.port = settings.MILVUS_PORT
        self.collection_name = settings.COLLECTION_NAME
        self.dimension = settings.VECTOR_DIMENSION
        self.collection: Optional[Collection] = None
        
    def connect(self) -> bool:
        """
        连接Milvus数据库
        
        Returns:
            连接是否成功
        """
        try:
            connections.connect(
                alias="default",
                host=self.host,
                port=self.port
            )
            logger.info(f"成功连接Milvus: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"连接Milvus失败: {str(e)}")
            return False
    
    def disconnect(self):
        """
        断开Milvus连接
        """
        try:
            connections.disconnect("default")
            logger.info("已断开Milvus连接")
        except Exception as e:
            logger.error(f"断开Milvus连接失败: {str(e)}")
    
    def create_collection(self, force: bool = False) -> bool:
        """
        创建向量集合
        
        Args:
            force: 是否强制删除并重新创建（清空数据）
            
        Returns:
            创建是否成功
        """
        try:
            if utility.has_collection(self.collection_name):
                if force:
                    logger.info(f"正在删除旧集合: {self.collection_name}")
                    utility.drop_collection(self.collection_name)
                else:
                    logger.info(f"集合 {self.collection_name} 已存在")
                    self.collection = Collection(self.collection_name)
                    return True
            
            fields = [
                FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
                FieldSchema(name="law_name", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="chapter", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="article_number", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="case_number", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="judgment_date", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="case_type", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="file_path", dtype=DataType.VARCHAR, max_length=1024),
                FieldSchema(name="file_name", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(name="doc_type", dtype=DataType.VARCHAR, max_length=32)
            ]
            
            schema = CollectionSchema(fields=fields, description="法律知识库向量集合")
            self.collection = Collection(name=self.collection_name, schema=schema)
            
            index_params = {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {"M": 16, "efConstruction": 40}
            }
            self.collection.create_index(field_name="embedding", index_params=index_params)
            
            logger.info(f"成功创建集合: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"创建集合失败: {str(e)}")
            return False
    
    def insert_documents(self, documents: List[Dict[str, Any]], embeddings: List[List[float]]) -> bool:
        """
        批量插入文档
        
        Args:
            documents: 文档列表，包含content和metadata
            embeddings: 嵌入向量列表
            
        Returns:
            插入是否成功
        """
        try:
            if self.collection is None:
                self.collection = Collection(self.collection_name)
            
            data = [
                [doc.get("content", "") for doc in documents],
                embeddings,
                [doc.get("law_name", "") for doc in documents],
                [doc.get("chapter", "") for doc in documents],
                [doc.get("article_number", "") for doc in documents],
                [doc.get("case_number", "") for doc in documents],
                [doc.get("judgment_date", "") for doc in documents],
                [doc.get("case_type", "") for doc in documents],
                [doc.get("file_path", "") for doc in documents],
                [doc.get("file_name", "") for doc in documents],
                [doc.get("doc_type", "law") for doc in documents]
            ]
            
            self.collection.insert(data)
            self.collection.flush()
            
            logger.info(f"成功插入 {len(documents)} 条文档")
            return True
            
        except Exception as e:
            logger.error(f"插入文档失败: {str(e)}")
            return False
    
    def vector_search(self, query_embedding: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        向量检索
        
        Args:
            query_embedding: 查询向量
            top_k: 返回结果数量
            
        Returns:
            检索结果列表
        """
        try:
            if self.collection is None:
                self.collection = Collection(self.collection_name)
            
            self.collection.load()
            
            search_params = {"metric_type": "COSINE", "params": {"nprobe": 16}}
            
            results = self.collection.search(
                data=[query_embedding],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["content", "law_name", "chapter", "article_number",
                              "case_number", "judgment_date", "case_type",
                              "file_path", "file_name", "doc_type"]
            )
            
            search_results = []
            for hits in results:
                for hit in hits:
                    result = {
                        "content": hit.entity.get("content"),
                        "score": hit.score,
                        "law_name": hit.entity.get("law_name"),
                        "chapter": hit.entity.get("chapter"),
                        "article_number": hit.entity.get("article_number"),
                        "case_number": hit.entity.get("case_number"),
                        "judgment_date": hit.entity.get("judgment_date"),
                        "case_type": hit.entity.get("case_type"),
                        "file_path": hit.entity.get("file_path"),
                        "file_name": hit.entity.get("file_name"),
                        "doc_type": hit.entity.get("doc_type")
                    }
                    search_results.append(result)
            
            return search_results
            
        except Exception as e:
            logger.error(f"向量检索失败: {str(e)}")
            return []
    
    def filter_by_metadata(
        self,
        doc_type: Optional[str] = None,
        law_name: Optional[str] = None,
        case_type: Optional[str] = None,
        article_number: Optional[str] = None,
        case_number: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        按元数据筛选文档
        
        Args:
            doc_type: 文档类型 (law/case)
            law_name: 法律名称
            case_type: 案件类型
            article_number: 法条编号
            case_number: 案号
            
        Returns:
            筛选结果列表
        """
        try:
            if self.collection is None:
                self.collection = Collection(self.collection_name)
            
            self.collection.load()
            
            filter_expr = ""
            conditions = []
            
            if doc_type:
                conditions.append(f'doc_type == "{doc_type}"')
            if law_name:
                conditions.append(f'law_name like "%{law_name}%"')
            if case_type:
                conditions.append(f'case_type == "{case_type}"')
            if article_number:
                conditions.append(f'article_number == "{article_number}"')
            if case_number:
                conditions.append(f'case_number like "%{case_number}%"')
            
            if conditions:
                filter_expr = " and ".join(conditions)
                results = self.collection.query(
                    expr=filter_expr,
                    output_fields=["content", "law_name", "chapter", "article_number",
                                  "case_number", "judgment_date", "case_type",
                                  "file_path", "file_name", "doc_type"]
                )
            else:
                results = self.collection.query(
                    expr="id >= 0",
                    output_fields=["content", "law_name", "chapter", "article_number",
                                  "case_number", "judgment_date", "case_type",
                                  "file_path", "file_name", "doc_type"]
                )
            
            return results
            
        except Exception as e:
            logger.error(f"元数据筛选失败: {str(e)}")
            return []
    
    def get_all_files(self) -> List[Dict[str, Any]]:
        """
        获取所有文件列表
        
        Returns:
            文件列表
        """
        try:
            if self.collection is None:
                self.collection = Collection(self.collection_name)
            
            self.collection.load()
            
            results = self.collection.query(
                expr="id >= 0",
                output_fields=["law_name", "case_type", "article_number",
                              "case_number", "file_path", "file_name", "doc_type"]
            )
            
            file_map = {}
            for item in results:
                file_path = item.get("file_path", "")
                if file_path and file_path not in file_map:
                    file_map[file_path] = {
                        "file_path": file_path,
                        "file_name": item.get("file_name", ""),
                        "law_name": item.get("law_name", ""),
                        "case_type": item.get("case_type", ""),
                        "article_number": item.get("article_number", ""),
                        "case_number": item.get("case_number", ""),
                        "doc_type": item.get("doc_type", "")
                    }
            
            return list(file_map.values())
            
        except Exception as e:
            logger.error(f"获取文件列表失败: {str(e)}")
            return []


class BM25Retriever:
    """
    BM25关键词检索器
    """
    
    def __init__(self):
        """
        初始化BM25检索器
        """
        self.bm25 = None
        self.documents = []
        self.tokenized_corpus = []
        self.is_initialized = False

    def initialize(self):
        """
        延迟初始化：加载法律词典并预热 jieba
        """
        if self.is_initialized:
            return
            
        if os.path.exists(settings.LEGAL_DICT_PATH):
            logger.info(f"正在后台异步加载法律词典: {settings.LEGAL_DICT_PATH}")
            jieba.load_userdict(settings.LEGAL_DICT_PATH)
            # 显式初始化 jieba 引擎，防止第一个搜索请求阻塞
            jieba.initialize()
            
        self.is_initialized = True
        
    def build_index(self, documents: List[Dict[str, Any]]):
        """
        构建BM25索引
        
        Args:
            documents: 文档列表
        """
        # 确保 jieba 已初始化
        self.initialize()
        
        self.documents = documents
        self.tokenized_corpus = []
        
        for doc in documents:
            content = doc.get("content", "")
            tokens = list(jieba.cut(content))
            self.tokenized_corpus.append(tokens)
        
        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            logger.info(f"BM25索引构建完成，共 {len(self.documents)} 条文档")
    
    def search(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """
        BM25检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            检索结果列表
        """
        if self.bm25 is None:
            logger.warning("BM25索引未构建")
            return []
        
        # 确保已初始化（词典加载）
        self.initialize()
        
        try:
            query_tokens = list(jieba.cut(query))
            scores = self.bm25.get_scores(query_tokens)
            
            top_indices = np.argsort(scores)[::-1][:top_k]
            
            results = []
            for idx in top_indices:
                result = self.documents[idx].copy()
                result["score"] = float(scores[idx])
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"BM25检索失败: {str(e)}")
            return []
            
    def save_to_cache(self, file_path: str):
        """
        保存BM25索引到缓存文件
        
        Args:
            file_path: 缓存文件路径
        """
        try:
            import pickle
            # 确保目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'wb') as f:
                pickle.dump({
                    'documents': self.documents,
                    'tokenized_corpus': self.tokenized_corpus,
                    'bm25': self.bm25
                }, f)
            logger.info(f"BM25索引已缓存至: {file_path}")
        except Exception as e:
            logger.error(f"保存BM25缓存失败: {str(e)}")

    def load_from_cache(self, file_path: str) -> bool:
        """
        从缓存文件加载BM25索引
        
        Args:
            file_path: 缓存文件路径
            
        Returns:
            是否加载成功
        """
        if not os.path.exists(file_path):
            return False
            
        try:
            import pickle
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
                self.documents = data.get('documents', [])
                self.tokenized_corpus = data.get('tokenized_corpus', [])
                self.bm25 = data.get('bm25')
            
            if self.bm25 and self.documents:
                logger.info(f"成功从缓存加载BM25索引，共 {len(self.documents)} 条文档")
                return True
            return False
        except Exception as e:
            logger.error(f"从缓存加载BM25失败: {str(e)}")
            return False


class Reranker:
    """
    重排器
    使用bge-reranker-base模型对检索结果进行重排
    """
    
    def __init__(self, model_path: str = None):
        """
        初始化重排器
        
        Args:
            model_path: 模型路径
        """
        self.model_path = model_path or settings.RERANK_MODEL_PATH
        self.reranker = None
        self.is_ready = False
        
    def load_model(self):
        """
        加载重排模型
        """
        try:
            from sentence_transformers import CrossEncoder
            
            logger.info(f"正在加载重排模型: {self.model_path}")
            self.reranker = CrossEncoder(self.model_path, max_length=512)
            self.is_ready = True
            logger.info("重排模型加载完成")
            
        except Exception as e:
            logger.error(f"加载重排模型失败: {str(e)}")
            raise
    
    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        对检索结果进行重排
        
        Args:
            query: 查询文本
            documents: 检索结果列表
            top_k: 返回结果数量
            
        Returns:
            重排后的结果列表
        """
        if self.reranker is None:
            self.load_model()
        
        if not documents:
            return []
        
        try:
            pairs = [[query, doc.get("content", "")] for doc in documents]
            scores = self.reranker.predict(pairs)
            
            scored_docs = list(zip(documents, scores))
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for doc, score in scored_docs[:top_k]:
                result = doc.copy()
                result["rerank_score"] = float(score)
                results.append(result)
            
            return results
            
        except Exception as e:
            logger.error(f"重排失败: {str(e)}")
            return documents[:top_k]


class HybridRetriever:
    """
    混合检索器
    融合向量检索和BM25检索结果
    """
    
    def __init__(self, milvus_manager: MilvusManager, embedding_generator: EmbeddingGenerator):
        """
        初始化混合检索器
        
        Args:
            milvus_manager: Milvus管理器
            embedding_generator: 嵌入向量生成器
        """
        self.milvus_manager = milvus_manager
        self.embedding_generator = embedding_generator
        self.bm25_retriever = BM25Retriever()
        self.reranker = Reranker()
        self.is_bm25_built = False
        self.is_ready = False
        
    def build_bm25_index(self):
        """
        构建或加载BM25索引
        """
        try:
            # 1. 优先尝试从缓存加载
            if hasattr(settings, 'BM25_CACHE_PATH') and self.bm25_retriever.load_from_cache(settings.BM25_CACHE_PATH):
                self.is_bm25_built = True
                self.is_ready = True  # ✅ 修复：缓存加载成功后同样需要设置就绪状态
                logger.info(">>> 系统已从 BM25 缓存加载完毕，进入就绪状态 <<<")
                return

            # 2. 缓存不可用，执行构建流程
            logger.info("正在从数据库构建BM25索引...")
            all_docs = self.milvus_manager.filter_by_metadata()
            if all_docs:
                self.bm25_retriever.build_index(all_docs)
                self.is_bm25_built = True
                
                # 3. 成功后保存到缓存
                if hasattr(settings, 'BM25_CACHE_PATH'):
                    self.bm25_retriever.save_to_cache(settings.BM25_CACHE_PATH)
            else:
                logger.warning("Milvus 中暂无文档，BM25 索引为空，但系统仍将进入就绪状态")
            
            # 无论是否有文档，只要流程完成就标记为就绪
            self.is_ready = True
            logger.info(">>> BM25 索引构建完毕，系统已进入就绪状态 <<<")
                    
        except Exception as e:
            logger.error(f"构建BM25索引失败: {str(e)}")
            # 即使 BM25 构建失败，仍设置 is_ready 以允许系统使用纯向量检索回退
            self.is_ready = True
            logger.warning("BM25 构建失败，系统将以纯向量检索模式运行")
    
    def hybrid_search(self, query: str, top_k: int = 5) -> List[SearchResult]:
        """
        执行混合检索
        
        Args:
            query: 查询文本
            top_k: 返回结果数量
            
        Returns:
            检索结果列表
        """
        try:
            query_embedding = self.embedding_generator.generate_single_embedding(query)
            
            vector_results = self.milvus_manager.vector_search(
                query_embedding, 
                top_k=settings.TOP_K_VECTOR
            )
            
            bm25_results = []
            if self.is_bm25_built:
                bm25_results = self.bm25_retriever.search(query, top_k=settings.TOP_K_BM25)
            
            combined_results = self._merge_results(vector_results, bm25_results)
            
            reranked_results = self.reranker.rerank(query, combined_results, top_k=60) # 先拿多一点重排
            
            search_results = []
            for result in reranked_results:
                # 给重排分数再次引入层级权重（以确认为最终排序的主要依据）
                h_weight = self._get_hierarchy_weight(result.get("law_name", ""), result.get("doc_type", "law"))
                # 统一转为 SearchResult
                search_results.append(SearchResult(
                    content=result.get("content", ""),
                    score=float(result.get("rerank_score", 0)) * h_weight,
                    law_name=result.get("law_name", ""),
                    chapter=result.get("chapter", ""),
                    article_number=result.get("article_number", ""),
                    case_number=result.get("case_number", ""),
                    judgment_date=result.get("judgment_date", ""),
                    case_type=result.get("case_type", ""),
                    file_path=result.get("file_path", ""),
                    file_name=result.get("file_name", ""),
                    doc_type=result.get("doc_type", "law")
                ))
            
            # 按加权后的重排分数进行最终排序并取 top_k
            search_results.sort(key=lambda x: x.score, reverse=True)
            return search_results[:top_k]
            
        except Exception as e:
            logger.error(f"混合检索失败: {str(e)}")
            return []

    def _get_hierarchy_weight(self, law_name: str, doc_type: str) -> float:
        """
        获取法律层级权重
        宪法 > 法律 > 司法解释 > 行政法规 > 地方性法规
        """
        if not law_name:
            return 1.0
            
        if "宪法" in law_name:
            return 1.5
        
        # doc_type 判断
        if doc_type == "law":
            # 进一步细分
            if "法律" in law_name or "民法典" in law_name or "刑法" in law_name:
                return 1.4
            return 1.3
        elif doc_type == "interpretation" or "解释" in law_name or "规定" in law_name:
            return 1.2
        elif "行政法规" in law_name or "条例" in law_name:
            return 1.1
        elif "地方" in law_name or "省" in law_name or "市" in law_name:
            return 0.9
            
        return 1.0

    def _merge_results(
        self, 
        vector_results: List[Dict[str, Any]], 
        bm25_results: List[Dict[str, Any]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        使用 RRF (Reciprocal Rank Fusion) 算法合并向量检索和 BM25 检索结果
        
        Args:
            vector_results: 向量检索结果
            bm25_results: BM25检索结果
            k: RRF 常数，默认为 60
            
        Returns:
            合并并按 RRF 分数排序后的结果列表
        """
        rrf_scores = {}
        content_map = {}
        
        for rank, result in enumerate(vector_results):
            content = result.get("content", "")
            if content not in rrf_scores:
                rrf_scores[content] = 0
                content_map[content] = result
            rrf_scores[content] += 1.0 / (k + rank + 1)
        
        for rank, result in enumerate(bm25_results):
            content = result.get("content", "")
            if content not in rrf_scores:
                rrf_scores[content] = 0
                content_map[content] = result
            rrf_scores[content] += 1.0 / (k + rank + 1)
        
        final_results = []
        for content, score in rrf_scores.items():
            result = content_map[content].copy()
            
            # 引入层级权重
            h_weight = self._get_hierarchy_weight(result.get("law_name", ""), result.get("doc_type", ""))
            result["combined_score"] = score * h_weight
            final_results.append(result)
        
        return sorted(final_results, key=lambda x: x["combined_score"], reverse=True)


if __name__ == "__main__":
    milvus_manager = MilvusManager()
    if milvus_manager.connect():
        milvus_manager.create_collection()
        
        embedding_generator = EmbeddingGenerator()
        hybrid_retriever = HybridRetriever(milvus_manager, embedding_generator)
        
        results = hybrid_retriever.hybrid_search("什么是正当防卫？")
        for result in results:
            print(f"内容: {result.content[:100]}...")
            print(f"得分: {result.score}")
            print(f"法律名称: {result.law_name}")
            print(f"文件路径: {result.file_path}")
            print("-" * 50)
