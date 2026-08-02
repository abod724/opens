session_memory = {}

def get_memory(user_id):
    if user_id not in session_memory:
        session_memory[user_id] = []
    return session_memory[user_id]

def add_message(user_id, role, content):
    if user_id not in session_memory:
        session_memory[user_id] = []
    session_memory[user_id].append({"role": role, "content": content})
    if len(session_memory[user_id]) > 20:
        session_memory[user_id] = session_memory[user_id][-20:]

def get_history(user_id, limit=10):
    if user_id not in session_memory:
        return []
    return session_memory[user_id][-limit:]

def clear_memory(user_id):
    if user_id in session_memory:
        session_memory[user_id] = []

def get_all_memories():
    return session_memory

def get_session_count():
    return len(session_memory)
