"""
数据预处理主脚本
处理法律领域的Word和PDF数据，输出为JSONL格式
"""
import os
import sys
import logging
import argparse
from tqdm import tqdm
from typing import List

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from word_processor import WordProcessor, ProcessedDocument
from pdf_processor import PDFProcessor
from text_cleaner import LegalTextProcessor
from jsonl_writer import JSONLWriter


class DataPreprocessor:
    """数据预处理器"""
    
    def __init__(
        self,
        laws_dir: str = "../knowledge_base/laws",
        cases_dir: str = "../knowledge_base/cases",
        output_dir: str = "./processed_data",
        use_ocr: bool = False,
        desensitize: bool = True
    ):
        self.laws_dir = os.path.abspath(laws_dir)
        self.cases_dir = os.path.abspath(cases_dir)
        self.output_dir = output_dir
        
        self.word_processor = WordProcessor()
        self.pdf_processor = PDFProcessor(use_ocr=use_ocr)
        self.legal_processor = LegalTextProcessor()
        self.jsonl_writer = JSONLWriter(output_dir)
        
        self.desensitize = desensitize
        
        os.makedirs(output_dir, exist_ok=True)
    
    def process_all(self) -> dict:
        """处理所有文档"""
        stats = {
            'laws': {'total': 0, 'success': 0, 'failed': 0, 'articles': 0},
            'cases': {'total': 0, 'success': 0, 'failed': 0}
        }
        
        all_docs = []
        
        logger.info("=" * 60)
        logger.info("开始处理法律文档...")
        logger.info("=" * 60)
        
        law_docs = self._process_directory(self.laws_dir, 'law')
        stats['laws']['total'] = len(law_docs)
        stats['laws']['success'] = len([d for d in law_docs if d.content])
        stats['laws']['failed'] = len([d for d in law_docs if not d.content])
        stats['laws']['articles'] = sum(len(d.articles) for d in law_docs)
        all_docs.extend(law_docs)
        
        logger.info(f"法律文档处理完成: {stats['laws']['success']}/{stats['laws']['total']}")
        logger.info(f"提取法条数: {stats['laws']['articles']}")
        
        logger.info("=" * 60)
        logger.info("开始处理案例文档...")
        logger.info("=" * 60)
        
        case_docs = self._process_directory(self.cases_dir, 'case')
        stats['cases']['total'] = len(case_docs)
        stats['cases']['success'] = len([d for d in case_docs if d.content])
        stats['cases']['failed'] = len([d for d in case_docs if not d.content])
        all_docs.extend(case_docs)
        
        logger.info(f"案例文档处理完成: {stats['cases']['success']}/{stats['cases']['total']}")
        
        logger.info("=" * 60)
        logger.info("清洗文本并脱敏...")
        logger.info("=" * 60)
        
        for doc in tqdm(all_docs, desc="清洗文本"):
            if doc.content:
                doc.content, info = self.legal_processor.process(
                    doc.content,
                    desensitize=self.desensitize
                )
                
                for article in doc.articles:
                    if article.get('content'):
                        article['content'], _ = self.legal_processor.process(
                            article['content'],
                            desensitize=self.desensitize
                        )
        
        logger.info("=" * 60)
        logger.info("保存为JSONL格式...")
        logger.info("=" * 60)
        
        output_files = self.jsonl_writer.write_documents(all_docs, split_by_type=True)
        
        if law_docs:
            self.jsonl_writer.write_article_chunks(law_docs)
        
        logger.info(f"输出文件: {output_files}")
        
        self._save_stats(stats)
        
        return stats
    
    def _process_directory(self, directory: str, doc_type: str) -> List[ProcessedDocument]:
        """处理目录下所有文档"""
        if not os.path.exists(directory):
            logger.warning(f"目录不存在: {directory}")
            return []
        
        docs = []
        supported_extensions = ['.docx', '.doc', '.pdf', '.txt']
        
        all_files = []
        for root, dirs, files in os.walk(directory):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in supported_extensions:
                    all_files.append(os.path.join(root, file))
        
        logger.info(f"找到 {len(all_files)} 个文档文件")
        
        for file_path in tqdm(all_files, desc=f"处理{doc_type}文档"):
            try:
                doc = self._process_file(file_path, doc_type)
                if doc:
                    docs.append(doc)
            except Exception as e:
                logger.error(f"处理文件失败: {file_path}, 错误: {str(e)}")
        
        return docs
    
    def _process_file(self, file_path: str, doc_type: str) -> ProcessedDocument:
        """处理单个文件"""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext in ['.docx', '.doc']:
            return self.word_processor.process(file_path, doc_type)
        elif ext == '.pdf':
            return self.pdf_processor.process(file_path, doc_type)
        elif ext == '.txt':
            return self._process_txt(file_path, doc_type)
        else:
            logger.warning(f"不支持的文件格式: {ext}")
            return None
    
    def _process_txt(self, file_path: str, doc_type: str) -> ProcessedDocument:
        """处理TXT文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            doc = ProcessedDocument(
                file_name=os.path.basename(file_path),
                file_path=file_path,
                doc_type=doc_type,
                content=content
            )
            
            if doc_type == "law":
                self.word_processor._extract_law_metadata(content, doc)
            else:
                self.word_processor._extract_case_metadata(content, doc)
            
            return doc
            
        except Exception as e:
            logger.error(f"读取TXT文件失败: {file_path}, 错误: {str(e)}")
            return None
    
    def _save_stats(self, stats: dict):
        """保存统计信息"""
        import json
        from datetime import datetime
        
        stats_file = os.path.join(self.output_dir, "processing_stats.json")
        
        stats['processed_at'] = datetime.now().isoformat()
        
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        logger.info(f"统计信息已保存: {stats_file}")


def main():
    parser = argparse.ArgumentParser(description='法律文档数据预处理工具')
    parser.add_argument('--laws-dir', default='../knowledge_base/laws', help='法律文档目录')
    parser.add_argument('--cases-dir', default='../knowledge_base/cases', help='案例文档目录')
    parser.add_argument('--output-dir', default='./processed_data', help='输出目录')
    parser.add_argument('--use-ocr', action='store_true', help='对扫描版PDF使用OCR')
    parser.add_argument('--no-desensitize', action='store_true', help='不进行敏感信息脱敏')
    
    args = parser.parse_args()
    
    print("""
╔══════════════════════════════════════════════════════════╗
║          法律文档数据预处理工具                          ║
╚══════════════════════════════════════════════════════════╝
    """)
    
    print(f"配置信息:")
    print(f"  法律文档目录: {args.laws_dir}")
    print(f"  案例文档目录: {args.cases_dir}")
    print(f"  输出目录: {args.output_dir}")
    print(f"  使用OCR: {args.use_ocr}")
    print(f"  敏感信息脱敏: {not args.no_desensitize}")
    print()
    
    preprocessor = DataPreprocessor(
        laws_dir=args.laws_dir,
        cases_dir=args.cases_dir,
        output_dir=args.output_dir,
        use_ocr=args.use_ocr,
        desensitize=not args.no_desensitize
    )
    
    stats = preprocessor.process_all()
    
    print("\n" + "=" * 60)
    print("处理完成!")
    print("=" * 60)
    print(f"法律文档: {stats['laws']['success']}/{stats['laws']['total']} 成功")
    print(f"  提取法条: {stats['laws']['articles']} 条")
    print(f"案例文档: {stats['cases']['success']}/{stats['cases']['total']} 成功")
    print(f"\n输出目录: {args.output_dir}")
    print("  - laws.jsonl: 法律文档")
    print("  - cases.jsonl: 案例文档")
    print("  - article_chunks.jsonl: 法条数据块")
    print("  - processing_stats.json: 处理统计")


if __name__ == "__main__":
    main()
