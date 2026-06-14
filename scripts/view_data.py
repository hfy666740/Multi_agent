"""查看数据库中的聊天记录
命令行工具：查看数据库中的会话和消息记录"""
import psycopg2
from psycopg2.extras import RealDictCursor

DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'postgres',
    'password': '123456',
    'database': 'agent_chat'
}

def view_data():
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    print("="*60)
    print("所有会话")
    print("="*60)
    cursor.execute("SELECT * FROM chat_sessions ORDER BY created_at DESC")
    sessions = cursor.fetchall()
    for s in sessions:
        print(f"会话ID: {s['session_id'][:20]}...")
        print(f"  创建时间: {s['created_at']}")
        print(f"  更新时间: {s['updated_at']}")
        print()
    
    print("="*60)
    print("所有消息")
    print("="*60)
    cursor.execute("SELECT * FROM chat_messages ORDER BY created_at DESC")
    messages = cursor.fetchall()
    for m in messages:
        content = m['content'][:50]
        print(f"[{m['created_at']}] {m['role']}: {content}...")
    
    cursor.close()
    conn.close()

if __name__ == '__main__':
    view_data()