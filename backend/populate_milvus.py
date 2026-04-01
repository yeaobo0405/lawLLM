import json
import logging
import os
from tqdm import tqdm

try:
    from backend.modules.rag_retriever import MilvusManager, EmbeddingGenerator
    from backend.config import settings
except ImportError:
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from modules.rag_retriever import MilvusManager, EmbeddingGenerator
    from config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def populate():
    # 数据文件列表
    data_sources = [
        {"path": r"d:\develop1\law03\backend\data\laws_processed.jsonl", "type": "law"},
        {"path": r"d:\develop1\law03\backend\data\cases_processed.jsonl", "type": "case"}
    ]

    milvus_manager = MilvusManager()
    embedding_generator = EmbeddingGenerator()
    
    # 强制启用 GPU
    embedding_generator.force_gpu()
    
    if not milvus_manager.connect():
        return

    # 重新创建集合以实现清空旧数据（强制重新构建架构）
    milvus_manager.create_collection(force=True)

    for source in data_sources:
        jsonl_path = source["path"]
        doc_type = source["type"]
        
        if not os.path.exists(jsonl_path):
            logger.warning(f"找不到 JSONL 文件: {jsonl_path}，跳过...")
            continue

        documents = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                documents.append(json.loads(line))

        logger.info(f"正在向量化并导入 {doc_type} 数据 ({len(documents)} 条)...")
        
        batch_size = 50
        for i in tqdm(range(0, len(documents), batch_size)):
            batch = documents[i:i+batch_size]
            texts = [doc["content"] for doc in batch]
            embeddings = embedding_generator.generate_embeddings(texts)
            
            formatted_batch = []
            for doc in batch:
                if doc_type == "law":
                    formatted_batch.append({
                        "content": doc["content"],
                        "law_name": doc["law_name"],
                        "chapter": doc.get("chapter", "正文"),
                        "article_number": doc["article_number"],
                        "doc_type": "law",
                        "file_name": doc["file_name"],
                        "file_path": os.path.join(r"d:\develop1\law03\knowledge_base\laws", doc["file_name"])
                    })
                else:
                    # 案例 meta 处理
                    formatted_batch.append({
                        "content": doc["content"],
                        "law_name": doc.get("case_number", "未知案号"),  # 案例复用 law_name 字段或单独映射
                        "chapter": "案例正文",
                        "article_number": "0",
                        "doc_type": "case",
                        "file_name": doc["file_name"],
                        "file_path": os.path.join(r"d:\develop1\law03\knowledge_base\cases", doc["file_name"])
                    })
                
            milvus_manager.insert_documents(formatted_batch, embeddings)

    logger.info("所有数据导入完成！")

if __name__ == "__main__":
    populate()
