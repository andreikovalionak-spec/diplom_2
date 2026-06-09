import streamlit as st
import psycopg2
import pandas as pd
import random

# ============================================================
# НАСТРОЙКА СТРАНИЦЫ
# ============================================================
st.set_page_config(
    page_title="EnglishCard - Изучение английского",
    page_icon="📚",
    layout="wide"
)


# РАБОТА С БАЗОЙ ДАННЫХ


def get_db_connection():
    """Подключение к PostgreSQL"""
    conn = psycopg2.connect(
        host="localhost",
        database="englishcard_2",
        user="postgres",
        password="2409"
    )
    return conn

def init_database():
    """Создание таблиц и заполнение начальными данными"""
    conn = get_db_connection()
    cur = conn.cursor()

    # Таблица пользователей
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Таблица общих слов
    cur.execute("""
        CREATE TABLE IF NOT EXISTS common_words (
            id SERIAL PRIMARY KEY,
            russian_word VARCHAR(255) NOT NULL,
            english_word VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Таблица персональных слов пользователя
    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_words (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            russian_word VARCHAR(255) NOT NULL,
            english_word VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, english_word)
        );
    """)

    # Таблица статистики обучения
    cur.execute("""
        CREATE TABLE IF NOT EXISTS learning_stats (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            word_id INTEGER NOT NULL,
            word_type VARCHAR(10) NOT NULL,  -- 'common' или 'personal'
            correct_answers INTEGER DEFAULT 0,
            total_attempts INTEGER DEFAULT 0,
            last_reviewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Заполнение common_words начальными словами
    initial_words = [
        ('красный', 'red'),
        ('синий', 'blue'),
        ('зелёный', 'green'),
        ('жёлтый', 'yellow'),
        ('чёрный', 'black'),
        ('белый', 'white'),
        ('дом', 'house'),
        ('книга', 'book'),
        ('яблоко', 'apple'),
        ('вода', 'water'),
        ('кошка', 'cat'),
        ('собака', 'dog')
    ]

    cur.execute("SELECT COUNT(*) FROM common_words")
    count = cur.fetchone()[0]
    if count == 0:
        insert_query = "INSERT INTO common_words (russian_word, english_word) VALUES (%s, %s)"
        cur.executemany(insert_query, initial_words)

    conn.commit()
    cur.close()
    conn.close()

def login_user(username):
    """Авторизация пользователя"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT id FROM users WHERE username = %s", (username,))
        result = cur.fetchone()
        if result:
            user_id = result[0]
        else:
            cur.execute(
                "INSERT INTO users (username) VALUES (%s) RETURNING id",
                (username,)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
        return user_id
    except Exception as e:
        st.error(f"Ошибка при авторизации: {e}")
        return None
    finally:
        cur.close()
        conn.close()

def get_user_words(user_id):
    """Получить все слова пользователя (общие + персональные)"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        query = """
        SELECT
            cw.id,
            cw.russian_word,
            cw.english_word,
            'common' as word_type
        FROM common_words cw
        UNION ALL
        SELECT
            uw.id,
            uw.russian_word,
            uw.english_word,
            'personal' as word_type
        FROM user_words uw
        WHERE uw.user_id = %s
        """
        cur.execute(query, (user_id,))
        rows = cur.fetchall()
        words = []
        for row in rows:
            words.append({
                'id': row[0],
                'russian_word': row[1],
                'english_word': row[2],
                'word_type': row[3]
            })
        return words
    except Exception as e:
        st.error(f"Ошибка при получении слов: {e}")
        return []
    finally:
        cur.close()
        conn.close()

def add_personal_word(user_id, russian_word, english_word):
    """Добавить персональное слово для пользователя"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        # Проверяем, нет ли уже такого слова
        cur.execute(
            "SELECT id FROM user_words WHERE user_id = %s AND english_word = %s",
            (user_id, english_word)
        )
        if cur.fetchone():
            return False

        cur.execute(
            "INSERT INTO user_words (user_id, russian_word, english_word) VALUES (%s, %s, %s)",
            (user_id, russian_word, english_word)
        )
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Ошибка при добавлении слова: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def delete_personal_word(user_id, word_id):
    """Удалить персональное слово пользователя"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            "DELETE FROM user_words WHERE id = %s AND user_id = %s",
            (word_id, user_id)
        )
        deleted = cur.rowcount > 0
        conn.commit()
        return deleted
    except Exception as e:
        st.error(f"Ошибка при удалении слова: {e}")
        return False
    finally:
        cur.close()
        conn.close()

def update_stats(user_id, word_id, word_type, is_correct):
    """Обновить статистику изучения слова"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO learning_stats (user_id, word_id, word_type, correct_answers, total_attempts, last_reviewed)
            VALUES (%s, %s, %s, %s, 1, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, word_id, word_type)
            DO UPDATE SET
                correct_answers = learning_stats.correct_answers + %s,
                total_attempts = learning_stats.total_attempts + 1,
                last_reviewed = CURRENT_TIMESTAMP
        """, (user_id, word_id, word_type, int(is_correct), int(is_correct)))
        conn.commit()
    except Exception as e:
        st.error(f"Ошибка при обновлении статистики: {e}")
    finally:
        cur.close()
        conn.close()

def get_statistics(user_id):
    """Получить статистику пользователя"""
    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT
                SUM(correct_answers) as total_correct,
                SUM(total_attempts) as total_attempts
            FROM learning_stats
            WHERE user_id = %s
        """, (user_id,))
        result = cur.fetchone()

        if result and result[1] > 0:
            accuracy = (result[0] / result[1]) * 100
        else:
            accuracy = 0

        return {
            'total_correct': result[0] if result else 0,
            'total_attempts': result[1] if result else 0,
            'accuracy': round(accuracy, 2)
        }
    except Exception as e:
        st.error(f"Ошибка при получении статистики: {e}")
        return {'total_correct': 0, 'total_attempts': 0, 'accuracy': 0}
    finally:
        cur.close()
        conn.close()

