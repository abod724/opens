from database import execute_query, fetch_all, fetch_one, init_db
init_db()

def add_message(user_id, role, content):
    execute_query(
        "INSERT INTO conversations (user_id, role, content) VALUES (%s, %s, %s)",
        (user_id, role, content)
    )
    trim_history(user_id)

def get_history(user_id, limit=10):
    rows = fetch_all(
        "SELECT role, content FROM conversations WHERE user_id = %s ORDER BY created_at DESC LIMIT %s",
        (user_id, limit)
    )
    history = [{"role": row[0], "content": row[1]} for row in rows]
    history.reverse()
    return history

def clear_memory(user_id):
    execute_query("DELETE FROM conversations WHERE user_id = %s", (user_id,))

def trim_history(user_id, max_len=20):
    execute_query("""
        DELETE FROM conversations 
        WHERE user_id = %s 
        AND id NOT IN (
            SELECT id FROM conversations 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT %s
        )
    """, (user_id, user_id, max_len))
