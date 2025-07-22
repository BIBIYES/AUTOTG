#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import datetime
import logging
from colorama import init, Fore, Back, Style
from zoneinfo import ZoneInfo

# 初始化colorama
init(autoreset=True)

logger = logging.getLogger(__name__)

class MessageFormatter:
    """消息格式化类"""
    
    CHAT_TYPE_COLORS = {
        'private': Back.BLUE,
        'group': Back.GREEN,
        'supergroup': Back.MAGENTA,
        'channel': Back.CYAN
    }
    
    @staticmethod
    def format_message_for_console(message_data):
        """
        格式化消息用于控制台显示
        
        Args:
            message_data: 消息数据字典
            
        Returns:
            格式化后的字符串
        """
        try:
            # 获取基础信息
            chat_type = message_data.get('chat_type', 'unknown')
            chat_title = message_data.get('chat_title', 'Unknown')
            sender_name = MessageFormatter._get_sender_name(message_data)
            message_text = message_data.get('text', '')
            date_str = message_data.get('date', '')
            chat_id = message_data.get('chat_id')
            sender_id = message_data.get('sender_id')
            
            # 设置颜色
            chat_color = MessageFormatter.CHAT_TYPE_COLORS.get(chat_type, Back.WHITE) + Fore.BLACK
            
            # 构建消息头
            header = f"{chat_color} {chat_type.upper()} {Style.RESET_ALL} "
            header += f"{Fore.CYAN}{chat_title}{Style.RESET_ALL}"
            
            # 构建发送者信息
            sender_info = f"{Fore.YELLOW}{sender_name}{Style.RESET_ALL}"
            
            # 构建日期信息
            if date_str:
                try:
                    # 将ISO格式字符串（带时区）解析为datetime对象
                    date_obj_utc = datetime.datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    
                    # 定义上海时区
                    shanghai_tz = ZoneInfo("Asia/Shanghai")
                    
                    # 转换为上海本地时间
                    date_obj_local = date_obj_utc.astimezone(shanghai_tz)
                    
                    # 格式化为字符串
                    date_formatted = date_obj_local.strftime('%Y-%m-%d %H:%M:%S')
                    date_info = f"{Fore.GREEN}[{date_formatted}]{Style.RESET_ALL}"
                except Exception as e:
                    logger.warning(f"无法格式化日期 '{date_str}': {e}")
                    date_info = f"{Fore.GREEN}[{date_str}]{Style.RESET_ALL}"
            else:
                date_info = ""
            
            # 构建媒体信息
            media_type = message_data.get('media_type')
            media_info = ""
            if media_type:
                if media_type == "MessageMediaUnsupported":
                    media_info = f"{Fore.RED}[不支持的媒体类型]{Style.RESET_ALL} "
                    if not message_text:
                        message_text = "[不支持的媒体内容]"
                else:
                    media_info = f"{Fore.RED}[{media_type}]{Style.RESET_ALL} "
            
            # 构建转发信息
            forward_info = ""
            if message_data.get('is_forwarded'):
                forward_from = message_data.get('forward_from', 'Unknown')
                forward_info = f"{Fore.BLUE}[转发自: {forward_from}]{Style.RESET_ALL} "
            
            # 构建回复信息
            reply_info = ""
            if message_data.get('reply_to_msg_id'):
                reply_info = f"{Fore.MAGENTA}[回复消息: {message_data.get('reply_to_msg_id')}]{Style.RESET_ALL} "
            
            # 构建完整的消息
            id_info = f"ChatID: {chat_id} | SenderID: {sender_id}"
            message_lines = [
                f"┌─{header}─{date_info}",
                f"│ {sender_info}:",
                f"│ {media_info}{forward_info}{reply_info}{message_text}",
                f"└─[ {id_info} ]{'─' * (33 - len(id_info))}"
            ]
            
            return '\n'.join(message_lines)
            
        except Exception as e:
            logger.error(f"格式化消息失败: {e}")
            return json.dumps(message_data, ensure_ascii=False, indent=2)
    
    @staticmethod
    def _get_sender_name(message_data):
        """获取发送者名称"""
        username = message_data.get('sender_username', '')
        first_name = message_data.get('sender_first_name', '')
        last_name = message_data.get('sender_last_name', '')
        sender_id = message_data.get('sender_id', '')
        
        if username:
            return f"@{username}"
        elif first_name or last_name:
            return f"{first_name} {last_name}".strip()
        else:
            return f"ID:{sender_id}" if sender_id else "Unknown"
    
    @staticmethod
    def extract_message_data(message):
        """
        从Telethon消息对象中提取数据
        
        Args:
            message: Telethon消息对象
            
        Returns:
            消息数据字典
        """
        try:
            # 基本消息数据
            message_data = {
                'message_id': message.id,
                'text': message.text or "",  # 确保text不为None
                'date': message.date.isoformat(),
                # 'raw_data': str(message.to_dict()) # Removed
            }
            
            # 添加聊天信息
            if message.chat:
                chat_id = message.chat.id
                
                # 确定聊天类型
                chat_type = 'private'  # 默认为私聊
                if hasattr(message.chat, 'type'):
                    chat_type = message.chat.type
                elif hasattr(message.chat, 'megagroup') and message.chat.megagroup:
                    chat_type = 'supergroup'
                elif hasattr(message.chat, 'gigagroup') and message.chat.gigagroup:
                    chat_type = 'supergroup'
                elif hasattr(message.chat, 'broadcast') and message.chat.broadcast:
                    chat_type = 'channel'
                elif hasattr(message.chat, 'is_group') and message.chat.is_group:
                    chat_type = 'group'
                
                # 确定聊天标题
                chat_title = None
                if hasattr(message.chat, 'title') and message.chat.title:
                    chat_title = message.chat.title
                elif hasattr(message.chat, 'first_name'):
                    chat_title = message.chat.first_name
                    if hasattr(message.chat, 'last_name') and message.chat.last_name:
                        chat_title += f" {message.chat.last_name}"
                else:
                    chat_title = f"Chat {chat_id}"
                
                message_data.update({
                    'chat_id': chat_id,
                    'chat_title': chat_title,
                    'chat_type': chat_type
                })
            
            # 添加发送者信息
            if message.sender:
                sender = message.sender
                message_data.update({
                    'sender_id': sender.id,
                    'sender_username': getattr(sender, 'username', ''),
                    'sender_first_name': getattr(sender, 'first_name', ''),
                    'sender_last_name': getattr(sender, 'last_name', '')
                })
            
            # 检查媒体类型
            if message.media:
                message_data['media_type'] = message.media.__class__.__name__
                
                # 如果是不支持的媒体，尝试添加描述
                if message.media.__class__.__name__ == "MessageMediaUnsupported":
                    if not message_data['text']:
                        message_data['text'] = "[不支持的媒体内容]"
                
                # 处理其他类型的媒体，尝试获取更多信息
                elif hasattr(message.media, 'photo'):
                    message_data['media_type'] = 'Photo'
                elif hasattr(message.media, 'document'):
                    doc = message.media.document
                    mime_type = getattr(doc, 'mime_type', '')
                    if 'video' in mime_type:
                        message_data['media_type'] = 'Video'
                    elif 'audio' in mime_type or 'voice' in mime_type:
                        message_data['media_type'] = 'Audio'
                    elif 'image' in mime_type:
                        message_data['media_type'] = 'Image'
                    else:
                        file_name = getattr(doc, 'attributes', [{}])[0].file_name if doc.attributes else ''
                        message_data['media_type'] = f'Document{": " + file_name if file_name else ""}'
            else:
                message_data['media_type'] = None
            
            # 检查转发信息
            message_data['is_forwarded'] = message.forward is not None
            if message.forward:
                forward_sender = message.forward.sender
                if forward_sender:
                    forward_name = getattr(forward_sender, 'username', '') or getattr(forward_sender, 'first_name', '') or str(forward_sender.id)
                else:
                    forward_name = "Unknown"
                message_data['forward_from'] = forward_name
            else:
                message_data['forward_from'] = None
            
            # 检查回复信息
            if message.reply_to:
                message_data['reply_to_msg_id'] = message.reply_to.reply_to_msg_id
            else:
                message_data['reply_to_msg_id'] = None
                
            return message_data
        except Exception as e:
            logger.error(f"提取消息数据失败: {e}")
            # 返回基本信息
            return {
                'message_id': getattr(message, 'id', None),
                'text': getattr(message, 'text', ''),
                # 'raw_data': str(message) # Removed
            } 