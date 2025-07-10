from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
import MySQLdb.cursors
from werkzeug.security import generate_password_hash, check_password_hash
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'mySuperSecretKey123!@#'

# MySQL config
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Bhavana@2002'
app.config['MYSQL_DB'] = 'task_reminder_db'

mysql = MySQL(app)

# Categories with suggestions for autocomplete
CATEGORY_SUGGESTIONS = {
    'Work': ['Email client', 'Project meeting', 'Code review', 'Write report'],
    'Personal': ['Buy groceries', 'Call mom', 'Pay bills', 'Workout'],
    'Health': ['Doctor appointment', 'Meditation', 'Take medicine', 'Yoga'],
    'Family': ['Birthday party', 'Visit grandparents', 'Family dinner'],
    'Finance': ['Budget planning', 'Tax filing', 'Investment review'],
    'Shopping': ['Buy shoes', 'Order gifts', 'Buy birthday cake'],
    'Events': ['Concert', 'Webinar', 'Conference'],
    'Travel': ['Book flight', 'Pack bags', 'Hotel reservation'],
    'Education': ['Study math', 'Read book', 'Online course'],
    'Home': ['Clean kitchen', 'Fix sink', 'Water plants'],
    'Hobbies': ['Photography', 'Painting', 'Guitar practice'],
    'Calls': ['Call John', 'Follow up with HR'],
    'Emails': ['Reply to boss', 'Send invoices'],
    'Goals': ['Run 5K', 'Learn French']
}

# Password validation function
def is_valid_password(p):
    return (6 <= len(p) <= 8 and
            re.search(r'[A-Z]', p) and
            re.search(r'[a-z]', p) and
            re.search(r'\d', p) and
            re.search(r'[!@#$%^&*(),.?":{}|<>]', p))

@app.route('/', methods=['GET', 'POST'])
def login_signup():
    if 'email' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        # Basic validation
        if not email or not password:
            flash('Please enter email and password.')
            return redirect(url_for('login_signup'))

        if form_type == 'login':
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cursor.fetchone()

            if user and check_password_hash(user['password'], password):
                session['email'] = email
                return redirect(url_for('index'))
            else:
                flash('Invalid email or password.')
                return redirect(url_for('login_signup'))

        elif form_type == 'signup':
            if not email.endswith('@gmail.com'):
                flash('Email must be a gmail.com address.')
                return redirect(url_for('login_signup'))

            if not is_valid_password(password):
                flash('Password must be 6-8 chars, include uppercase, lowercase, number, symbol.')
                return redirect(url_for('login_signup'))

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT * FROM users WHERE email = %s', (email,))
            existing_user = cursor.fetchone()
            if existing_user:
                flash('Email already registered.')
                return redirect(url_for('login_signup'))

            hashed_password = generate_password_hash(password)
            cursor.execute('INSERT INTO users (email, password) VALUES (%s, %s)', (email, hashed_password))
            mysql.connection.commit()
            flash('Registration successful! Please login.')
            return redirect(url_for('login_signup'))

    return render_template('login.html')

@app.route('/index')
def index():
    if 'email' not in session:
        return redirect(url_for('login_signup'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM tasks WHERE user_email = %s ORDER BY time", (session['email'],))
    tasks = cursor.fetchall()
    return render_template('index.html', tasks=tasks, categories=list(CATEGORY_SUGGESTIONS.keys()))

@app.route('/add_task', methods=['POST'])
def add_task():
    if 'email' not in session:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401

    task = request.form.get('task', '').strip()
    time_str = request.form.get('time')
    category = request.form.get('category', '').strip()

    if not task or not time_str or not category:
        return jsonify({'success': False, 'message': 'All fields are required.'})

    try:
        datetime.strptime(time_str, '%Y-%m-%dT%H:%M')
    except:
        return jsonify({'success': False, 'message': 'Invalid datetime format.'})

    cursor = mysql.connection.cursor()
    cursor.execute("INSERT INTO tasks (task, time, category, user_email, status) VALUES (%s, %s, %s, %s, %s)", 
                   (task, time_str, category, session['email'], 'pending'))
    mysql.connection.commit()

    return jsonify({'success': True, 'task': task, 'time': time_str, 'category': category})

@app.route('/tasks_suggestions/<category>')
def tasks_suggestions(category):
    suggestions = CATEGORY_SUGGESTIONS.get(category, [])
    return jsonify(suggestions)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login_signup'))

@app.route('/update_task_status', methods=['POST'])
def update_task_status():
    if 'email' not in session:
        return jsonify({'success': False}), 401

    task_id = request.form.get('task_id')
    status = request.form.get('status')
    if not task_id or status not in ['taken', 'missed']:
        return jsonify({'success': False, 'message': 'Invalid request.'})

    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE tasks SET status = %s WHERE id = %s AND user_email = %s", (status, task_id, session['email']))
    mysql.connection.commit()
    return jsonify({'success': True})

@app.route('/check_due_tasks')
def check_due_tasks():
    if 'email' not in session:
        return jsonify({'due_tasks': []})

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("""
        SELECT * FROM tasks
        WHERE user_email = %s AND time = %s AND status = 'pending'
        ORDER BY time LIMIT 1
    """, (session['email'], now_str))
    due_tasks = cursor.fetchall()
    return jsonify({'due_tasks': due_tasks})

if __name__ == '__main__':
    app.run(debug=True)
