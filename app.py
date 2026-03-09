from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'insecure-learning-key-only'  # ⚠️ Только для локальных тестов!

# 🔹 ПОДКЛЮЧЕНИЕ К СУЩЕСТВУЮЩЕЙ БД
# Ищет файл test_db.sqlite или test_db.db в текущей директории
DB_FILENAME = 'test_db.sqlite'  # Или 'test_db.db', в зависимости от вашего файла
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_FILENAME)

def get_db_connection():
    """Подключение к базе данных test_db"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('profile'))
    return render_template_string('''
        <h1>🚨 Уязвимое приложение (ТОЛЬКО LOCALHOST!)</h1>
        <p>База данных: <strong>test_db</strong></p>
        <p>Путь: <code>{{ db_path }}</code></p>
        <a href="{{ url_for('login') }}">Войти</a> | 
        <a href="{{ url_for('register') }}">Регистрация</a>
    ''', db_path=DB_PATH)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Введите имя и пароль', 'danger')
            return redirect(url_for('register'))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ❌ SQL INJECTION: Прямая конкатенация
        query = f"SELECT * FROM users WHERE username = '{username}'"
        cursor.execute(query)
        
        if cursor.fetchone():
            flash('Пользователь уже существует', 'danger')
            conn.close()
            return redirect(url_for('register'))
        
        # ❌ SQL INJECTION: Вставка без экранирования
        insert_query = f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')"
        cursor.execute(insert_query)
        conn.commit()
        conn.close()
        
        flash('Регистрация успешна!', 'success')
        return redirect(url_for('login'))
    
    return render_template_string('''
        <h1>Регистрация</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="Имя пользователя" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">Зарегистрироваться</button>
        </form>
        <a href="{{ url_for('login') }}">Войти</a>
    ''')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # ❌ SQL INJECTION: Прямая конкатенация в WHERE
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        cursor.execute(query)
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Вы вошли!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Неверные данные', 'danger')
    
    return render_template_string('''
        <h1>Вход</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="Имя пользователя" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">Войти</button>
        </form>
        <a href="{{ url_for('register') }}">Регистрация</a>
    ''')

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    username = session.get('username', 'Гость')
    
    return render_template_string('''
        <h1>Личный кабинет</h1>
        <p>Привет, {{ username }}!</p>
        <p>Ваш ID: {{ session['user_id'] }}</p>
        <p>База данных: <strong>test_db</strong></p>
        <a href="{{ url_for('logout') }}">Выйти</a>
    ''', username=username)

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Проверка наличия БД при старте
    if os.path.exists(DB_PATH):
        print(f"✅ База данных найдена: {DB_PATH}")
        
        # Проверка таблицы users
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
        if cursor.fetchone():
            print("✅ Таблица 'users' существует")
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            print(f"✅ Записей в таблице: {count}")
        else:
            print("⚠️ Таблица 'users' не найдена!")
        conn.close()
    else:
        print(f"❌ База данных не найдена: {DB_PATH}")
        print("💡 Убедитесь, что файл test_db.sqlite находится в той же папке, что и app.py")
    
    app.run(debug=True, host='127.0.0.1', port=5000)
