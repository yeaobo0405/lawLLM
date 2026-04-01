import os
import re
import json
import logging
import cn2an
from docx import Document as DocxDocument
from typing import List, Dict, Any, Tuple

try:
    from .modules.document_processor import DocumentProcessor
except ImportError:
    from modules.document_processor import DocumentProcessor

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BaseDataEngine:
    """数据处理引擎基类"""
    def __init__(self, input_dir: str, output_path: str):
        self.input_dir = input_dir
        self.output_path = output_path
        if not os.path.exists(os.path.dirname(self.output_path)):
            os.makedirs(os.path.dirname(self.output_path))

class LawDataEngine(BaseDataEngine):
    """
    法律数据处理引擎
    负责解析文件名、提取法条内容、归一化编号并导出 JSONL
    """
    
    def __init__(self, input_dir: str, output_path: str):
        super().__init__(input_dir, output_path)
        self.processor = DocumentProcessor()
        self.filename_regex = re.compile(r'(.+?)_(\d{4}-\d{2}-\d{2})_(\d{4}-\d{2}-\d{2})_(.+?)_(.+?)_(.+?)\.docx')
        # 支持: "第一条", "一、", "1.", "1、" 等格式
        self.article_regex = re.compile(r'^(?:第([一二三四五六七八九十百零0-9]+)条|([一二三四五六七八九十百零0-9]+)[、.．])')

    def parse_filename(self, filename: str) -> Dict[str, str]:
        """
        从文件名提取元数据 (法律名_公布日期_施行日期_分类_机关_时效性)
        """
        match = self.filename_regex.match(filename)
        if match:
            return {
                "law_name": match.group(1),
                "publish_date": match.group(2),
                "effective_date": match.group(3),
                "category": match.group(4),
                "authority": match.group(5),
                "status": match.group(6)
            }
        
        # 增强容错：如果正则失败，尝试以下划线拆分，或者至少保留法律名称
        parts = filename.replace(".docx", "").split("_")
        if len(parts) >= 1:
            logger.info(f"文件名部分匹配 {filename}, 尝试提取基本信息")
            return {
                "law_name": parts[0],
                "publish_date": parts[1] if len(parts) > 1 else "未知",
                "effective_date": parts[2] if len(parts) > 2 else "未知",
                "category": parts[3] if len(parts) > 3 else "法律法规",
                "authority": parts[4] if len(parts) > 4 else "未知",
                "status": parts[5] if len(parts) > 5 else "有效"
            }
            
        logger.warning(f"文件名完全无法解析: {filename}")
        return {}

    def extract_articles(self, file_path: str) -> List[Dict[str, str]]:
        """
        使用 DocumentProcessor 加载并按条切分
        """
        try:
            # 1. 自动选择加载器加载文档 (pdf/doc/docx)
            loader_docs = self.processor.load_document(file_path)
            if not loader_docs:
                return []
            
            # 合并所有段落内容
            paragraphs = []
            for doc in loader_docs:
                # 处理可能包含多行的内容
                texts = [p.strip() for p in doc.page_content.split('\n') if p.strip()]
                paragraphs.extend(texts)
                
            if not paragraphs:
                logger.warning(f"加载器提取内容为空: {file_path}")
                return []

        except Exception as e:
            logger.error(f"无法读取文件 {file_path}: {e}")
            return []

        articles = []
        current_article_num = ""
        current_content = []

        for p in paragraphs:
            match = self.article_regex.match(p)
            if match:
                # 如果当前有正在处理的条文，先保存
                if current_article_num and current_content:
                    articles.append({
                        "article_number": current_article_num,
                        "content": "\n".join(current_content)
                    })
                
                # 开始新条文
                # 提取序号：优先从“第...条”中提，否则从“...、”中提
                raw_num = match.group(1) if match.group(1) else match.group(2)
                try:
                    # 统一转换为阿拉伯数字字符串
                    current_article_num = str(cn2an.cn2an(raw_num, "normal")) if not raw_num.isdigit() else raw_num
                except:
                    current_article_num = raw_num
                
                # 内容包含匹配后的剩余部分
                content_after = p[match.end():].strip(' :：')
                current_content = [content_after] if content_after else []
            else:
                if current_article_num:
                    current_content.append(p)
        
        # 保存最后一个条文
        if current_article_num and current_content:
            articles.append({
                "article_number": current_article_num,
                "content": "\n".join(current_content)
            })

        if not articles:
            logger.warning(f"未从文件提取到任何条文: {file_path}")
            # 如果没提取到条文，尝试作为单一记录处理
            if paragraphs:
                articles.append({
                    "article_number": "总则",
                    "content": "\n".join(paragraphs)
                })

        return articles

    def run(self):
        """
        启动法律生产逻辑
        """
        all_records = []
        count_files = 0
        count_articles = 0

        # 扩展支持后缀
        supported_exts = ['.docx', '.doc', '.pdf']
        
        for filename in os.listdir(self.input_dir):
            if any(filename.lower().endswith(ext) for ext in supported_exts):
                metadata = self.parse_filename(filename)
                if not metadata:
                    print(f"Skipping {filename}: metadata parse failed")
                    continue
                
                file_path = os.path.join(self.input_dir, filename)
                print(f"Loading law: {filename}...")
                articles = self.extract_articles(file_path)
                
                if not articles:
                    print(f"Warning: {filename} extrated 0 articles!")
                else:
                    print(f"Success: {filename} extrated {len(articles)} articles.")

                for art in articles:
                    record = {
                        **metadata,
                        "article_number": art["article_number"],
                        "content": art["content"],
                        "doc_type": "law",
                        "file_name": filename
                    }
                    all_records.append(record)
                    count_articles += 1
                
                count_files += 1

        with open(self.output_path, 'w', encoding='utf-8') as f:
            for record in all_records:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        logger.info(f"法律处理完成！文件数: {count_files}, 条文总数: {count_articles}, 输出: {self.output_path}")


class CaseDataEngine(BaseDataEngine):
    """案例数据处理引擎 - 针对裁判文书优化"""
    def __init__(self, input_dir: str, output_path: str):
        super().__init__(input_dir, output_path)
        self.processor = DocumentProcessor()
        # 语义分段标志
        self.section_headers = ['当事人信息', '审理经过', '事实与理由', '法院认为', '裁判结果']

    def process_case_file(self, file_path: str) -> List[Dict[str, str]]:
        """使用 DocumentProcessor 加载并拆分案例"""
        try:
            # 1. 自动选择加载器加载文档 (pdf/doc/docx)
            docs = self.processor.load_document(file_path)
            if not docs:
                return []
            
            full_text = "\n".join([doc.page_content for doc in docs])
            
            # 对全文进行数据清洗 (移除 PDF 噪声)
            full_text = self.processor.data_cleaning(full_text)
            
            filename = os.path.basename(file_path)
            
            # 2. 提取元数据 (案号、日期等)
            case_metadata = self.processor.extract_case_metadata(full_text, file_path)
            
            # 3. 语义分段逻辑
            # 如果文中包含明确的语义标志位，则按标志位切分
            split_pattern = f"({'|'.join(self.section_headers)})"
            parts = re.split(split_pattern, full_text)
            
            chunks = []
            if len(parts) > 1:
                # 包含标志位，进行结构化组装
                for i in range(1, len(parts), 2):
                    header = parts[i]
                    content = parts[i+1] if i+1 < len(parts) else ""
                    if len(content.strip()) > 20:
                        chunks.append({
                            "content": f"{header}\n{content.strip()}",
                            "case_number": case_metadata.case_number,
                            "judgment_date": case_metadata.judgment_date,
                            "case_type": case_metadata.case_type,
                            "doc_type": "case",
                            "file_name": filename
                        })
            
            # 4. 如果没有明显的语义标志，或者切分后的块依然太长，使用递归切分
            if not chunks:
                # 使用 processor 内置的 splitter 进行基础切分
                from langchain.schema import Document as LCDocument
                temp_doc = LCDocument(page_content=full_text, metadata={})
                sub_docs = self.processor.text_splitter.split_documents([temp_doc])
                for sd in sub_docs:
                    chunks.append({
                        "content": sd.page_content,
                        "case_number": case_metadata.case_number,
                        "judgment_date": case_metadata.judgment_date,
                        "case_type": case_metadata.case_type,
                        "doc_type": "case",
                        "file_name": filename
                    })
            
            return chunks
        except Exception as e:
            logger.error(f"处理案例失败 {file_path}: {str(e)}")
            return []

    def run(self):
        all_records = []
        count_files = 0
        
        # 扩展支持后缀
        supported_exts = ['.docx', '.doc', '.pdf']
        
        for filename in os.listdir(self.input_dir):
            if any(filename.lower().endswith(ext) for ext in supported_exts):
                logger.info(f"正在处理案例: {filename}")
                file_path = os.path.join(self.input_dir, filename)
                records = self.process_case_file(file_path)
                all_records.extend(records)
                count_files += 1
        
        with open(self.output_path, 'w', encoding='utf-8') as f:
            for r in all_records:
                f.write(json.dumps(r, ensure_ascii=False) + '\n')
        logger.info(f"案例处理完成！文件数: {count_files}, Chunk总数: {len(all_records)}, 输出: {self.output_path}")

if __name__ == "__main__":
    # 处理法律
    LawDataEngine(
        input_dir=r"d:\develop1\law03\knowledge_base\laws",
        output_path=r"d:\develop1\law03\backend\data\laws_processed.jsonl"
    ).run()
    
    # 处理案例
    CaseDataEngine(
        input_dir=r"d:\develop1\law03\knowledge_base\cases",
        output_path=r"d:\develop1\law03\backend\data\cases_processed.jsonl"
    ).run()
