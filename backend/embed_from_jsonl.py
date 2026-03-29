"""
从JSONL文件嵌入数据到Milvus
支持溯源到原始Word/PDF文件
"""
import os
import sys
import json
import logging
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from modules.rag_retriever import MilvusManager
from modules.document_processor import EmbeddingGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def embed_multiple_jsonl(
    jsonl_paths: list,
    batch_size: int = 32
):
    """
    从多个JSONL文件嵌入数据
    
    Args:
        jsonl_paths: JSONL文件路径列表
        batch_size: 批处理大小
    """
    milvus_manager = MilvusManager()
    if not milvus_manager.connect():
        logger.error("无法连接Milvus")
        return False
    
    from pymilvus import utility
    if utility.has_collection(settings.COLLECTION_NAME):
        logger.info(f"清空已有集合: {settings.COLLECTION_NAME}")
        utility.drop_collection(settings.COLLECTION_NAME)
    
    milvus_manager.create_collection()
    
    logger.info("正在加载嵌入模型...")
    embedding_generator = EmbeddingGenerator()
    embedding_generator.load_model()
    
    total_chunks = 0
    
    for jsonl_path in jsonl_paths:
        if not os.path.exists(jsonl_path):
            logger.warning(f"JSONL文件不存在: {jsonl_path}")
            continue
        
        logger.info(f"\n处理文件: {jsonl_path}")
        
        records = []
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        
        logger.info(f"读取到 {len(records)} 条记录")
        
        for i in tqdm(range(0, len(records), batch_size), desc="嵌入数据"):
            batch = records[i:i + batch_size]
            
            documents = []
            texts = []
            
            for record in batch:
                doc = {
                    "content": record.get("content", ""),
                    "law_name": record.get("law_name", ""),
                    "chapter": record.get("chapter", ""),
                    "article_number": record.get("article_number", ""),
                    "case_number": record.get("case_number", ""),
                    "judgment_date": record.get("judgment_date", ""),
                    "case_type": record.get("case_type", ""),
                    "file_path": record.get("file_path", ""),
                    "file_name": record.get("file_name", ""),
                    "doc_type": record.get("doc_type", "law")
                }
                documents.append(doc)
                texts.append(doc["content"])
            
            embeddings = embedding_generator.generate_embeddings(texts)
            milvus_manager.insert_documents(documents, embeddings)
            total_chunks += len(batch)
    
    logger.info(f"\n嵌入完成，共 {total_chunks} 条记录")
    
    logger.info("创建HNSW索引...")
    from pymilvus import Collection
    collection = Collection(settings.COLLECTION_NAME)
    
    indexes = collection.indexes
    has_index = any(idx.field_name == "embedding" for idx in indexes)
    
    if not has_index:
        index_params = {
            "metric_type": "COSINE",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 256}
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        logger.info("索引创建完成")
    else:
        logger.info("索引已存在，跳过创建")
    
    milvus_manager.disconnect()
    return True


def embed_from_jsonl(
    jsonl_path: str,
    batch_size: int = 32
):
    """
    从单个JSONL文件嵌入数据
    
    Args:
        jsonl_path: JSONL文件路径
        batch_size: 批处理大小
    """
    return embed_multiple_jsonl([jsonl_path], batch_size)


def main():
    """
    主函数
    """
    print("""
╔══════════════════════════════════════════════════════════╗
║          从预处理数据嵌入到Milvus                        ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    laws_path = "../process-data/processed_data/article_chunks.jsonl"
    cases_path = "../process-data/processed_data/cases.jsonl"
    
    print(f"配置信息:")
    print(f"  法条数据: {laws_path}")
    print(f"  案例数据: {cases_path}")
    print()
    
    jsonl_paths = []
    
    if os.path.exists(laws_path):
        jsonl_paths.append(laws_path)
    else:
        logger.warning(f"法条数据文件不存在: {laws_path}")
    
    if os.path.exists(cases_path):
        jsonl_paths.append(cases_path)
    else:
        logger.warning(f"案例数据文件不存在: {cases_path}")
    
    if not jsonl_paths:
        logger.error("没有找到任何数据文件")
        return
    
    success = embed_multiple_jsonl(jsonl_paths)
    
    if success:
        print("\n✅ 嵌入完成！所有数据可溯源到原始文件")
    else:
        print("\n❌ 嵌入失败")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='从JSONL嵌入数据')
    parser.add_argument('--jsonl', help='单个JSONL文件路径（可选，不指定则导入所有）')
    parser.add_argument('--batch-size', type=int, default=32, help='批处理大小')
    
    args = parser.parse_args()
    
    if args.jsonl:
        embed_from_jsonl(args.jsonl, args.batch_size)
    else:
        main()
