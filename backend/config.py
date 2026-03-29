import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv("OPENAI_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    MILVUS_HOST: str = os.getenv("MILVUS_HOST", "localhost")
    MILVUS_PORT: int = int(os.getenv("MILVUS_PORT", "19530"))
    EMBEDDING_MODEL_PATH: str = os.getenv("EMBEDDING_MODEL_PATH", "D:\\develop1\\Qwen3-Embedding-0.6B")
    RERANK_MODEL_PATH: str = os.getenv("RERANK_MODEL_PATH", "BAAI/bge-reranker-base")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "legal_knowledge")
    VECTOR_DIMENSION: int = int(os.getenv("VECTOR_DIMENSION", "1024"))
    
    LLM_MODEL_NAME: str = "qwen3.5-35b-a3b"
    BATCH_SIZE: int = 100
    TOP_K_VECTOR: int = 10
    TOP_K_BM25: int = 10
    TOP_K_RERANK: int = 5

settings = Settings()
