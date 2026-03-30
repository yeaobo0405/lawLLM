"""
用户认证模块
支持用户登录、Token验证
"""
import os
import sqlite3
import hashlib
import secrets
import logging
from typing import Optional, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AuthManager:
    """用户认证管理器"""
    
    TOKEN_EXPIRE_HOURS = 24
    
    def __init__(self, db_path: str = "data/users.db"):
        """
        初始化认证管理器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()
        self._ensure_admin_user()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tokens_token 
            ON tokens(token)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tokens_user_id 
            ON tokens(user_id)
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"用户数据库初始化完成: {self.db_path}")
    
    def _ensure_admin_user(self):
        """确保admin用户存在"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM users WHERE username = ?', ('admin',))
        if not cursor.fetchone():
            password_hash = self._hash_password('123456')
            cursor.execute(
                'INSERT INTO users (username, password_hash) VALUES (?, ?)',
                ('admin', password_hash)
            )
            conn.commit()
            logger.info("已创建默认管理员账户: admin / 123456")
        
        conn.close()
    
    def _hash_password(self, password: str) -> str:
        """生成密码哈希"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _generate_token(self) -> str:
        """生成安全Token"""
        return secrets.token_urlsafe(32)
    
    def verify_user(self, username: str, password: str) -> Optional[int]:
        """
        验证用户凭据
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            用户ID或None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        password_hash = self._hash_password(password)
        cursor.execute(
            'SELECT id FROM users WHERE username = ? AND password_hash = ?',
            (username, password_hash)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def login(self, username: str, password: str) -> Optional[Dict]:
        """
        用户登录
        
        Args:
            username: 用户名
            password: 密码
            
        Returns:
            包含token和用户信息的字典，或None
        """
        user_id = self.verify_user(username, password)
        if not user_id:
            return None
        
        token = self._generate_token()
        expires_at = datetime.now() + timedelta(hours=self.TOKEN_EXPIRE_HOURS)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'INSERT INTO tokens (user_id, token, expires_at) VALUES (?, ?, ?)',
            (user_id, token, expires_at.isoformat())
        )
        
        conn.commit()
        conn.close()
        
        logger.info(f"用户登录成功: {username}")
        
        return {
            "token": token,
            "user_id": user_id,
            "username": username,
            "expires_at": expires_at.isoformat()
        }
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """
        验证Token
        
        Args:
            token: 认证Token
            
        Returns:
            用户信息字典或None
        """
        if not token:
            return None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT t.user_id, t.expires_at, u.username 
            FROM tokens t 
            JOIN users u ON t.user_id = u.id 
            WHERE t.token = ?
        ''', (token,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
        
        user_id, expires_at, username = result
        
        if datetime.fromisoformat(expires_at) < datetime.now():
            return None
        
        return {
            "user_id": user_id,
            "username": username
        }
    
    def logout(self, token: str) -> bool:
        """
        用户登出
        
        Args:
            token: 认证Token
            
        Returns:
            是否成功
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM tokens WHERE token = ?', (token,))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        return deleted
    
    def cleanup_expired_tokens(self):
        """清理过期的Token"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'DELETE FROM tokens WHERE expires_at < ?',
            (datetime.now().isoformat(),)
        )
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        if deleted > 0:
            logger.info(f"已清理 {deleted} 个过期Token")
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """根据ID获取用户信息"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            'SELECT id, username, created_at FROM users WHERE id = ?',
            (user_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                "id": result[0],
                "username": result[1],
                "created_at": result[2]
            }
        return None
