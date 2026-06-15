import streamlit as st
import psycopg2
import pandas as pd
import random

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(
    page_title="EnglishCard - Learning English",
    page_icon="📚",
    layout="wide"
)


# ============================================================
# DATABASE FUNCTIONS (unchanged)
# ============================================================

def get_db_connection():
    """Establish connection to PostgreSQL"""
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


# ============================================================
# USER INTERFACE
# ============================================================

# Инициализация базы данных при запуске
init_database()

# Боковая панель для навигации
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Choose a section:",
    ["Login", "Add Words", "Study Words", "My Words", "Statistics", "Delete Words"]
)

# Страница авторизации
if page == "Login":
    st.title("Welcome to EnglishCard!")
    st.subheader("Please log in or create an account")

    username = st.text_input("Enter your username:")
    if st.button("Login / Register"):
        if username:
            user_id = login_user(username)
            if user_id:
                st.session_state.user_id = user_id
                st.success(f"Welcome, {username}! User ID: {user_id}")
                st.balloons()
            else:
                st.error("Login failed. Please try again.")
        else:
            st.warning("Please enter a username.")

# Страница добавления слов
elif page == "Add Words":
    if 'user_id' not in st.session_state:
        st.warning("Please log in first!")
    else:
        st.title("Add Personal Words")
        st.subheader("Enter new words to learn")

        col1, col2 = st.columns(2)
        with col1:
            russian_word = st.text_input("Russian word:")
        with col2:
            english_word = st.text_input("English word:")

        if st.button("Add Word"):
            if russian_word and english_word:
                success = add_personal_word(st.session_state.user_id, russian_word, english_word)
                if success:
                    st.success("Word added successfully!")
                else:
                    st.error("This word already exists in your personal list.")
            else:
                st.warning("Please fill in both fields.")

# Страница изучения слов (квиз)
elif page == "Study Words":
    if 'user_id' not in st.session_state:
        st.warning("Please log in first!")
    else:
        st.title("Study Words")
        st.subheader("Test your knowledge!")

        words = get_user_words(st.session_state.user_id)
        if not words:
            st.info("No words found. Add some words first!")
        else:
            # Выбираем случайное слово
            current_word = random.choice(words)
            st.write(f"**Russian:** {current_word['russian_word']}")

            with st.form("quiz_form"):
                user_answer = st.text_input("Translate to English:")
                submitted = st.form_submit_button("Check")

                if submitted:
                    is_correct = user_answer.lower().strip() == current_word['english_word'].lower()

                    # Обновляем статистику
            update_stats(
                st.session_state.user_id,
                current_word['id'],
                current_word['word_type'],
                is_correct
            )

            if is_correct:
                st.success("Correct! 🎉")
            else:
                st.error(f"Wrong! Correct answer: **{current_word['english_word']}**")

# Страница просмотра всех слов
elif page == "My Words":
    if 'user_id' not in st.session_state:
        st.warning("Please log in first!")
    else:
        st.title("My Vocabulary")
        st.subheader("All your words (common + personal)")

        words = get_user_words(st.session_state.user_id)
        if words:
            df = pd.DataFrame(words)
            st.dataframe(df, use_container_width=True)
            st.write(f"Total words: {len(words)}")
        else:
            st.info("You haven't added any words yet. Go to 'Add Words' section!")

# Страница статистики
elif page == "Statistics":
    if 'user_id' not in st.session_state:
        st.warning("Please log in first!")
    else:
        st.title("Learning Statistics")
        st.subheader("Your progress")

        stats = get_statistics(st.session_state.user_id)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Attempts", stats['total_attempts'])
        with col2:
            st.metric("Correct Answers", stats['total_correct'])
        with col3:
            st.metric("Accuracy", f"{stats['accuracy']}%")

        # Прогресс-бар
        progress = stats['accuracy'] / 100
        st.progress(progress)
        st.write(f"Your current accuracy: {stats['accuracy']}%")

# Страница удаления слов
elif page == "Delete Words":
    if 'user_id' not in st.session_state:
        st.warning("Please log in first!")
    else:
        st.title("Delete Words")
        st.subheader("Remove words from your personal list")

        words = get_user_words(st.session_state.user_id)
        personal_words = [w for w in words if w['word_type'] == 'personal']

        if personal_words:
            word_options = {f"{w['russian_word']} - {w['english_word']}": w['id'] for w in personal_words}
            selected_word = st.selectbox("Select word to delete:", options=list(word_options.keys()))

            if st.button("Delete Selected Word"):
                word_id = word_options[selected_word]
                success = delete_personal_word(st.session_state.user_id, word_id)
                if success:
                    st.success("Word deleted successfully!")
                    st.rerun()
                else:
                    st.error("Error deleting word.")
        else:
            st.info("No personal words to delete.")

# Информация о приложении в футере
st.sidebar.markdown("---")
st.sidebar.info("EnglishCard v1.0\nLearn English with spaced repetition!")