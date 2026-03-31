"""
对话记忆存储模块
使用SQLite持久化存储对话历史，支持用户隔离
"""
import os
import sqlite3
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ConversationMemory:
    """对话记忆管理器"""
    
    def __init__(self, db_path: str = "data/conversation_memory.db"):
        """
        初始化对话记忆管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 0,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_session_id 
            ON conversations(session_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_user_id 
            ON conversations(user_id)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON conversations(created_at)
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS summaries (
                session_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL DEFAULT 0,
                layer1_summary TEXT,
                layer2_summary TEXT,
                layer1_msg_count INTEGER DEFAULT 0,
                layer2_msg_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"对话记忆数据库初始化完成: {self.db_path}")
    
    def add_message(self, session_id: str, role: str, content: str, user_id: int = 0):
        """
        添加一条对话记录
        
        Args:
            session_id: 会话ID
            role: 角色 (user/assistant)
            content: 内容
            user_id: 用户ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversations (user_id, session_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, session_id, role, content, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_history(self, session_id: str, limit: int = 20, user_id: int = 0) -> List[Dict[str, str]]:
        """
        获取会话历史记录
        
        Args:
            session_id: 会话ID
            limit: 最大返回条数
            user_id: 用户ID
            
        Returns:
            对话历史列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT role, content 
            FROM conversations 
            WHERE session_id = ? AND user_id = ?
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (session_id, user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        history = [{"role": row[0], "content": row[1]} for row in reversed(rows)]
        return history
    
    def clear_history(self, session_id: str, user_id: int = 0):
        """
        清除指定会话的历史记录
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'DELETE FROM conversations WHERE session_id = ? AND user_id = ?',
            (session_id, user_id)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"已清除会话历史: {session_id}")
    
    def clear_all_history(self, user_id: Optional[int] = None):
        """
        清除会话历史
        
        Args:
            user_id: 用户ID，为None时清除所有
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id is not None:
            cursor.execute('DELETE FROM conversations WHERE user_id = ?', (user_id,))
        else:
            cursor.execute('DELETE FROM conversations')
        
        conn.commit()
        conn.close()
        logger.info(f"已清除会话历史: user_id={user_id}")
    
    def get_user_sessions(self, user_id: int) -> List[Dict]:
        """
        获取用户的所有会话列表
        
        Args:
            user_id: 用户ID
            
        Returns:
            会话列表，每个会话包含session_id、消息数量、最后更新时间
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT session_id, COUNT(*) as msg_count, MAX(created_at) as last_time
            FROM conversations 
            WHERE user_id = ?
            GROUP BY session_id
            ORDER BY last_time DESC
        ''', (user_id,))
        
        sessions = []
        for row in cursor.fetchall():
            sessions.append({
                "session_id": row[0],
                "message_count": row[1],
                "last_updated": row[2]
            })
        
        conn.close()
        return sessions
    
    def get_session_messages(self, session_id: str, user_id: int) -> List[Dict]:
        """
        获取会话的所有消息
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            消息列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT role, content, created_at
            FROM conversations 
            WHERE session_id = ? AND user_id = ?
            ORDER BY created_at ASC
        ''', (session_id, user_id))
        
        messages = []
        for row in cursor.fetchall():
            messages.append({
                "role": row[0],
                "content": row[1],
                "created_at": row[2]
            })
        
        conn.close()
        return messages
    
    def get_all_sessions(self) -> List[str]:
        """获取所有会话ID列表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT DISTINCT session_id 
            FROM conversations 
            ORDER BY created_at DESC
        ''')
        
        sessions = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return sessions
    
    def get_stats(self, user_id: Optional[int] = None) -> Dict:
        """
        获取统计信息
        
        Args:
            user_id: 用户ID，为None时统计所有
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if user_id is not None:
            cursor.execute(
                'SELECT COUNT(*) FROM conversations WHERE user_id = ?',
                (user_id,)
            )
            total_messages = cursor.fetchone()[0]
            
            cursor.execute(
                'SELECT COUNT(DISTINCT session_id) FROM conversations WHERE user_id = ?',
                (user_id,)
            )
            total_sessions = cursor.fetchone()[0]
        else:
            cursor.execute('SELECT COUNT(*) FROM conversations')
            total_messages = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(DISTINCT session_id) FROM conversations')
            total_sessions = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_messages": total_messages,
            "total_sessions": total_sessions
        }
    
    def delete_session(self, session_id: str, user_id: int = 0) -> bool:
        """
        删除指定会话的所有消息
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            是否删除成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                'DELETE FROM conversations WHERE session_id = ? AND user_id = ?',
                (session_id, user_id)
            )
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_count > 0:
                logger.info(f"已删除会话 {session_id} 的 {deleted_count} 条消息")
                return True
            else:
                logger.warning(f"未找到会话 {session_id} 或无权删除")
                return False
        except Exception as e:
            logger.error(f"删除会话失败: {e}")
            return False
    def save_summary(
        self, 
        session_id: str, 
        user_id: int, 
        layer1_summary: str, 
        layer2_summary: str,
        layer1_msg_count: int,
        layer2_msg_count: int
    ):
        """保存会话摘要"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO summaries (
                session_id, user_id, 
                layer1_summary, layer2_summary, 
                layer1_msg_count, layer2_msg_count, 
                last_updated
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                layer1_summary=excluded.layer1_summary,
                layer2_summary=excluded.layer2_summary,
                layer1_msg_count=excluded.layer1_msg_count,
                layer2_msg_count=excluded.layer2_msg_count,
                last_updated=excluded.last_updated
        ''', (
            session_id, user_id, 
            layer1_summary, layer2_summary, 
            layer1_msg_count, layer2_msg_count, 
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_summary(self, session_id: str, user_id: int) -> Optional[Dict]:
        """获取会话摘要"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT layer1_summary, layer2_summary, layer1_msg_count, layer2_msg_count
            FROM summaries
            WHERE session_id = ? AND user_id = ?
        ''', (session_id, user_id))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "layer1_summary": row[0],
                "layer2_summary": row[1],
                "layer1_msg_count": row[2],
                "layer2_msg_count": row[3]
            }
        return None

    def delete_summary(self, session_id: str, user_id: int):
        """删除会话摘要"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM summaries WHERE session_id = ? AND user_id = ?', (session_id, user_id))
        conn.commit()
        conn.close()
