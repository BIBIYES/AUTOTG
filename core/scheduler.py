import schedule
import time
import logging
from threading import Thread
from zoneinfo import ZoneInfo
from functools import partial
from core.reporter import run_daily_report

logger = logging.getLogger(__name__)

class ReportScheduler:
    def __init__(self, config, db):
        self.report_config = config.get('daily_report', {})
        self.config = config
        self.db = db
        self.running = False
        self.thread = None

    def _schedule_job(self):
        """设置调度任务"""
        if not self.report_config.get('enabled', False):
            logger.info("每日报告功能已禁用。")
            return
            
        schedule_time_str = self.report_config.get('schedule_time', '23:00')
        timezone_str = self.report_config.get('timezone', 'UTC')
        
        try:
            # 使用正确的时区来调度
            tz = ZoneInfo(timezone_str)
            logger.info(f"每日报告已计划在每天 {schedule_time_str} ({timezone_str}) 执行。")
            
            # 创建一个偏函数，将config和db对象绑定到任务函数上
            job_func = partial(run_daily_report, self.config, self.db)
            
            # 设置定时任务
            schedule.every().day.at(schedule_time_str, tz).do(job_func)
            
        except Exception as e:
            logger.error(f"设置定时报告任务失败: {e}")
            
    def _run_pending(self):
        """在一个循环中运行所有待定的调度任务"""
        self.running = True
        logger.info("报告调度器已启动。")
        while self.running:
            schedule.run_pending()
            time.sleep(1)
        logger.info("报告调度器已停止。")

    def start(self):
        """在后台线程中启动调度器"""
        self._schedule_job()
        self.thread = Thread(target=self._run_pending, daemon=True)
        self.thread.start()

    def stop(self):
        """停止调度器"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=5) 