#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import asyncio
import json
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError
from colorama import Fore, Style

logger = logging.getLogger(__name__)

class Tgbot:
    def __init__(self, config):
        """
        初始化Tgbot
        
        Args:
            config: 配置对象
        """
        self.config = config
        self.api_id = config.get('api_id')
        self.api_hash = config.get('api_hash')
        self.session_name = config.get('session_name', 'autotg_session')
        self.client = None
        self.db = None
        self.message_formatter = None
        self.running = False
        self.socketio = None
        # Load filter lists from config
        self.filter_chat_ids = config.get('filter_chat_ids', [])
        self.filter_sender_ids = config.get('filter_sender_ids', [])
        
        # 设置日志级别
        log_level = config.get('log_level', 'INFO')
        numeric_level = getattr(logging, log_level.upper(), None)
        if isinstance(numeric_level, int):
            logging.getLogger().setLevel(numeric_level)
    
    def set_database(self, db):
        """设置数据库实例"""
        self.db = db
    
    def set_message_formatter(self, formatter):
        """设置消息格式化器"""
        self.message_formatter = formatter
    
    def set_socketio(self, socketio): # Add this method
        """设置SocketIO实例"""
        self.socketio = socketio
    
    async def _login_async(self):
        """异步登录方法"""
        try:
            # 检查是否使用代理
            proxy_config = self.config.get('proxy', {})
            proxy = None
            
            if proxy_config.get('enabled', False):
                proxy_type = proxy_config.get('type', 'socks5')
                proxy = (
                    proxy_type, 
                    proxy_config.get('addr', '127.0.0.1'), 
                    proxy_config.get('port', 1080),
                    proxy_config.get('username', None) or None,
                    proxy_config.get('password', None) or None
                )
                logger.info(f"使用代理: {proxy_type}://{proxy_config.get('addr')}:{proxy_config.get('port')}")
            
            # 创建客户端
            self.client = TelegramClient(
                self.session_name, 
                self.api_id, 
                self.api_hash,
                proxy=proxy
            )
            
            # 连接到Telegram
            await self.client.connect()
            
            # 检查是否已经授权
            if not await self.client.is_user_authorized():
                logger.info("需要进行登录授权...")
                
                # 发送验证码
                phone = input("请输入您的手机号码 (带国家代码，例如: +86xxxxxxxxxxx): ")
                await self.client.send_code_request(phone)
                
                # 请求用户输入验证码
                code = input("请输入收到的验证码: ")
                try:
                    await self.client.sign_in(phone, code)
                except SessionPasswordNeededError:
                    # 如果启用了两步验证
                    password = input("请输入您的两步验证密码: ")
                    await self.client.sign_in(password=password)
            
            # 获取并显示当前账户信息
            me = await self.client.get_me()
            logger.info(f"登录成功! 用户ID: {me.id}, 用户名: {me.username}")
            return True
            
        except Exception as e:
            logger.error(f"登录失败: {e}")
            return False
    
    def login(self):
        """
        登录Telegram账户
        
        Returns:
            bool: 登录是否成功
        """
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(self._login_async())
    
    def logout(self):
        """登出当前账户"""
        if self.client:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self.client.log_out())
            return True
        return False
    
    async def _setup_handlers(self):
        """设置消息处理器"""
        @self.client.on(events.NewMessage)
        async def on_new_message(event):
            """处理新消息"""
            try:
                message = event.message
                
                # --- NEW: Filtering Logic ---
                if message.chat_id in self.filter_chat_ids:
                    logger.info(f"消息来自被过滤的群组 {message.chat_id}，已忽略。")
                    return
                if message.sender_id in self.filter_sender_ids:
                    logger.info(f"消息来自被过滤的用户 {message.sender_id}，已忽略。")
                    return
                # --- END NEW ---
                
                # 提取消息数据
                if self.message_formatter:
                    message_data = self.message_formatter.extract_message_data(message)
                    
                    # 格式化并打印消息
                    formatted_message = self.message_formatter.format_message_for_console(message_data)
                    print(formatted_message)
                    
                    # 异步保存到数据库，避免阻塞
                    if self.db:
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, self.db.save_message, message_data)
                    
                    # 通过WebSocket发送到前端
                    if self.socketio:
                        self.socketio.emit('new_message', message_data)
                
            except Exception as e:
                logger.error(f"处理新消息时出错: {e}")
        
        @self.client.on(events.MessageEdited)
        async def on_message_edited(event):
            """处理消息编辑"""
            try:
                message = event.message
                
                # 提取消息数据
                if self.message_formatter:
                    message_data = self.message_formatter.extract_message_data(message)
                    message_data['is_edited'] = True
                    
                    # 格式化并打印消息
                    print(f"\n{Fore.RED}【消息已编辑】{Style.RESET_ALL}")
                    formatted_message = self.message_formatter.format_message_for_console(message_data)
                    print(formatted_message)
                    
                    # 异步保存到数据库
                    if self.db:
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(None, self.db.save_message, message_data)
                
            except Exception as e:
                logger.error(f"处理编辑消息时出错: {e}")
        
        logger.info("消息处理器已设置")
    
    async def _start_listening(self):
        """开始监听消息"""
        try:
            # 设置消息处理器
            await self._setup_handlers()
            
            # 设置标志
            self.running = True
            
            logger.info("开始监听消息...")
            
            # 保持运行
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("接收到键盘中断，停止监听...")
            self.running = False
        except Exception as e:
            logger.error(f"监听消息时出错: {e}")
            self.running = False
    
    def start(self):
        """
        开始监听消息
        
        Returns:
            bool: 是否成功启动
        """
        try:
            # 检查是否已登录
            if not self.client:
                logger.error("尚未登录，请先调用login方法")
                return False
            
            # 检查数据库
            if not self.db:
                logger.warning("未设置数据库，消息将不会被保存")
            
            # 检查消息格式化器
            if not self.message_formatter:
                from core.formatter import MessageFormatter
                self.message_formatter = MessageFormatter
                logger.info("使用默认消息格式化器")
            
            # 启动监听
            loop = asyncio.get_event_loop()
            logger.info("启动消息监听...")
            loop.run_until_complete(self._start_listening())
            
            return True
        except Exception as e:
            logger.error(f"启动监听失败: {e}")
            return False
    
    def stop(self):
        """停止监听消息"""
        self.running = False
        logger.info("停止监听消息...")
        return True 