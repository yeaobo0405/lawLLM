"""
启动脚本
用于启动法律智能问答系统后端服务
"""
import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_environment():
    """
    检查运行环境
    """
    logger.info("检查运行环境...")
    
    required_packages = [
        'langchain',
        'langchain_openai',
        'langgraph',
        'pymilvus',
        'fastapi',
        'uvicorn',
        'cn2an',
        'tiktoken',
        'tenacity'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"缺少必要的依赖包: {', '.join(missing_packages)}")
        logger.error("请运行: pip install -r requirements.txt")
        return False
    
    logger.info("环境检查通过")
    return True


def check_milvus_connection():
    """
    检查Milvus连接
    """
    from config import settings
    from pymilvus import connections
    
    try:
        connections.connect(
            alias="check",
            host=settings.MILVUS_HOST,
            port=settings.MILVUS_PORT
        )
        connections.disconnect("check")
        logger.info(f"Milvus连接正常: {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
        return True
    except Exception as e:
        logger.warning(f"Milvus连接失败: {str(e)}")
        logger.warning("请确保Milvus服务已启动")
        return False
def main():
    """
    主函数
    """
    logger.info("=" * 50)
    logger.info("法律智能问答系统启动中...")
    logger.info("=" * 50)
    
    if not check_environment():
        sys.exit(1)
    
    check_milvus_connection()
    
    import uvicorn
    from main import app
    
    logger.info("启动FastAPI服务...")
    logger.info("API文档地址: http://localhost:8000/docs")
    logger.info("API交互文档: http://localhost:8000/redoc")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )


if __name__ == "__main__":
    main()
