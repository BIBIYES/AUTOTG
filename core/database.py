#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class Database:
    """数据库管理类"""
    
    def __init__(self, db_file='data.db'):
        """
        初始化数据库管理器
        
        Args:
            db_file: 数据库文件路径，默认为'data.db'
        """
        self.db_file = db_file
        self.conn = None
        self.cursor = None
        self.init_db()
    
    def init_db(self):
        """初始化数据库连接和表结构"""
        try:
            db_exists = os.path.exists(self.db_file)
            
            # 创建连接
            self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
            # 设置行工厂为字典
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            
            # 创建消息表
            # 旧的建表语句（保留，以防万一）
            # CREATE TABLE IF NOT EXISTS messages ( ... raw_data TEXT, ... )
            
            # 检查raw_data列是否存在
            self.cursor.execute("PRAGMA table_info(messages)")
            columns = [column['name'] for column in self.cursor.fetchall()]
            if 'raw_data' in columns:
                logger.info("检测到旧的 'raw_data' 列，正在尝试移除...")
                try:
                    # 创建一个没有raw_data的新表
                    self.cursor.execute('''
                    CREATE TABLE messages_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER, chat_id INTEGER,
                        chat_title TEXT, chat_type TEXT, sender_id INTEGER, sender_username TEXT,
                        sender_first_name TEXT, sender_last_name TEXT, text TEXT, date TEXT,
                        media_type TEXT, is_forwarded BOOLEAN, forward_from TEXT,
                        reply_to_msg_id INTEGER, created_at TEXT
                    )
                    ''')
                    # 复制数据
                    self.cursor.execute('''
                    INSERT INTO messages_new SELECT 
                        id, message_id, chat_id, chat_title, chat_type, sender_id, sender_username,
                        sender_first_name, sender_last_name, text, date, media_type, is_forwarded,
                        forward_from, reply_to_msg_id, created_at 
                    FROM messages
                    ''')
                    # 删除旧表
                    self.cursor.execute("DROP TABLE messages")
                    # 重命名新表
                    self.cursor.execute("ALTER TABLE messages_new RENAME TO messages")
                    self.conn.commit()
                    logger.info("'raw_data' 列已成功移除。")
                except Exception as e:
                    logger.error(f"移除 'raw_data' 列失败，可能需要手动处理数据库: {e}")
                    # 如果失败，可能需要回滚
                    self.conn.rollback()
            else:
                 # 如果列不存在，则创建新表（不含raw_data）
                self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, message_id INTEGER, chat_id INTEGER,
                    chat_title TEXT, chat_type TEXT, sender_id INTEGER, sender_username TEXT,
                    sender_first_name TEXT, sender_last_name TEXT, text TEXT, date TEXT,
                    media_type TEXT, is_forwarded BOOLEAN, forward_from TEXT,
                    reply_to_msg_id INTEGER, created_at TEXT
                )
                ''')
            
            # 创建索引
            self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)
            ''')
            self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_sender_id ON messages(sender_id)
            ''')
            self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date)
            ''')
            
            self.conn.commit()
            
            if not db_exists:
                logger.info(f"数据库初始化成功: {self.db_file}")
            else:
                logger.info(f"连接到现有数据库: {self.db_file}")
                
        except Exception as e:
            logger.error(f"初始化数据库失败: {e}")
    
    def close(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")
    
    def save_message(self, message_data):
        """
        保存消息到数据库
        
        Args:
            message_data: 消息数据字典
            
        Returns:
            插入的消息ID
        """
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            self.cursor.execute('''
            INSERT INTO messages (
                message_id, chat_id, chat_title, chat_type, sender_id,
                sender_username, sender_first_name, sender_last_name, text,
                date, media_type, is_forwarded, forward_from, reply_to_msg_id,
                created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                message_data.get('message_id'),
                message_data.get('chat_id'),
                message_data.get('chat_title'),
                message_data.get('chat_type'),
                message_data.get('sender_id'),
                message_data.get('sender_username'),
                message_data.get('sender_first_name'),
                message_data.get('sender_last_name'),
                message_data.get('text'),
                message_data.get('date'),
                message_data.get('media_type'),
                message_data.get('is_forwarded'),
                message_data.get('forward_from'),
                message_data.get('reply_to_msg_id'),
                now
            ))
            
            self.conn.commit()
            last_id = self.cursor.lastrowid
            logger.debug(f"消息保存成功，ID: {last_id}")
            return last_id
        except Exception as e:
            logger.error(f"保存消息失败: {e}")
            return None
    
    def get_message_by_id(self, message_id):
        """
        通过ID获取消息
        
        Args:
            message_id: 消息ID
            
        Returns:
            消息数据字典
        """
        try:
            self.cursor.execute('SELECT * FROM messages WHERE id = ?', (message_id,))
            row = self.cursor.fetchone()
            if row:
                return dict(row)
            return None
        except Exception as e:
            logger.error(f"获取消息失败: {e}")
            return None
    
    def get_messages(self, chat_id=None, sender_id=None, limit=100, offset=0):
        """
        获取消息列表
        
        Args:
            chat_id: 聊天ID，可选
            sender_id: 发送者ID，可选
            limit: 返回条数限制，默认100
            offset: 偏移量，默认0
            
        Returns:
            消息列表
        """
        try:
            conditions = []
            params = []
            
            if chat_id is not None:
                conditions.append('chat_id = ?')
                params.append(chat_id)
            
            if sender_id is not None:
                conditions.append('sender_id = ?')
                params.append(sender_id)
            
            where_clause = ''
            if conditions:
                where_clause = 'WHERE ' + ' AND '.join(conditions)
            
            query = f'''
            SELECT * FROM (
                SELECT * FROM messages 
                {where_clause}
                ORDER BY date DESC
                LIMIT ? OFFSET ?
            )
            ORDER BY date ASC
            '''
            
            params.extend([limit, offset])
            self.cursor.execute(query, tuple(params))
            messages = [dict(row) for row in self.cursor.fetchall()]

            # --- NEW: Fetch content for replied messages ---
            reply_ids = [m['reply_to_msg_id'] for m in messages if m.get('reply_to_msg_id')]
            if reply_ids and chat_id:
                placeholders = ','.join('?' for _ in reply_ids)
                reply_query_params = reply_ids + [chat_id]
                reply_query = f"""
                    SELECT message_id, text, sender_first_name, sender_username, sender_id 
                    FROM messages 
                    WHERE message_id IN ({placeholders}) AND chat_id = ?
                """
                self.cursor.execute(reply_query, reply_query_params)
                replied_messages_rows = self.cursor.fetchall()
                
                replied_map = {row['message_id']: dict(row) for row in replied_messages_rows}
                
                for msg in messages:
                    if msg.get('reply_to_msg_id') in replied_map:
                        original_msg = replied_map[msg['reply_to_msg_id']]
                        sender_name = original_msg.get('sender_first_name') or original_msg.get('sender_username') or f"ID:{original_msg.get('sender_id')}"
                        msg['reply_content'] = {
                            'sender': sender_name,
                            'text': original_msg.get('text', '')
                        }
            # --- END NEW ---
            
            return messages
        except Exception as e:
            logger.error(f"获取消息列表失败: {e}")
            return [] 

    def get_messages_for_today(self, chat_id=None):
        """
        获取指定chat_id或所有聊天今天的消息文本。
        
        Args:
            chat_id (int, optional): 单个chat_id。如果为None，则获取所有消息。
            
        Returns:
            str: 拼接好的所有消息文本。
        """
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            query = """
                SELECT text FROM messages 
                WHERE 
                    date(date) = ? 
                    AND text IS NOT NULL 
                    AND text != ''
                    AND (media_type IS NULL OR media_type != 'MessageMediaUnsupported')
            """
            params = [today]
            
            if chat_id:
                query += " AND chat_id = ?"
                params.append(chat_id)
            
            self.cursor.execute(query, tuple(params))
            
            all_texts = [row['text'] for row in self.cursor.fetchall()]
            return " ".join(all_texts)
            
        except Exception as e:
            logger.error(f"获取今日消息失败 (chat_id: {chat_id}): {e}")
            return ""

    def get_chat_title(self, chat_id):
        """
        根据chat_id获取最新的聊天标题。
        
        Args:
            chat_id (int): 聊天ID。
            
        Returns:
            str: 聊天标题，如果找不到则返回chat_id本身。
        """
        try:
            query = "SELECT chat_title FROM messages WHERE chat_id = ? ORDER BY date DESC LIMIT 1"
            self.cursor.execute(query, (chat_id,))
            row = self.cursor.fetchone()
            return row['chat_title'] if row and row['chat_title'] else str(chat_id)
        except Exception as e:
            logger.error(f"获取聊天标题失败 (chat_id: {chat_id}): {e}")
            return str(chat_id) 