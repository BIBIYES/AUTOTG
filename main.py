#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
import argparse
import os
import sys
import signal
from threading import Thread
import time # Added for the new_code

# 将web目录添加到路径，以便导入app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'web'))

from core.Tgbot import Tgbot
from core.config import Config
from core.database import Database
from core.formatter import MessageFormatter
from web.app import app, socketio # 导入Flask app和socketio实例
from core.scheduler import ReportScheduler # 导入调度器

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 全局bot实例
bot = None

def signal_handler(sig, frame):
    """处理信号中断"""
    print("\n正在退出程序...")
    if bot:
        bot.stop()
    # scheduler is handled by daemon thread, no need to stop explicitly
    sys.exit(0)

def run_web_app():
    """在eventlet服务器中运行Flask应用"""
    logger.info("启动Web服务器于 http://0.0.0.0:5000")
    # 明确禁用reloader以避免在生产环境中（如systemd服务）出现Werkzeug错误
    socketio.run(app, host='0.0.0.0', port=5000, use_reloader=False)

def main():
    global bot
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    
    # 命令行参数解析
    parser = argparse.ArgumentParser(description='Telegram账户数据管理和采集工具')
    parser.add_argument('-c', '--config', default='config.json', help='配置文件路径')
    parser.add_argument('-d', '--db', default='data.db', help='数据库文件路径')
    parser.add_argument('--no-listen', action='store_true', help='登录后不监听消息')
    args = parser.parse_args()
    
    # 加载配置
    config_path = args.config
    if not os.path.exists(config_path):
        logger.warning(f"配置文件 {config_path} 不存在，将创建一个默认配置")
    
    config = Config(config_path)
    
    # 检查必要的配置
    api_id = config.get('api_id')
    api_hash = config.get('api_hash')
    
    if not api_id or not api_hash:
        logger.error("配置文件中缺少必要的API凭据")
        logger.info("请在配置文件中设置api_id和api_hash")
        return
    
    # 初始化数据库
    db = Database(args.db)
    
    # 创建Tgbot实例
    bot = Tgbot(config)
    
    # 设置依赖
    bot.set_database(db)
    bot.set_message_formatter(MessageFormatter)
    bot.set_socketio(socketio) # 将socketio实例传递给bot
    
    # 初始化并启动报告调度器
    scheduler = ReportScheduler(config, db)
    scheduler.start()

    # 登录
    if bot.login():
        logger.info("登录成功！")
        
        # 在新线程中启动Web服务器
        web_thread = Thread(target=run_web_app)
        web_thread.daemon = True
        web_thread.start()

        # 主线程中开始监听消息
        if not args.no_listen:
            logger.info("开始监听消息和存储数据...")
            logger.info("按 Ctrl+C 停止运行")
            bot.start()
        else:
            logger.info("消息监听已禁用。Web服务和调度器正在运行，请按 Ctrl+C 退出。")
            # 如果不监听，则等待web线程结束
            try:
                while True:
                    time.sleep(60)
            except KeyboardInterrupt:
                signal_handler(signal.SIGINT, None)
    else:
        logger.error("登录失败！")
    
    # 关闭数据库连接
    db.close()

if __name__ == "__main__":
    main() 