"""
PDF文档预处理模块
支持可复制版PDF和扫描版PDF（OCR）
"""
import os
import re
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class PDFProcessor:
    """PDF文档处理器"""
    
    def __init__(self, use_ocr: bool = False):
        self.use_ocr = use_ocr
        self.page_number_patterns = [
            r'^\s*第\s*\d+\s*页\s*$',
            r'^\s*\d+\s*/\s*\d+\s*$',
            r'^\s*-\s*\d+\s*-\s*$',
            r'^\s*\d+\s*$',
        ]
        self.watermark_patterns = [
            r'仅供.*?参考',
            r'内部资料',
            r'机密文件',
            r'版权所有',
        ]
    
    def extract_text_pdfplumber(self, file_path: str) -> str:
        """使用pdfplumber提取文本（适合可复制版PDF）"""
        try:
            import pdfplumber
            
            text_parts = []
            
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        lines = page_text.split('\n')
                        for line in lines:
                            line = line.strip()
                            if line and not self._is_page_number(line):
                                text_parts.append(line)
            
            return '\n'.join(text_parts)
            
        except Exception as e:
            logger.error(f"pdfplumber提取失败: {e}")
            return ""
    
    def extract_text_pymupdf(self, file_path: str) -> str:
        """使用PyMuPDF提取文本（备选方案）"""
        try:
            import fitz
            
            text_parts = []
            
            doc = fitz.open(file_path)
            for page in doc:
                page_text = page.get_text()
                if page_text:
                    lines = page_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not self._is_page_number(line):
                            text_parts.append(line)
            doc.close()
            
            return '\n'.join(text_parts)
            
        except Exception as e:
            logger.error(f"PyMuPDF提取失败: {e}")
            return ""
    
    def extract_text_ocr(self, file_path: str) -> str:
        """使用OCR提取文本（适合扫描版PDF）"""
        try:
            import fitz
            from PIL import Image
            import pytesseract
            
            text_parts = []
            
            doc = fitz.open(file_path)
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                mat = fitz.Matrix(2, 2)
                pix = page.get_pixmap(matrix=mat)
                
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                ocr_text = pytesseract.image_to_string(img, lang='chi_sim+eng')
                
                if ocr_text:
                    lines = ocr_text.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line and not self._is_page_number(line):
                            text_parts.append(line)
            
            doc.close()
            
            return '\n'.join(text_parts)
            
        except ImportError as e:
            logger.error(f"OCR依赖未安装: {e}")
            logger.error("请安装: pip install pytesseract pillow")
            logger.error("并下载Tesseract: https://github.com/tesseract-ocr/tesseract")
            return ""
        except Exception as e:
            logger.error(f"OCR提取失败: {e}")
            return ""
    
    def _is_page_number(self, text: str) -> bool:
        """判断是否为页码"""
        text = text.strip()
        
        for pattern in self.page_number_patterns:
            if re.match(pattern, text, re.IGNORECASE):
                return True
        
        if len(text) <= 3 and text.isdigit():
            return True
        
        return False
    
    def is_scanned_pdf(self, file_path: str) -> bool:
        """判断是否为扫描版PDF"""
        try:
            import fitz
            
            doc = fitz.open(file_path)
            
            text_length = 0
            for page in doc:
                text_length += len(page.get_text())
            
            doc.close()
            
            return text_length < 100
            
        except Exception:
            return False
    
    def process(self, file_path: str, doc_type: str = "case") -> Dict:
        """处理PDF文档"""
        from word_processor import ProcessedDocument
        
        file_name = os.path.basename(file_path)
        
        text = ""
        
        if self.use_ocr or self.is_scanned_pdf(file_path):
            logger.info(f"使用OCR处理扫描版PDF: {file_name}")
            text = self.extract_text_ocr(file_path)
        
        if not text:
            text = self.extract_text_pdfplumber(file_path)
        
        if not text:
            text = self.extract_text_pymupdf(file_path)
        
        if not text:
            logger.warning(f"无法提取PDF文本: {file_path}")
        
        processed_doc = ProcessedDocument(
            file_name=file_name,
            file_path=file_path,
            doc_type=doc_type,
            content=text
        )
        
        if text and doc_type == "case":
            self._extract_case_metadata(text, processed_doc)
        
        return processed_doc
    
    def _extract_case_metadata(self, text: str, doc):
        """提取案例文档元数据"""
        case_number_match = re.search(r'[（(](\d{4})[)）].*?第?(\d+号?)', text)
        if case_number_match:
            doc.case_number = case_number_match.group(0)
        
        date_match = re.search(r'(\d{4})年(\d{1,2})月(\d{1,2})日', text)
        if date_match:
            doc.judgment_date = date_match.group(0)
        
        case_types = ['民事', '刑事', '行政', '经济', '知识产权', '劳动争议']
        for ct in case_types:
            if ct in text:
                doc.case_type = ct
                break
