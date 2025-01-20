import streamlit as st
import pandas as pd
import sqlite3

# Conexão com o banco de dados SQLite
DATABASE_FILE = "database.db"
def get_connection():
    return sqlite3.connect(DATABASE_FILE)

def initialize_database():
    """Cria as tabelas necessárias no banco de dados SQLite."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS streamlitapp2 (
        useremail TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS thread_save (
        useremail TEXT,
        thread_key TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS message_limit (
        useremail TEXT,
        counter INTEGER DEFAULT 0
    )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            useremail TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

def authenticate_user(useremail: str):
    try:
        return get_data(useremail=useremail)
    except:
        return False

def input_data(useremail: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO streamlitapp2 (useremail) VALUES (?)",
            (useremail,),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error occurred while inserting data: {e}")
        return False

def get_data(useremail: str) -> bool:
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM streamlitapp2 WHERE useremail = ?",
            (useremail,),
        )
        result = cursor.fetchall()
        conn.close()
        return len(result) > 0
    except Exception as e:
        print(f"Error occurred while fetching data: {e}")
        return False

def get_thread_key(useremail: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT thread_key FROM thread_save WHERE useremail = ?",
            (useremail,),
        )
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        print(f"Error occurred while fetching thread key: {e}")
        return None

def put_thread_key(useremail: str, thread_key: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO thread_save (useremail, thread_key) VALUES (?, ?)",
            (useremail, thread_key),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error occurred while inserting thread key: {e}")
        return False

def get_limit_message(useremail: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT counter FROM message_limit WHERE useremail = ?",
        (useremail,),
    )
    result = cursor.fetchone()

    if result:
        is_below_limit = result[0] < 20
        conn.close()
        return is_below_limit, result[0]
    else:
        conn.close()
        return False, 0

def set_initial_limit(useremail: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO message_limit (useremail, counter) VALUES (?, 0)",
            (useremail,),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"An error occurred: {e}")
        return False

def update_limit_counter(useremail: str, new_counter: int):
    if new_counter < 20:
        try:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE message_limit SET counter = ? WHERE useremail = ?",
                (new_counter, useremail),
            )
            conn.commit()
            conn.close()
            return new_counter
        except Exception as e:
            print(f"Error occurred while updating counter: {e}")
            return "Error occurred while updating counter"
    else:
        return "Limit reached!"
def save_message(useremail, role, content):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO messages (useremail, role, content) VALUES (?, ?, ?)
    """, (useremail, role, content))
    conn.commit()
    conn.close()

def load_messages(useremail):
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT role, content FROM messages WHERE useremail = ? ORDER BY timestamp ASC
    """, (useremail,))
    messages = cursor.fetchall()
    conn.close()
    return [{"role": role, "content": content} for role, content in messages]
# Inicializa o banco de dados
initialize_database()
