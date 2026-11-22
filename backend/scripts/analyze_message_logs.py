"""Script phân tích dữ liệu thực tế cho trang Nhật ký tin nhắn."""
import os, sys
sys.path.append('.')
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
load_dotenv('backend/.env')

db_url = os.getenv('DATABASE_URL')
engine = create_engine(db_url)
with engine.connect() as conn:
    res = conn.execute(text("""
        SELECT 
            m.id as msg_id,
            m.content as student_question,
            m.created_at as msg_time,
            u.username as student_name,
            u.email as student_email,
            u.grade,
            s.id as session_id,
            ol.target_agent,
            ol.reason as routing_reason,
            ol.notify_parent,
            ol.id as log_id
        FROM messages m
        JOIN sessions s ON m.session_id = s.id
        JOIN users u ON s.user_id = u.id
        LEFT JOIN orchestrator_logs ol ON ol.session_id = s.id AND ol.user_query = m.content
        WHERE m.sender_type = 'USER'
        ORDER BY m.created_at DESC
        LIMIT 20
    """))
    print('=== Full join (20 rows) ===')
    for r in res:
        print(r)

    cnt = conn.execute(text("SELECT COUNT(*) as cnt FROM messages WHERE sender_type = 'USER'"))
    print('\nTotal USER messages:', cnt.scalar())

    cnt2 = conn.execute(text("SELECT COUNT(*) as cnt FROM orchestrator_logs"))
    print('Total orchestrator_logs:', cnt2.scalar())

    cnt3 = conn.execute(text("SELECT target_agent, COUNT(*) as cnt FROM orchestrator_logs GROUP BY target_agent ORDER BY cnt DESC"))
    print('Agent distribution:')
    for r in cnt3: print(r)

    # Sessions count
    cnt4 = conn.execute(text("SELECT COUNT(DISTINCT session_id) FROM messages WHERE sender_type = 'USER'"))
    print('\nDistinct sessions with messages:', cnt4.scalar())

