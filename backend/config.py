import os
from dotenv import load_dotenv

load_dotenv()

# 当前配置文件所在的目录（即 backend/ 目录）
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    EMBEDDING_MODEL_PATH: str = os.getenv("EMBEDDING_MODEL_PATH", "D:\\develop1\\Qwen3-Embedding-0.6B")
    RERANK_MODEL_PATH: str = os.getenv("RERANK_MODEL_PATH", "D:\\develop1\\bge-reranker-base")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "legal_knowledge")
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", "1024"))
    
    LLM_MODEL_NAME: str = "qwen3.5-35b-a3b"
    BATCH_SIZE: int = 100
    TOP_K_VECTOR: int = 10
    TOP_K_BM25: int = 10
    TOP_K_RERANK: int = 5
    
    KNOWLEDGE_BASE_PATH: str = os.path.join(_BASE_DIR, "knowledge_base")
    # 使用基于配置文件目录的绝对路径，避免因运行目录不同导致路径解析错误
    DATABASE_PATH: str = os.path.join(_BASE_DIR, "data", "conversation_memory.db")
    LEGAL_DICT_PATH: str = os.path.join(_BASE_DIR, "data", "legal_dict.txt")
    BM25_CACHE_PATH: str = os.path.join(_BASE_DIR, "data", "bm25_index.pkl")

settings = Settings()
