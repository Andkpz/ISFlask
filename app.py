from flask import Flask, render_template_string, request, redirect, url_for, session, flash
import sqlite3
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'hardcoded-secret-key'  # УЯЗВИМОСТЬ 1: Жёстко заданный ключ

# Инициализация БД
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            password TEXT  # УЯЗВИМОСТЬ 2: Пароли без хэширования
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('profile'))
    return render_template_string('''
        <h1>Уязвимое приложение</h1>
        <a href="{{ url_for('login') }}">Войти</a> | 
        <a href="{{ url_for('register') }}">Регистрация</a>
    ''')

# УЯЗВИМОСТЬ 3: SQL-инъекция в регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # ❌ SQL INJECTION: Прямая конкатенация
        query = f"SELECT * FROM users WHERE username = '{username}'"
        cursor.execute(query)
        
        if cursor.fetchone():
            flash('Пользователь уже существует', 'danger')
            conn.close()
            return redirect(url_for('register'))
        
        # ❌ SQL INJECTION: Вставка данных без экранирования
        insert_query = f"INSERT INTO users (username, password) VALUES ('{username}', '{password}')"
        cursor.execute(insert_query)
        conn.commit()
        conn.close()
        
        flash('Регистрация успешна!', 'success')
        return redirect(url_for('login'))
    
    return render_template_string('''
        <h1>Регистрация</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="Имя пользователя">
            <input type="password" name="password" placeholder="Пароль">
            <button type="submit">Зарегистрироваться</button>
        </form>
        <a href="{{ url_for('login') }}">Войти</a>
    ''')

# УЯЗВИМОСТЬ 4: SQL-инъекция в логине
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        
        # ❌ SQL INJECTION: Прямая конкатенация в WHERE
        query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        cursor.execute(query)
        user = cursor.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash('Вы вошли!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Неверные данные', 'danger')
    
    return render_template_string('''
        <h1>Вход</h1>
        <form method="POST">
            <input type="text" name="username" placeholder="Имя пользователя">
            <input type="password" name="password" placeholder="Пароль">
            <button type="submit">Войти</button>
        </form>
        <a href="{{ url_for('register') }}">Регистрация</a>
    ''')

# УЯЗВИМОСТЬ 5: XSS в профиле
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    username = session.get('username', 'Гость')
    
    # ❌ XSS: Отсутствие экранирования (если использовать |safe)
    return render_template_string('''
        <h1>Личный кабинет</h1>
        <p>Привет, {{ username }}!</p>
        <p>Ваш ID: {{ session['user_id'] }}</p>
        <a href="{{ url_for('logout') }}">Выйти</a>
    ''', username=username, session=session)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)  # УЯЗВИМОСТЬ 6: Debug в продакшене
