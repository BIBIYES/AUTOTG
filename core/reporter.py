import logging
import smtplib
import jieba
import os
import io # Import the io module
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from wordcloud import WordCloud

logger = logging.getLogger(__name__)

class DailyReporter:
    def __init__(self, config, db):
        self.report_config = config.get('daily_report', {})
        self.smtp_config = config.get('smtp_settings', {})
        self.db = db
        # 确保词云有中文字体，这里我们假设服务器上存在这个字体文件
        # 在Windows上，它可能是 'C:/Windows/Fonts/simhei.ttf'
        # 在Linux上，可能是 '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc'
        # 我们让它可配置
        self.font_path = self.report_config.get('font_path', 'simhei.ttf') 

    def _generate_wordcloud(self, text):
        """生成词云图片并返回其二进制数据"""
        if not text:
            logger.warning("没有足够的文本来生成词云。")
            return None
        
        try:
            # 使用jieba进行中文分词
            word_list = jieba.lcut(text)
            processed_text = " ".join(word_list)
            
            # 检查字体路径是否存在
            if not os.path.exists(self.font_path):
                 logger.error(f"指定的字体文件不存在: {self.font_path}。词云可能无法正确显示中文。")
                 # 可以在这里回退到默认字体，但中文会是乱码
            
            wordcloud = WordCloud(
                font_path=self.font_path,
                width=1200,
                height=800,
                background_color='white'
            ).generate(processed_text)
            
            # --- NEW: Save image to a memory buffer with a specific format ---
            img_byte_arr = io.BytesIO()
            wordcloud.to_image().save(img_byte_arr, format='PNG')
            img_byte_arr = img_byte_arr.getvalue()
            return img_byte_arr
            # --- END NEW ---
            
        except Exception as e:
            logger.error(f"生成词云失败: {e}")
            return None

    def _send_email(self, image_data):
        """发送包含词云图片的邮件"""
        if not image_data:
            logger.warning("没有词云图片数据，邮件未发送。")
            return

        recipient = self.report_config.get('recipient_email')
        if not recipient:
            logger.error("未配置收件人邮箱，邮件无法发送。")
            return
            
        msg = MIMEMultipart()
        msg['From'] = self.smtp_config.get('username')
        msg['To'] = recipient
        msg['Subject'] = f"Telegram每日词云报告 - {datetime.now().strftime('%Y-%m-%d')}"
        
        # 邮件正文
        msg.attach(MIMEText('您好，\n\n这是今日的Telegram聊天词云报告。\n\n祝好！', 'plain', 'utf-8'))
        
        # 添加图片附件
        image = MIMEImage(image_data, _subtype='png', name='wordcloud.png')
        image.add_header('Content-ID', '<wordcloud_image>')
        msg.attach(image)
        
        try:
            server = smtplib.SMTP(self.smtp_config.get('host'), self.smtp_config.get('port'))
            if self.smtp_config.get('use_tls', True):
                server.starttls()
            server.login(self.smtp_config.get('username'), self.smtp_config.get('password'))
            server.send_message(msg)
            server.quit()
            logger.info(f"每日报告已成功发送到 {recipient}")
        except Exception as e:
            logger.error(f"发送邮件失败: {e}")

    def run_report(self):
        """执行报告生成和发送的完整流程"""
        logger.info("开始生成每日词云报告...")
        chat_ids = self.report_config.get('target_chat_ids')
        text_data = self.db.get_messages_for_today(chat_ids=chat_ids if chat_ids else None)
        
        image_bytes = self._generate_wordcloud(text_data)
        self._send_email(image_bytes)
        logger.info("每日报告任务执行完毕。")

def run_daily_report(config, db):
    """一个独立的函数，用于被调度器调用"""
    reporter = DailyReporter(config, db)
    reporter.run_report() 