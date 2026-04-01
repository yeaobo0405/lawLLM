"""
快速验证：确认 config 路径修复 + is_ready bug 修复是否生效
"""
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')

print("=" * 60)
print("步骤 1: 验证 config 路径")
print("=" * 60)
from config import settings
print(f"BM25_CACHE_PATH = {settings.BM25_CACHE_PATH}")
print(f"  └─ 存在: {os.path.exists(settings.BM25_CACHE_PATH)}")
print(f"LEGAL_DICT_PATH = {settings.LEGAL_DICT_PATH}")
print(f"  └─ 存在: {os.path.exists(settings.LEGAL_DICT_PATH)}")
print(f"DATABASE_PATH   = {settings.DATABASE_PATH}")
print(f"  └─ 存在: {os.path.exists(settings.DATABASE_PATH)}")

print()
print("=" * 60)
print("步骤 2: 验证 BM25 缓存加载后 is_ready 能否设置为 True")
print("=" * 60)

from modules.rag_retriever import BM25Retriever, HybridRetriever, MilvusManager
from modules.document_processor import EmbeddingGenerator

# 创建一个 mock 测试
bm25 = BM25Retriever()
loaded = bm25.load_from_cache(settings.BM25_CACHE_PATH)
print(f"BM25 从缓存加载: {'成功' if loaded else '失败'}")
if loaded:
    print(f"  └─ 文档数量: {len(bm25.documents)}")

# 模拟 HybridRetriever 的行为（不真正连 Milvus）
class MockMilvusManager:
    def filter_by_metadata(self): return []

class MockEmbeddingGenerator:
    pass

mm = MockMilvusManager()
eg = MockEmbeddingGenerator()

# 手动构造 HybridRetriever 实例（不连接 Milvus）
hr = HybridRetriever.__new__(HybridRetriever)
hr.milvus_manager = mm
hr.embedding_generator = eg
hr.bm25_retriever = BM25Retriever()
hr.reranker = None
hr.is_bm25_built = False
hr.is_ready = False

hr.build_bm25_index()

print(f"\nis_bm25_built = {hr.is_bm25_built}")
print(f"is_ready      = {hr.is_ready}")

if hr.is_ready:
    print("\n✅ 修复验证成功！系统初始化后 is_ready 将正确设置为 True")
else:
    print("\n❌ 修复验证失败，is_ready 仍为 False，请检查")
