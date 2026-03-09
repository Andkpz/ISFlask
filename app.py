from flask import Flask, render_template_string, request, redirect, url_for, session, flash, make_response
import sqlite3
import os
import hashlib

app = Flask(__name__)

# 🔴 УЯЗВИМОСТЬ 1: Слабый SECRET_KEY (легко подобрать)
app.config['SECRET_KEY'] = 'insecure-learning-key-only'

# 🔹 Путь к базе данных
DB_FILENAME = 'test_db.sqlite'
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_FILENAME)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ============================================
# 🚨 ГЛАВНАЯ СТРАНИЦА
# ============================================
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('profile'))
    
    db_exists = os.path.exists(DB_PATH)
    
    # 🔴 УЯЗВИМОСТЬ 2: Информация о путях (Information Disclosure)
    return render_template_string('''
        <h1>🚨 Уязвимое приложение (ТОЛЬКО LOCALHOST!)</h1>
        <p>Статус БД: <strong>{{ 'Найдена' if db_exists else 'НЕ НАЙДЕНА' }}</strong></p>
        <p>Путь к БД: <code>{{ db_path }}</code></p>
        <p>SECRET_KEY: <code>insecure-learning-key-only</code></p>
        <p>Debug режим: <code>True</code></p>
        {% if not db_exists %}
            <p style="color:red">❌ Файл базы данных не найден!</p>
        {% endif %}
        <a href="{{ url_for('login') }}">Войти</a> | 
        <a href="{{ url_for('register') }}">Регистрация</a>
        <br><br>
        <a href="{{ url_for('search') }}">🔍 Поиск пользователей</a>
        <a href="{{ url_for('debug') }}">🐛 Debug страница</a>
    ''', db_path=DB_PATH, db_exists=db_exists)

# ============================================
# 🚨 РЕГИСТРАЦИЯ (SQL Injection)
# ============================================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('Введите имя и пароль', 'danger')
            return redirect(url_for('register'))
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 🔴 УЯЗВИМОСТЬ 3: SQL Injection в SELECT
            query = f"SELECT * FROM users WHERE username = '{username}'"
            cursor.execute(query)
            
            if cursor.fetchone():
                flash('Пользователь уже существует', 'danger')
                conn.close()
                return redirect(url_for('register'))
            
            # 🔴 УЯЗВИМОСТЬ 4: SQL Injection в INSERT + Пароли без хэша
            insert_query = f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')"
            cursor.execute(insert_query)
            conn.commit()
            conn.close()
            
            flash('Регистрация успешна!', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            # 🔴 УЯЗВИМОСТЬ 5: Раскрытие ошибок БД
            flash(f'Ошибка БД: {str(e)}', 'danger')
            print(f"❌ Ошибка в register: {e}")
    
    return render_template_string('''
        <h1>Регистрация</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="Имя пользователя" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">Зарегистрироваться</button>
        </form>
        <a href="{{ url_for('login') }}">Войти</a>
    ''')

# ============================================
# 🚨 ВХОД (SQL Injection + Brute Force)
# ============================================
@app.route('/login', methods=['GET', 'POST'])
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Уязвимый запрос
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        
        try:
            cursor.execute(query)
            user = cursor.fetchone()
        except Exception as e:
            # 🔴 ВАЖНО: Выводим ошибку явно, чтобы sqlmap её увидел
            # Или просто падаем с 500 ошибкой, что тоже информативно для сканера
            return f"<h1>Database Error</h1><pre>{str(e)}</pre>", 500
        
        conn.close()
        
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('profile'))
        else:
            return "<h1>Login Failed</h1><p>Invalid credentials</p>", 200
    
    return render_template_string('''
        <h1>Вход</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="Имя пользователя" required>
            <input type="password" name="password" placeholder="Пароль" required>
            <button type="submit">Войти</button>
        </form>
        <a href="{{ url_for('register') }}">Регистрация</a>
    ''')

# ============================================
# 🚨 ПРОФИЛЬ (XSS + Session Fixation)
# ============================================
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    username = session.get('username', 'Гость')
    
    # 🔴 УЯЗВИМОСТЬ 9: XSS через параметр GET
    message = request.args.get('message', '')
    
    # 🔴 УЯЗВИМОСТЬ 10: Нет проверки User-Agent / Session Fixation
    return render_template_string('''
        <h1>Личный кабинет</h1>
        <p>Привет, {{ username }}!</p>
        <p>Ваш ID: {{ session['user_id'] }}</p>
        
        <!-- 🔴 УЯЗВИМОСТЬ 11: XSS через message (не экранируется) -->
        {% if message %}
            <div style="background: yellow; padding: 10px;">
                {{ message | safe }}
            </div>
        {% endif %}
        
        <!-- 🔴 УЯЗВИМОСТЬ 12: Отображение сырых данных сессии -->
        <details>
            <summary>🔍 Информация о сессии</summary>
            <pre>{{ session }}</pre>
        </details>
        
        <br>
        <a href="{{ url_for('logout') }}">Выйти</a>
        <a href="{{ url_for('search') }}">🔍 Поиск</a>
    ''', username=username, message=message)

# ============================================
# 🚨 ПОИСК (SQL Injection + UNION)
# ============================================
@app.route('/search')
def search():
    query = request.args.get('q', '')
    
    results = []
    sql_query = ""
    
    if query:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 🔴 УЯЗВИМОСТЬ 13: SQL Injection в поиске
            sql_query = f"SELECT id, username, password FROM users WHERE username LIKE '%{query}%'"
            cursor.execute(sql_query)
            results = cursor.fetchall()
            conn.close()
        except Exception as e:
            results = []
            sql_query = f"Ошибка: {str(e)}"
    
    return render_template_string('''
        <h1>🔍 Поиск пользователей</h1>
        <form method="GET">
            <input type="text" name="q" placeholder="Поиск..." value="{{ query }}">
            <button type="submit">Найти</button>
        </form>
        
        {% if results %}
            <h2>Результаты:</h2>
            <table border="1">
                <tr><th>ID</th><th>Username</th><th>Password</th></tr>
                {% for user in results %}
                <tr>
                    <td>{{ user['id'] }}</td>
                    <td>{{ user['username'] }}</td>
                    <td>{{ user['password'] }}</td>
                </tr>
                {% endfor %}
            </table>
        {% endif %}
        
        <!-- 🔴 УЯЗВИМОСТЬ 14: Раскрытие SQL запроса -->
        {% if sql_query %}
            <details>
                <summary>🐛 SQL Query (Debug)</summary>
                <code>{{ sql_query }}</code>
            </details>
        {% endif %}
        
        <br>
        <a href="{{ url_for('index') }}">На главную</a>
    ''', query=query, results=results, sql_query=sql_query)

# ============================================
# 🚨 DEBUG СТРАНИЦА (Information Disclosure)
# ============================================
@app.route('/debug')
def debug():
    # 🔴 УЯЗВИМОСТЬ 15: Полная информация о системе
    debug_info = {
        'SECRET_KEY': app.config['SECRET_KEY'],
        'DB_PATH': DB_PATH,
        'DB_EXISTS': os.path.exists(DB_PATH),
        'SESSION': dict(session),
        'REQUEST_HEADERS': dict(request.headers),
        'ENV': dict(os.environ),
    }
    
    return render_template_string('''
        <h1>🐛 Debug Информация</h1>
        <pre>{{ debug_info }}</pre>
        <br>
        <a href="{{ url_for('index') }}">На главную</a>
    ''', debug_info=debug_info)

# ============================================
# 🚨 КОММЕНТАРИИ (SQL Injection в cookie)
# ============================================
@app.route('/set_theme')
def set_theme():
    theme = request.args.get('theme', 'light')
    
    # 🔴 УЯЗВИМОСТЬ 16: XSS через Cookie
    resp = make_response(redirect(url_for('profile')))
    resp.set_cookie('theme', theme)
    return resp

# ============================================
# 🚨 ВЫХОД
# ============================================
@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))

# ============================================
# 🚨 ЗАПУСК
# ============================================
if __name__ == '__main__':
    print(f"🔍 Поиск БД: {DB_PATH}")
    print(f"✅ Файл существует: {os.path.exists(DB_PATH)}")
    print(f"🚨 ВНИМАНИЕ: Запуск с debug=True и уязвимостями!")
    
    # 🔴 УЯЗВИМОСТЬ 17: Debug режим + доступ снаружи контейнера
    app.run(debug=True, host='0.0.0.0', port=5000)

