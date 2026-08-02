from flask_login import UserMixin
from database import fetch_one, execute_query
import bcrypt

class User(UserMixin):
    def __init__(self, id, email, name):
        self.id = id
        self.email = email
        self.name = name

def get_user_by_id(user_id):
    row = fetch_one("SELECT id, email, name FROM users WHERE id = %s", (user_id,))
    if row:
        return User(row[0], row[1], row[2])
    return None

def get_user_by_email(email):
    row = fetch_one("SELECT id, email, name FROM users WHERE email = %s", (email,))
    if row:
        return User(row[0], row[1], row[2])
    return None

def create_user(email, password, name):
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    execute_query(
        "INSERT INTO users (email, password_hash, name) VALUES (%s, %s, %s)",
        (email, password_hash, name)
    )

def check_password(email, password):
    row = fetch_one("SELECT password_hash FROM users WHERE email = %s", (email,))
    if row:
        return bcrypt.checkpw(password.encode('utf-8'), row[0].encode('utf-8'))
    return False
