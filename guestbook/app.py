from functools import wraps
from flask import Flask, render_template, request, redirect, jsonify, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'byt-ut-den-har-mot-nagot-hemligt'  # krävs för sessions

DATA_FILE = 'guestbook.json'
USERS_FILE = 'users.json'











def load_entries():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        entries = json.load(f)

    changed = False
    for entry in entries:
        if 'id' not in entry:
            entry['id'] = str(uuid.uuid4())[:8]
            changed = True
        if 'likes' not in entry:
            entry['likes'] = 0
            changed = True
    if changed:
        save_entries(entries)

    return entries

def save_entries(entries):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)










def load_users():
    if not os.path.exists(USERS_FILE):
        return []
    with open(USERS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated









@app.route('/', methods=['GET', 'POST'])
def index():
    entries = load_entries()

    if request.method == 'POST':
        if 'username' not in session:
            return redirect(url_for('login'))

        comment = request.form['comment']
        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        entries.append({
            'id': str(uuid.uuid4())[:8],
            'name': session['username'],
            'comment': comment,
            'time': time,
            'likes': 0
        })
        save_entries(entries)
        return redirect(url_for('index'))

    return render_template('index.html', entries=reversed(entries), username=session.get('username'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        if not username or not password:
            return render_template('register.html', error='Fyll i både användarnamn och lösenord.')

        users = load_users()
        if any(u['username'].lower() == username.lower() for u in users):
            return render_template('register.html', error='Användarnamnet är upptaget.')

        users.append({
            'username': username,
            'password_hash': generate_password_hash(password)
        })
        save_users(users)

        session['username'] = username
        return redirect(url_for('index'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        users = load_users()
        user = next((u for u in users if u['username'].lower() == username.lower()), None)

        if user and check_password_hash(user['password_hash'], password):
            session['username'] = user['username']
            return redirect(url_for('index'))

        return render_template('login.html', error='Fel användarnamn eller lösenord.')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/like/<entry_id>', methods=['POST'])
def like(entry_id):
    entries = load_entries()

    for entry in entries:
        if entry['id'] == entry_id:
            entry['likes'] += 1
            save_entries(entries)
            return jsonify({'likes': entry['likes']})

    return jsonify({'error': 'Entry not found'}), 404


if __name__ == '__main__':
    app.run(debug=True)