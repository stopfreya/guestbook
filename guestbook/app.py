from functools import wraps
from flask import Flask, render_template, request, redirect, jsonify, session, url_for
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'byt-ut-den-har-mot-nagot-hemligt'

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, 'guestbook.json')
USERS_FILE = os.path.join(BASE_DIR, 'users.json')








def find_node(nodes, target_id):
    """Sök rekursivt efter en nod (inlägg eller svar) med givet id."""
    target_id = str(target_id)
    for node in nodes:
        if str(node.get('id')) == target_id:
            return node
        found = find_node(node.get('replies', []), target_id)
        if found:
            return found
    return None

def migrate_nodes(nodes):
    """Se till att varje nod har id, likes, liked_by och replies. Returnerar True om något ändrades."""
    changed = False
    for node in nodes:
        if 'id' not in node:
            node['id'] = str(uuid.uuid4())[:8]
            changed = True
        elif not isinstance(node['id'], str):
            node['id'] = str(node['id'])
            changed = True
        if 'likes' not in node:
            node['likes'] = 0
            changed = True
        if 'liked_by' not in node or not isinstance(node.get('liked_by'), list):
            node['liked_by'] = []
            changed = True
        if 'replies' not in node:
            node['replies'] = []
            changed = True
        if migrate_nodes(node['replies']):
            changed = True
    return changed

def load_entries():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        entries = json.load(f)

    if migrate_nodes(entries):
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








def get_like_key():
    if 'username' in session:
        return f'user:{session["username"]}'

    anon_key = session.get('anon_like_id')
    if not anon_key:
        anon_key = str(uuid.uuid4())
        session['anon_like_id'] = anon_key

    return f'anon:{anon_key}'


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
            'likes': 0,
            'liked_by': [],
            'replies': []
        })
        save_entries(entries)
        return redirect(url_for('index'))

    return render_template(
        'index.html',
        entries=reversed(entries),
        username=session.get('username'),
        current_like_key=get_like_key()
    )


@app.route('/reply/<parent_id>', methods=['POST'])
@login_required
def reply(parent_id):
    entries = load_entries()
    parent = find_node(entries, parent_id)

    if parent is not None:
        comment = request.form['comment']
        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        parent['replies'].append({
            'id': str(uuid.uuid4())[:8],
            'name': session['username'],
            'comment': comment,
            'time': time,
            'likes': 0,
            'liked_by': [],
            'replies': []
        })
        save_entries(entries)

    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        if not username or not password:
            return render_template('register.html', error='Please enter both a username and a password.')

        users = load_users()
        if any(u['username'].lower() == username.lower() for u in users):
            return render_template('register.html', error='This username is already taken.')

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

        return render_template('login.html', error='Invalid username or password.')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/like/<node_id>', methods=['POST'])
def like(node_id):
    entries = load_entries()
    node = find_node(entries, node_id)

    if node is None:
        return jsonify({'error': 'Not found'}), 404

    if 'liked_by' not in node or not isinstance(node['liked_by'], list):
        node['liked_by'] = []

    like_key = get_like_key()
    liked_by = node['liked_by']

    if like_key in liked_by:
        liked_by.remove(like_key)
        node['likes'] = max(0, node['likes'] - 1)
        liked = False
    else:
        liked_by.append(like_key)
        node['likes'] += 1
        liked = True

    save_entries(entries)
    return jsonify({'likes': node['likes'], 'liked': liked})


if __name__ == '__main__':
    app.run(debug=True)