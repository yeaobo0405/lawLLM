"""
数据嵌入脚本
将知识库文档处理并嵌入到Milvus向量数据库
"""
import os
import sys
import logging
from tqdm import tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_milvus():
    """
    检查Milvus连接
    """
    from config import settings
    from pymilvus import connections
    
    try:
        connections.connect(
            alias="default",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT
        )
        logger.info(f"Milvus连接成功: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
        return True
    except Exception as e:
        logger.error(f"Milvus连接失败: {str(e)}")
        logger.error("请确保Milvus服务已启动: docker run -d --name milvus -p 19530:19530 milvusdb/milvus:latest")
        return False


def embed_knowledge_base(
    laws_dir: str = "./knowledge_base/laws",
    cases_dir: str = "./knowledge_base/cases",
    batch_size: int = 50
):
    """
    嵌入知识库文档到Milvus
    
    Args:
        laws_dir: 法条文档目录
        cases_dir: 案例文档目录
        batch_size: 批处理大小
    """
    from config import settings
    from modules.document_processor import DocumentProcessor, EmbeddingGenerator
    from modules.rag_retriever import MilvusManager
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    laws_dir = os.path.abspath(os.path.join(script_dir, laws_dir))
    cases_dir = os.path.abspath(os.path.join(script_dir, cases_dir))
    
    logger.info("=" * 60)
    logger.info("开始嵌入知识库文档...")
    logger.info("=" * 60)
    
    failed_files = []
    
    milvus_manager = MilvusManager()
    if not milvus_manager.connect():
        logger.error("无法连接Milvus，退出")
        return False
    
    milvus_manager.create_collection()
    
    from pymilvus import utility
    if utility.has_collection(settings.COLLECTION_NAME):
        logger.info(f"清空已有集合: {settings.COLLECTION_NAME}")
        utility.drop_collection(settings.COLLECTION_NAME)
        milvus_manager.create_collection()
    
    processor = DocumentProcessor()
    logger.info("正在加载嵌入模型...")
    embedding_generator = EmbeddingGenerator()
    embedding_generator.load_model()
    
    total_docs = 0
    total_chunks = 0
    
    supported_extensions = ['.pdf', '.docx', '.doc', '.txt']
    
    for doc_type, directory in [("law", laws_dir), ("case", cases_dir)]:
        if not os.path.exists(directory):
            logger.warning(f"目录不存在: {directory}")
            continue
        
        logger.info(f"\n处理 {doc_type} 类型文档: {directory}")
        
        all_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in supported_extensions:
                    all_files.append(os.path.join(root, file))
        
        if not all_files:
            logger.warning(f"未找到支持的文档文件")
            continue
        
        logger.info(f"找到 {len(all_files)} 个文档文件")
        
        for file_path in tqdm(all_files, desc=f"处理{doc_type}文档"):
            try:
                chunks = processor.process_document(file_path, doc_type)
                
                if not chunks:
                    logger.warning(f"文档未生成块: {file_path}")
                    continue
                
                for i in range(0, len(chunks), batch_size):
                    batch_chunks = chunks[i:i + batch_size]
                    
                    documents = [
                        {
                            "content": chunk.page_content,
                            **chunk.metadata
                        }
                        for chunk in batch_chunks
                    ]
                    
                    texts = [doc["content"] for doc in documents]
                    embeddings = embedding_generator.generate_embeddings(texts)
                    
                    milvus_manager.insert_documents(documents, embeddings)
                    
                    total_chunks += len(batch_chunks)
                
                total_docs += 1
                
            except Exception as e:
                logger.error(f"处理文档失败: {file_path}, 错误: {str(e)}")
                failed_files.append({
                    "file_path": file_path,
                    "error": str(e)
                })
                continue
    
    logger.info("\n" + "=" * 60)
    logger.info("嵌入完成!")
    logger.info(f"处理文档数: {total_docs}")
    logger.info(f"生成向量块数: {total_chunks}")
    logger.info(f"失败文档数: {len(failed_files)}")
    logger.info("=" * 60)
    
    if failed_files:
        log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "failed_files.log")
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write("处理失败的文档列表:\n\n")
            for item in failed_files:
                f.write(f"文件: {item['file_path']}\n")
                f.write(f"错误: {item['error']}\n")
                f.write("-" * 50 + "\n")
        logger.info(f"失败文档已记录到: {log_file}")
    
    milvus_manager.disconnect()
    return True


def build_bm25_index():
    """
    构建BM25索引
    """
    from modules.rag_retriever import MilvusManager, HybridRetriever, EmbeddingGenerator
    
    logger.info("\n正在构建BM25索引...")
    
    milvus_manager = MilvusManager()
    milvus_manager.connect()
    
    embedding_generator = EmbeddingGenerator()
    hybrid_retriever = HybridRetriever(milvus_manager, embedding_generator)
    hybrid_retriever.build_bm25_index()
    
    milvus_manager.disconnect()
    
    logger.info("BM25索引构建完成")


def main():
    """
    主函数
    """
    print("""
╔══════════════════════════════════════════════════════════╗
║          法律智能问答系统 - 数据嵌入工具                  ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    if not check_milvus():
        sys.exit(1)
    
    laws_dir = "../knowledge_base/laws"
    cases_dir = "../knowledge_base/cases"
    batch_size = 32
    
    print(f"配置信息:")
    print(f"  法条目录: {laws_dir}")
    print(f"  案例目录: {cases_dir}")
    print(f"  批处理大小: {batch_size}")
    print()
    
    success = embed_knowledge_base(laws_dir, cases_dir, batch_size)
    
    if success:
        build_bm25_index()
        print("\n✅ 数据嵌入完成！现在可以启动系统了。")
    else:
        print("\n❌ 数据嵌入失败，请检查错误信息")


if __name__ == "__main__":
    main()
