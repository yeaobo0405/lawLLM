import os
from modules.document_processor import DocumentProcessor

f = r"d:\develop1\law03\knowledge_base\laws\内蒙古自治区宗教事务条例_2019-11-28_2020-01-01_地方性法规_内蒙古自治区人民代表大会常务委员会_有效.docx"
processor = DocumentProcessor()
docs = processor.load_document(f)
if docs:
    for doc in docs:
        print(f"Content length: {len(doc.page_content)}")
        print(f"First 500 chars: {doc.page_content[:500]}")
else:
    print("Failed to load")
