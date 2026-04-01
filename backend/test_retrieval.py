import logging
import os
import sys

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.rag_retriever import MilvusManager, EmbeddingGenerator, HybridRetriever
from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_retrieval():
    milvus_manager = MilvusManager()
    if not milvus_manager.connect():
        logger.error("无法连接到 Milvus")
        return

    embedding_generator = EmbeddingGenerator()
    # 强制 GPU 以确保一致性
    embedding_generator.force_gpu()
    
    hybrid_retriever = HybridRetriever(milvus_manager, embedding_generator)
    
    # 准备测试查询
    queries = [
        "民间借贷纠纷中的保证责任", # 应该能搜到法律和案例
        "什么是正当防卫？",          # 法律
        "交通事故责任认定"           # 案例
    ]
    
    for query in queries:
        print(f"\n{'='*20} 测试查询: {query} {'='*20}")
        # 使用 hybrid_search 获取结构化结果
        results = hybrid_retriever.hybrid_search(query, top_k=3)
        
        if not results:
            print("未找到结果。")
            continue
            
        for i, res in enumerate(results, 1):
            doc_type_str = "【法律】" if res.doc_type == "law" else "【案例】"
            source_name = res.law_name if res.doc_type == "law" else res.case_number
            print(f"[{i}] {doc_type_str} {source_name}")
            print(f"    内容摘要: {res.content[:150]}...")
            print(f"    得分: {res.score:.4f}")
            print("-" * 30)

if __name__ == "__main__":
    test_retrieval()
