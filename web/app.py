import sys
import os
import logging
from flask import Flask, jsonify, request, render_template
from flask_socketio import SocketIO
from threading import Thread

# 将项目根目录添加到Python路径中，以便能够导入core模块
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.database import Database

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
# 设置异步模式为 'threading' 以获得更好的兼容性
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

# 全局数据库实例
db = None

def get_db():
    """获取数据库连接"""
    global db
    if db is None:
        # 假设数据库文件在项目根目录
        db_path = os.path.join(os.path.dirname(app.root_path), 'data.db')
        db = Database(db_file=db_path)
    return db

@app.route('/')
def index():
    """渲染主页面"""
    return render_template('index.html')

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """获取所有会话列表（群组/用户）"""
    try:
        database = get_db()
        # 通过查询数据库中所有不同的chat_id和chat_title来获取会话
        database.cursor.execute("SELECT DISTINCT chat_id, chat_title FROM messages ORDER BY chat_title")
        sessions = [{'id': row['chat_id'], 'title': row['chat_title']} for row in database.cursor.fetchall()]
        return jsonify(sessions)
    except Exception as e:
        logging.error(f"获取会话列表失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/messages/<int:session_id>', methods=['GET'])
def get_messages(session_id):
    """根据会话ID获取消息"""
    try:
        database = get_db()
        messages = database.get_messages(chat_id=session_id, limit=200) # 最近200条
        return jsonify(messages)
    except Exception as e:
        logging.error(f"获取消息失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_messages():
    """全局搜索消息"""
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400
    
    try:
        database = get_db()
        database.cursor.execute(
            "SELECT * FROM messages WHERE text LIKE ? ORDER BY date DESC LIMIT 100",
            (f'%{query}%',)
        )
        results = [dict(row) for row in database.cursor.fetchall()]
        return jsonify(results)
    except Exception as e:
        logging.error(f"搜索消息失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats/daily_frequency', methods=['GET'])
def daily_frequency():
    """获取过去7天的每日消息频率"""
    try:
        database = get_db()
        database.cursor.execute("""
            SELECT date(date) as day, COUNT(*) as count
            FROM messages
            WHERE date >= date('now', '-7 days')
            GROUP BY day
            ORDER BY day
        """)
        stats = [{'day': row['day'], 'count': row['count']} for row in database.cursor.fetchall()]
        return jsonify(stats)
    except Exception as e:
        logging.error(f"获取每日消息频率失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats/user_ranking', methods=['GET'])
def user_ranking():
    """获取过去7天用户发言排行"""
    try:
        database = get_db()
        database.cursor.execute("""
            SELECT sender_id, sender_username, sender_first_name, COUNT(*) as count
            FROM messages
            WHERE date >= date('now', '-7 days') AND sender_id IS NOT NULL
            GROUP BY sender_id
            ORDER BY count DESC
            LIMIT 10
        """)
        ranking = []
        for row in database.cursor.fetchall():
            name = row['sender_username'] or row['sender_first_name'] or f"ID: {row['sender_id']}"
            ranking.append({'name': name, 'count': row['count']})
        return jsonify(ranking)
    except Exception as e:
        logging.error(f"获取用户发言排行失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats/message_type_distribution', methods=['GET'])
def message_type_distribution():
    """获取消息类型分布"""
    try:
        database = get_db()
        # 将空或None的media_type视为'文本消息'
        query = """
            SELECT
                CASE
                    WHEN media_type IS NULL THEN '文本消息'
                    WHEN media_type = '' THEN '文本消息'
                    ELSE media_type
                END as type,
                COUNT(*) as value
            FROM messages
            GROUP BY type
            ORDER BY value DESC
        """
        database.cursor.execute(query)
        stats = [{'name': row['type'], 'value': row['value']} for row in database.cursor.fetchall()]
        return jsonify(stats)
    except Exception as e:
        logging.error(f"获取消息类型分布失败: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stats/hourly_activity', methods=['GET'])
def hourly_activity():
    """获取24小时活跃度"""
    try:
        database = get_db()
        # 提取小时并分组计数
        query = """
            SELECT
                strftime('%H', date) as hour,
                COUNT(*) as count
            FROM messages
            GROUP BY hour
            ORDER BY hour
        """
        database.cursor.execute(query)
        # 创建一个包含所有24小时的字典
        hourly_data = {f"{h:02d}": 0 for h in range(24)}
        for row in database.cursor.fetchall():
            hourly_data[row['hour']] = row['count']
        
        # 转换为ECharts需要的格式
        stats = [{'hour': h, 'count': c} for h, c in hourly_data.items()]
        return jsonify(stats)
    except Exception as e:
        logging.error(f"获取24小时活跃度失败: {e}")
        return jsonify({"error": str(e)}), 500

def run_web_app():
    """在eventlet服务器中运行Flask应用"""
    logging.info("启动Web服务器...")
    # 使用eventlet作为WebSocket服务器
    socketio.run(app, host='0.0.0.0', port=5000)

if __name__ == '__main__':
    run_web_app() 