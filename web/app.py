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
        offset = request.args.get('offset', 0, type=int)
        limit = request.args.get('limit', 50, type=int)
        
        messages = database.get_messages(chat_id=session_id, limit=limit, offset=offset)
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
        # 使用北京时间 (UTC+8)，并以 created_at 为基准
        database.cursor.execute("""
            SELECT date(created_at, '+8 hours') as day, COUNT(*) as count
            FROM messages
            WHERE date(created_at, '+8 hours') >= date('now', '-7 days', '+8 hours')
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
        # 使用北京时间 (UTC+8)，并以 created_at 为基准
        database.cursor.execute("""
            SELECT sender_id, sender_username, sender_first_name, COUNT(*) as count
            FROM messages
            WHERE date(created_at, '+8 hours') >= date('now', '-7 days', '+8 hours') AND sender_id IS NOT NULL
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

@app.route('/api/stats/group_ranking', methods=['GET'])
def group_ranking():
    """获取过去7天群组消息量排行"""
    try:
        database = get_db()
        # 筛选出群组/频道类型的消息 (chat_id通常是负数)
        # 并按消息数量排序
        # 使用北京时间 (UTC+8)，并以 created_at 为基准
        query = """
            SELECT
                chat_id,
                chat_title,
                COUNT(*) as count
            FROM messages
            WHERE
                date(created_at, '+8 hours') >= date('now', '-7 days', '+8 hours')
                AND (chat_type = 'group' OR chat_type = 'supergroup' OR chat_type = 'channel')
            GROUP BY chat_id, chat_title
            ORDER BY count DESC
            LIMIT 10
        """
        database.cursor.execute(query)
        ranking = [{'name': row['chat_title'], 'count': row['count']} for row in database.cursor.fetchall()]
        return jsonify(ranking)
    except Exception as e:
        logging.error(f"获取群组消息量排行失败: {e}")
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

@app.route('/api/stats/activity_heatmap', methods=['GET'])
def activity_heatmap():
    """获取过去14天的每小时活跃度数据，用于生成热力图"""
    try:
        database = get_db()
        # 使用北京时间 (UTC+8)，并以 created_at 为基准
        query = """
            WITH RECURSIVE 
            date_series AS (
            SELECT DATE('now', '-13 days', '+8 hours') as date_val
            UNION ALL
            SELECT DATE(date_val, '+1 day')
            FROM date_series
            WHERE date_val < DATE('now', '+8 hours')
            ),
            hour_series AS (
            SELECT 0 as hour_val
            UNION ALL
            SELECT hour_val + 1
            FROM hour_series
            WHERE hour_val < 23
            ),
            date_hour_matrix AS (
            SELECT 
                d.date_val,
                h.hour_val,
                CASE STRFTIME('%w', d.date_val)
                WHEN '0' THEN '周日'
                WHEN '1' THEN '周一'
                WHEN '2' THEN '周二'
                WHEN '3' THEN '周三'
                WHEN '4' THEN '周四'
                WHEN '5' THEN '周五'
                WHEN '6' THEN '周六'
                END as weekday_name
            FROM date_series d
            CROSS JOIN hour_series h
            )
            SELECT 
            dhm.date_val as date,
            dhm.hour_val as hour,
            dhm.weekday_name,
            COALESCE(COUNT(m.id), 0) as message_count
            FROM date_hour_matrix dhm
            LEFT JOIN messages m ON 
            DATE(m.created_at, '+8 hours') = dhm.date_val 
            AND CAST(STRFTIME('%H', m.created_at, '+8 hours') AS INTEGER) = dhm.hour_val
            GROUP BY dhm.date_val, dhm.hour_val, dhm.weekday_name
            ORDER BY dhm.date_val, dhm.hour_val;
        """
        database.cursor.execute(query)
        
        # 将数据处理成 [day, hour, count] 的格式
        # ECharts热力图需要这种格式
        heatmap_data = []
        for row in database.cursor.fetchall():
            heatmap_data.append([row['date'], int(row['hour']), row['message_count'], row['weekday_name']])
            
        return jsonify(heatmap_data)
    except Exception as e:
        logging.error(f"获取活跃度热力图数据失败: {e}")
        return jsonify({"error": str(e)}), 500

def run_web_app():
    """在eventlet服务器中运行Flask应用"""
    logging.info("启动Web服务器于 http://0.0.0.0:5000")
    # 使用eventlet作为WebSocket服务器，并禁用 werkzeug 的 reloader
    socketio.run(app, host='0.0.0.0', port=5000, use_reloader=False)

if __name__ == '__main__':
    run_web_app() 