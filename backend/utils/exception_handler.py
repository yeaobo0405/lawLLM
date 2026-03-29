"""
异常处理与优化模块
处理系统运行中的各类异常，优化系统性能与用户体验
"""
import logging
import functools
import traceback
from typing import Callable, Any
from datetime import datetime
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


class LegalQAException(Exception):
    """法律问答系统基础异常"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class MilvusConnectionError(LegalQAException):
    """Milvus连接异常"""
    def __init__(self, message: str = "Milvus数据库连接失败"):
        super().__init__(message, "MILVUS_CONNECTION_ERROR")


class EmbeddingModelError(LegalQAException):
    """嵌入模型异常"""
    def __init__(self, message: str = "嵌入模型加载或运行失败"):
        super().__init__(message, "EMBEDDING_MODEL_ERROR")


class DocumentProcessingError(LegalQAException):
    """文档处理异常"""
    def __init__(self, message: str = "文档处理失败"):
        super().__init__(message, "DOCUMENT_PROCESSING_ERROR")


class LLMError(LegalQAException):
    """大语言模型异常"""
    def __init__(self, message: str = "大语言模型调用失败"):
        super().__init__(message, "LLM_ERROR")


class FileNotFoundError(LegalQAException):
    """文件未找到异常"""
    def __init__(self, message: str = "文件不存在"):
        super().__init__(message, "FILE_NOT_FOUND")


class MemoryOverflowError(LegalQAException):
    """显存溢出异常"""
    def __init__(self, message: str = "显存不足，请减少批量处理数量"):
        super().__init__(message, "MEMORY_OVERFLOW_ERROR")


def handle_exceptions(default_return: Any = None):
    """
    异常处理装饰器
    
    Args:
        default_return: 发生异常时的默认返回值
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except LegalQAException as e:
                logger.error(f"业务异常: {e.message}, 错误码: {e.error_code}")
                return default_return
            except MemoryError as e:
                logger.error(f"内存溢出: {str(e)}")
                raise MemoryOverflowError()
            except Exception as e:
                logger.error(f"未预期异常: {str(e)}\n{traceback.format_exc()}")
                return default_return
        return wrapper
    return decorator


def handle_gpu_memory(func: Callable) -> Callable:
    """
    GPU显存管理装饰器
    自动清理GPU缓存
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                logger.error("GPU显存溢出，正在尝试清理...")
                try:
                    import torch
                    torch.cuda.empty_cache()
                    logger.info("GPU缓存已清理")
                except ImportError:
                    pass
                raise MemoryOverflowError()
            raise
        finally:
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except ImportError:
                pass
    return wrapper


class PerformanceMonitor:
    """
    性能监控器
    记录操作耗时，监控系统性能
    """
    
    def __init__(self):
        self.metrics = {}
    
    def record(self, operation: str, duration: float):
        """
        记录操作耗时
        
        Args:
            operation: 操作名称
            duration: 耗时（秒）
        """
        if operation not in self.metrics:
            self.metrics[operation] = []
        
        self.metrics[operation].append({
            "timestamp": datetime.now().isoformat(),
            "duration": duration
        })
        
        if len(self.metrics[operation]) > 100:
            self.metrics[operation] = self.metrics[operation][-100:]
    
    def get_average_duration(self, operation: str) -> float:
        """
        获取操作平均耗时
        
        Args:
            operation: 操作名称
            
        Returns:
            平均耗时（秒）
        """
        if operation not in self.metrics or not self.metrics[operation]:
            return 0.0
        
        durations = [m["duration"] for m in self.metrics[operation]]
        return sum(durations) / len(durations)
    
    def get_stats(self) -> dict:
        """
        获取性能统计
        
        Returns:
            性能统计字典
        """
        stats = {}
        for operation, records in self.metrics.items():
            durations = [m["duration"] for m in records]
            stats[operation] = {
                "count": len(durations),
                "avg_duration": sum(durations) / len(durations) if durations else 0,
                "max_duration": max(durations) if durations else 0,
                "min_duration": min(durations) if durations else 0
            }
        return stats


def monitor_performance(monitor: PerformanceMonitor):
    """
    性能监控装饰器
    
    Args:
        monitor: 性能监控器实例
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = (datetime.now() - start_time).total_seconds()
                monitor.record(func.__name__, duration)
                logger.debug(f"{func.__name__} 耗时: {duration:.3f}秒")
        return wrapper
    return decorator


class LogWriter:
    """
    日志写入器
    记录系统操作日志
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
    
    def write_operation_log(
        self, 
        operation: str, 
        user_id: str = "anonymous",
        details: dict = None,
        status: str = "success"
    ):
        """
        写入操作日志
        
        Args:
            operation: 操作类型
            user_id: 用户ID
            details: 操作详情
            status: 操作状态
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "user_id": user_id,
            "status": status,
            "details": details or {}
        }
        
        log_file = os.path.join(self.log_dir, f"operations_{datetime.now().strftime('%Y%m%d')}.log")
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(str(log_entry) + '\n')
    
    def write_error_log(
        self, 
        error_type: str, 
        error_message: str,
        stack_trace: str = None,
        user_id: str = "anonymous"
    ):
        """
        写入错误日志
        
        Args:
            error_type: 错误类型
            error_message: 错误信息
            stack_trace: 堆栈跟踪
            user_id: 用户ID
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "stack_trace": stack_trace,
            "user_id": user_id
        }
        
        log_file = os.path.join(self.log_dir, f"errors_{datetime.now().strftime('%Y%m%d')}.log")
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(str(log_entry) + '\n')


performance_monitor = PerformanceMonitor()
log_writer = LogWriter()
