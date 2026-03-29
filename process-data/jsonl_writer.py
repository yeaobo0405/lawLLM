"""
JSONL输出模块
将预处理后的文档保存为JSONL格式
"""
import json
import os
import logging
from typing import List, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class JSONLWriter:
    """JSONL格式写入器"""
    
    def __init__(self, output_dir: str = "./processed_data"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def write_document(self, doc: Any, output_file: str = None) -> str:
        """写入单个文档"""
        if output_file is None:
            output_file = os.path.join(self.output_dir, "processed_docs.jsonl")
        
        record = self._doc_to_record(doc)
        
        with open(output_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        return output_file
    
    def write_documents(self, docs: List[Any], output_file: str = None, split_by_type: bool = True) -> List[str]:
        """批量写入文档"""
        output_files = []
        
        if split_by_type:
            law_docs = [d for d in docs if d.doc_type == 'law']
            case_docs = [d for d in docs if d.doc_type == 'case']
            
            if law_docs:
                law_file = os.path.join(self.output_dir, "laws.jsonl")
                self._write_batch(law_docs, law_file)
                output_files.append(law_file)
                logger.info(f"写入法律文档: {len(law_docs)} 条 -> {law_file}")
            
            if case_docs:
                case_file = os.path.join(self.output_dir, "cases.jsonl")
                self._write_batch(case_docs, case_file)
                output_files.append(case_file)
                logger.info(f"写入案例文档: {len(case_docs)} 条 -> {case_file}")
        else:
            if output_file is None:
                output_file = os.path.join(self.output_dir, "all_docs.jsonl")
            self._write_batch(docs, output_file)
            output_files.append(output_file)
        
        return output_files
    
    def _write_batch(self, docs: List[Any], output_file: str):
        """批量写入"""
        with open(output_file, 'w', encoding='utf-8') as f:
            for doc in docs:
                record = self._doc_to_record(doc)
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
    
    def _doc_to_record(self, doc: Any) -> Dict:
        """将文档转换为JSON记录"""
        if hasattr(doc, '__dataclass_fields__'):
            record = {
                'file_name': doc.file_name,
                'file_path': doc.file_path,
                'doc_type': doc.doc_type,
                'law_name': doc.law_name,
                'chapter': doc.chapter,
                'article_number': doc.article_number,
                'case_number': doc.case_number,
                'judgment_date': doc.judgment_date,
                'case_type': doc.case_type,
                'content': doc.content,
                'articles': doc.articles if doc.articles else [],
                'processed_at': datetime.now().isoformat()
            }
        else:
            record = dict(doc) if isinstance(doc, dict) else {}
        
        return record
    
    def write_article_chunks(self, docs: List[Any], output_file: str = None) -> str:
        """写入法条级别的数据块"""
        if output_file is None:
            output_file = os.path.join(self.output_dir, "article_chunks.jsonl")
        
        chunks = []
        for doc in docs:
            if doc.articles:
                for article in doc.articles:
                    chunk = {
                        'file_name': doc.file_name,
                        'file_path': doc.file_path,
                        'doc_type': doc.doc_type,
                        'law_name': doc.law_name,
                        'chapter': doc.chapter,
                        'article_number': article.get('article_number', ''),
                        'content': article.get('content', ''),
                        'processed_at': datetime.now().isoformat()
                    }
                    chunks.append(chunk)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
        
        logger.info(f"写入法条数据块: {len(chunks)} 条 -> {output_file}")
        return output_file


class JSONLReader:
    """JSONL格式读取器"""
    
    def __init__(self):
        pass
    
    def read_all(self, file_path: str) -> List[Dict]:
        """读取所有记录"""
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records
    
    def read_by_type(self, file_path: str, doc_type: str) -> List[Dict]:
        """按类型读取记录"""
        records = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    if record.get('doc_type') == doc_type:
                        records.append(record)
        return records
    
    def count_records(self, file_path: str) -> int:
        """统计记录数"""
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    count += 1
        return count
