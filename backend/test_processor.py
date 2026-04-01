print("Starting test...")
import os
import sys

# Add current path to sys.path
sys.path.append(os.getcwd())

print("Importing DocumentProcessor...")
try:
    from modules.document_processor import DocumentProcessor
    print("DocumentProcessor imported!")
except Exception as e:
    print(f"Import failed: {e}")
    sys.exit(1)

f = r"d:\develop1\law03\knowledge_base\laws\内蒙古自治区中医药条例_2022-05-26_2022-07-01_地方性法规_内蒙古自治区人民代表大会常务委员会_有效.docx"
processor = DocumentProcessor()
print(f"Loading {os.path.basename(f)}...")
try:
    docs = processor.load_document(f)
    print(f"Success! Chunks: {len(docs)}")
except Exception as e:
    print(f"Failed: {e}")
