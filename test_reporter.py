import logging
import sys
import os

# 将项目根目录添加到Python路径中
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.config import Config
from core.database import Database
from core.reporter import run_daily_report

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """
    一个用于立即触发每日报告功能的测试脚本。
    """
    logger.info("--- 开始执行词云报告测试 ---")
    
    # 加载配置
    config = Config('config.json')
    if not config.config:
        logger.error("无法加载配置文件 config.json，测试中止。")
        return
        
    # 初始化数据库
    db = Database('data.db')
    
    # 直接调用报告生成和发送的核心函数
    try:
        run_daily_report(config, db)
    except Exception as e:
        logger.error(f"测试过程中发生未处理的异常: {e}", exc_info=True)
    finally:
        # 关闭数据库连接
        db.close()
        logger.info("--- 词云报告测试执行完毕 ---")

if __name__ == "__main__":
    main() 