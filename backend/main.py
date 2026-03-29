"""
后端API模块
使用FastAPI实现RESTful API接口
"""
import os
import logging
import uuid
from typing import List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from config import settings
from modules.rag_retriever import MilvusManager, HybridRetriever, EmbeddingGenerator
from modules.langgraph_workflow import LegalWorkflow
from modules.optimized_workflow import OptimizedLegalWorkflow
from modules.document_processor import DocumentProcessor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="法律智能问答系统API",
    description="基于RAG的法律智能问答系统后端接口",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

milvus_manager: Optional[MilvusManager] = None
embedding_generator: Optional[EmbeddingGenerator] = None
hybrid_retriever: Optional[HybridRetriever] = None
workflow: Optional[LegalWorkflow] = None
optimized_workflow: Optional[OptimizedLegalWorkflow] = None


class QueryRequest(BaseModel):
    """用户提问请求"""
    query: str = Field(..., description="用户提问内容", min_length=1, max_length=2000)
    session_id: Optional[str] = Field(None, description="会话ID，用于多轮对话")


class QueryResponse(BaseModel):
    """提问响应"""
    success: bool = Field(..., description="是否成功")
    answer: str = Field(..., description="回答内容")
    disclaimer: str = Field(..., description="免责声明")
    search_results: List[dict] = Field(default_factory=list, description="检索结果")
    session_id: str = Field(..., description="会话ID")


class FileFilterRequest(BaseModel):
    """文件筛选请求"""
    law_name: Optional[str] = Field(None, description="法律名称")
    case_type: Optional[str] = Field(None, description="案件类型")
    article_number: Optional[str] = Field(None, description="法条编号")


class FileInfo(BaseModel):
    """文件信息"""
    file_path: str = Field(..., description="文件路径")
    file_name: str = Field(..., description="文件名")
    law_name: str = Field(default="", description="法律名称")
    case_type: str = Field(default="", description="案件类型")
    article_number: str = Field(default="", description="法条编号")
    doc_type: str = Field(default="", description="文档类型")


class FileListResponse(BaseModel):
    """文件列表响应"""
    success: bool = Field(..., description="是否成功")
    total: int = Field(..., description="总数")
    files: List[FileInfo] = Field(..., description="文件列表")


class FileJumpRequest(BaseModel):
    """文件跳转请求"""
    file_path: str = Field(..., description="文件路径")


class FileJumpResponse(BaseModel):
    """文件跳转响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")
    file_exists: bool = Field(..., description="文件是否存在")


class UploadResponse(BaseModel):
    """上传响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="提示信息")
    file_name: Optional[str] = Field(None, description="文件名")


class SystemStatus(BaseModel):
    """系统状态"""
    milvus_connected: bool = Field(..., description="Milvus连接状态")
    embedding_model_loaded: bool = Field(..., description="嵌入模型加载状态")
    total_documents: int = Field(default=0, description="文档总数")


@app.on_event("startup")
async def startup_event():
    """
    应用启动时初始化
    """
    global milvus_manager, embedding_generator, hybrid_retriever, workflow, optimized_workflow
    
    try:
        logger.info("正在初始化系统组件...")
        
        milvus_manager = MilvusManager()
        if not milvus_manager.connect():
            logger.error("Milvus连接失败")
        else:
            milvus_manager.create_collection()
        
        logger.info("正在预加载嵌入模型...")
        embedding_generator = EmbeddingGenerator()
        embedding_generator.load_model()
        
        hybrid_retriever = HybridRetriever(milvus_manager, embedding_generator)
        
        logger.info("正在预加载重排模型...")
        hybrid_retriever.reranker.load_model()
        
        logger.info("正在构建BM25索引...")
        hybrid_retriever.build_bm25_index()
        
        workflow = LegalWorkflow(hybrid_retriever)
        optimized_workflow = OptimizedLegalWorkflow(hybrid_retriever)
        
        logger.info("系统初始化完成，所有模型已预加载")
        
    except Exception as e:
        logger.error(f"系统初始化失败: {str(e)}")


@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭时清理资源
    """
    global milvus_manager
    
    if milvus_manager:
        milvus_manager.disconnect()
    
    logger.info("系统资源已释放")


@app.get("/", tags=["系统"])
async def root():
    """
    根路径
    """
    return {"message": "法律智能问答系统API", "version": "1.0.0"}


@app.get("/api/system/status", response_model=SystemStatus, tags=["系统"])
async def get_system_status():
    """
    获取系统状态
    """
    global milvus_manager, embedding_generator
    
    milvus_connected = False
    total_documents = 0
    
    try:
        if milvus_manager and milvus_manager.collection:
            milvus_connected = True
            milvus_manager.collection.load()
            total_documents = milvus_manager.collection.num_entities
    except Exception:
        pass
    
    embedding_loaded = embedding_generator is not None and embedding_generator.model is not None
    
    return SystemStatus(
        milvus_connected=milvus_connected,
        embedding_model_loaded=embedding_loaded,
        total_documents=total_documents
    )


@app.post("/api/legal/query", response_model=QueryResponse, tags=["法律咨询"])
async def legal_query(request: QueryRequest):
    """
    用户提问接口（优化版，非流式）
    接收用户提问，返回法律咨询回答
    """
    global optimized_workflow
    
    if optimized_workflow is None:
        raise HTTPException(status_code=503, detail="系统未初始化完成，请稍后重试")
    
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        result = optimized_workflow.run_fast(request.query, session_id)
        
        return QueryResponse(
            success=result.get("success", False),
            answer=result.get("answer", ""),
            disclaimer=result.get("disclaimer", ""),
            search_results=result.get("search_results", []),
            session_id=session_id
        )
        
    except Exception as e:
        logger.error(f"处理提问失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"处理提问失败: {str(e)}")


@app.post("/api/legal/query/stream", tags=["法律咨询"])
async def legal_query_stream(request: QueryRequest):
    """
    用户提问接口（流式输出）
    接收用户提问，流式返回法律咨询回答
    """
    global optimized_workflow
    
    if optimized_workflow is None:
        raise HTTPException(status_code=503, detail="系统未初始化完成，请稍后重试")
    
    session_id = request.session_id or str(uuid.uuid4())
    
    return StreamingResponse(
        optimized_workflow.run_stream(request.query, session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/conversation/clear", tags=["法律咨询"])
async def clear_conversation(session_id: str = Query(default="default", description="会话ID")):
    """
    清除对话历史
    """
    global workflow
    
    if workflow:
        workflow.clear_memory(session_id)
    
    return {"success": True, "message": "对话历史已清除"}


@app.post("/api/file/filter", response_model=FileListResponse, tags=["文件管理"])
async def filter_files(request: FileFilterRequest):
    """
    文件筛选接口
    支持按法律名称、案件类型、法条编号多条件组合筛选
    """
    global milvus_manager
    
    if milvus_manager is None:
        raise HTTPException(status_code=503, detail="系统未初始化完成")
    
    try:
        results = milvus_manager.filter_by_metadata(
            law_name=request.law_name,
            case_type=request.case_type,
            article_number=request.article_number
        )
        
        file_map = {}
        for item in results:
            file_path = item.get("file_path", "")
            if file_path and file_path not in file_map:
                file_map[file_path] = FileInfo(
                    file_path=file_path,
                    file_name=item.get("file_name", ""),
                    law_name=item.get("law_name", ""),
                    case_type=item.get("case_type", ""),
                    article_number=item.get("article_number", ""),
                    doc_type=item.get("doc_type", "")
                )
        
        files = list(file_map.values())
        
        return FileListResponse(
            success=True,
            total=len(files),
            files=files
        )
        
    except Exception as e:
        logger.error(f"文件筛选失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文件筛选失败: {str(e)}")


@app.get("/api/file/list", response_model=FileListResponse, tags=["文件管理"])
async def get_file_list():
    """
    获取所有文件列表
    """
    global milvus_manager
    
    if milvus_manager is None:
        raise HTTPException(status_code=503, detail="系统未初始化完成")
    
    try:
        files = milvus_manager.get_all_files()
        
        file_infos = [
            FileInfo(
                file_path=f.get("file_path", ""),
                file_name=f.get("file_name", ""),
                law_name=f.get("law_name", ""),
                case_type=f.get("case_type", ""),
                article_number=f.get("article_number", ""),
                doc_type=f.get("doc_type", "")
            )
            for f in files
        ]
        
        return FileListResponse(
            success=True,
            total=len(file_infos),
            files=file_infos
        )
        
    except Exception as e:
        logger.error(f"获取文件列表失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")


@app.post("/api/file/jump", response_model=FileJumpResponse, tags=["文件管理"])
async def jump_to_file(request: FileJumpRequest):
    """
    文件跳转接口
    校验文件路径有效性，返回文件预览/打开权限
    """
    file_path = request.file_path
    
    if not file_path:
        return FileJumpResponse(
            success=False,
            message="文件路径不能为空",
            file_exists=False
        )
    
    if not os.path.isabs(file_path):
        return FileJumpResponse(
            success=False,
            message="文件路径必须是绝对路径",
            file_exists=False
        )
    
    if not os.path.exists(file_path):
        return FileJumpResponse(
            success=False,
            message=f"文件不存在: {file_path}",
            file_exists=False
        )
    
    if not os.path.isfile(file_path):
        return FileJumpResponse(
            success=False,
            message="路径不是文件",
            file_exists=False
        )
    
    return FileJumpResponse(
        success=True,
        message="文件存在，可以打开",
        file_exists=True
    )


@app.get("/api/file/preview")
async def preview_file(file_path: str = Query(..., description="文件路径")):
    """
    文件预览接口
    返回文件内容供预览
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail="路径不是文件")
    
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        return FileResponse(
            file_path,
            media_type='application/pdf',
            filename=os.path.basename(file_path)
        )
    elif ext in ['.docx', '.doc']:
        return FileResponse(
            file_path,
            media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            filename=os.path.basename(file_path)
        )
    elif ext == '.txt':
        return FileResponse(
            file_path,
            media_type='text/plain',
            filename=os.path.basename(file_path)
        )
    else:
        raise HTTPException(status_code=415, detail="不支持的文件类型")


@app.get("/api/file/content")
async def get_file_content(file_path: str = Query(..., description="文件路径")):
    """
    获取文件内容接口
    用于在线预览文件内容
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail="路径不是文件")
    
    ext = os.path.splitext(file_path)[1].lower()
    
    try:
        content = ""
        
        if ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        elif ext == '.docx':
            import docx2txt
            import zipfile
            try:
                # 先尝试作为标准docx读取
                content = docx2txt.process(file_path)
            except zipfile.BadZipFile:
                # 如果不是zip格式，可能是旧版doc格式但扩展名为docx
                try:
                    import win32com.client
                    word = win32com.client.Dispatch("Word.Application")
                    word.Visible = False
                    doc = word.Documents.Open(os.path.abspath(file_path))
                    content = doc.Content.Text
                    doc.Close(False)
                    word.Quit()
                except Exception as e:
                    raise HTTPException(status_code=500, detail=f"无法读取文件: {str(e)}")
        elif ext == '.pdf':
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            content = "\n\n".join([page.extract_text() or "" for page in reader.pages])
        elif ext == '.doc':
            try:
                import win32com.client
                word = win32com.client.Dispatch("Word.Application")
                word.Visible = False
                doc = word.Documents.Open(os.path.abspath(file_path))
                content = doc.Content.Text
                doc.Close(False)
                word.Quit()
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"无法读取DOC文件: {str(e)}")
        else:
            raise HTTPException(status_code=415, detail="不支持的文件类型")
        
        return {
            "success": True,
            "content": content,
            "file_name": os.path.basename(file_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"读取文件内容失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"读取文件内容失败: {str(e)}")


@app.get("/api/file/download")
async def download_file(file_path: str = Query(..., description="文件路径")):
    """
    文件下载接口
    """
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if not os.path.isfile(file_path):
        raise HTTPException(status_code=400, detail="路径不是文件")
    
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext == '.pdf':
        media_type = 'application/pdf'
    elif ext == '.docx':
        media_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    elif ext == '.doc':
        media_type = 'application/msword'
    elif ext == '.txt':
        media_type = 'text/plain'
    else:
        media_type = 'application/octet-stream'
    
    return FileResponse(
        file_path,
        media_type=media_type,
        filename=os.path.basename(file_path)
    )


@app.post("/api/knowledge/upload", response_model=UploadResponse, tags=["知识库管理"])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type: str = Query(default="law", description="文档类型: law/case")
):
    """
    上传文档到知识库
    支持PDF、DOCX、TXT格式
    """
    global milvus_manager, embedding_generator
    
    allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
    ext = os.path.splitext(file.filename)[1].lower()
    
    if ext not in allowed_extensions:
        return UploadResponse(
            success=False,
            message=f"不支持的文件格式: {ext}，仅支持PDF、DOCX、TXT格式"
        )
    
    try:
        upload_dir = os.path.join(settings.KNOWLEDGE_BASE_PATH or "./knowledge_base", doc_type)
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        
        content = await file.read()
        with open(file_path, 'wb') as f:
            f.write(content)
        
        background_tasks.add_task(
            process_uploaded_document,
            file_path,
            doc_type
        )
        
        return UploadResponse(
            success=True,
            message="文件上传成功，正在后台处理中",
            file_name=file.filename
        )
        
    except Exception as e:
        logger.error(f"文件上传失败: {str(e)}")
        return UploadResponse(
            success=False,
            message=f"文件上传失败: {str(e)}"
        )


def process_uploaded_document(file_path: str, doc_type: str):
    """
    后台处理上传的文档
    
    Args:
        file_path: 文件路径
        doc_type: 文档类型
    """
    global milvus_manager, embedding_generator
    
    try:
        processor = DocumentProcessor()
        chunks = processor.process_document(file_path, doc_type)
        
        if not chunks:
            logger.warning(f"文档处理未生成任何块: {file_path}")
            return
        
        documents = [
            {
                "content": chunk.page_content,
                **chunk.metadata
            }
            for chunk in chunks
        ]
        
        texts = [doc["content"] for doc in documents]
        embeddings = embedding_generator.generate_embeddings(texts)
        
        milvus_manager.insert_documents(documents, embeddings)
        
        logger.info(f"文档处理完成: {file_path}")
        
    except Exception as e:
        logger.error(f"后台处理文档失败: {str(e)}")


@app.post("/api/knowledge/rebuild", tags=["知识库管理"])
async def rebuild_knowledge_base(
    background_tasks: BackgroundTasks,
    directory: str = Query(default="./knowledge_base", description="知识库目录")
):
    """
    重建知识库索引
    扫描指定目录下的所有文档并建立索引
    """
    global milvus_manager, embedding_generator, hybrid_retriever
    
    if not os.path.exists(directory):
        raise HTTPException(status_code=404, detail="知识库目录不存在")
    
    background_tasks.add_task(
        rebuild_index_task,
        directory
    )
    
    return {"success": True, "message": "知识库重建任务已启动，请稍后查看状态"}


def rebuild_index_task(directory: str):
    """
    后台重建索引任务
    
    Args:
        directory: 知识库目录
    """
    global milvus_manager, embedding_generator, hybrid_retriever
    
    try:
        processor = DocumentProcessor(directory)
        
        laws_dir = os.path.join(directory, "laws")
        if os.path.exists(laws_dir):
            for chunks in processor.process_directory(laws_dir, "law"):
                documents = [
                    {"content": chunk.page_content, **chunk.metadata}
                    for chunk in chunks
                ]
                texts = [doc["content"] for doc in documents]
                embeddings = embedding_generator.generate_embeddings(texts)
                milvus_manager.insert_documents(documents, embeddings)
        
        cases_dir = os.path.join(directory, "cases")
        if os.path.exists(cases_dir):
            for chunks in processor.process_directory(cases_dir, "case"):
                documents = [
                    {"content": chunk.page_content, **chunk.metadata}
                    for chunk in chunks
                ]
                texts = [doc["content"] for doc in documents]
                embeddings = embedding_generator.generate_embeddings(texts)
                milvus_manager.insert_documents(documents, embeddings)
        
        if hybrid_retriever:
            hybrid_retriever.build_bm25_index()
        
        logger.info("知识库索引重建完成")
        
    except Exception as e:
        logger.error(f"知识库索引重建失败: {str(e)}")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    全局异常处理
    """
    logger.error(f"未处理的异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误，请稍后重试",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
