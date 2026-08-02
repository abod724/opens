class ConversationMemory:
    def __init__(self, max_history=20):
        self.max_history = max_history
        self.messages = []

    def add_message(self, role, content):
        self.messages.append({"role": role, "content": content})
        if len(self.messages) > self.max_history:
            self.messages = self.messages[-self.max_history:]

    def get_context(self):
        return self.messages

    def get_last_n_messages(self, n):
        return self.messages[-n:] if n > 0 else []

    def load_from_db(self, db_connection, session_id):
        history = db_connection.fetch_history(session_id)
        self.messages = history[-self.max_history:] if history else []

    def save_to_db(self, db_connection, session_id):
        db_connection.save_messages(session_id, self.messages)

    def clear(self):
        self.messages = []
