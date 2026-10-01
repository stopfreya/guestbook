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
GUESTBOOK_FILE = os.path.join(BASE_DIR, 'guestbook.json')
TOPICS_FILE = os.path.join(BASE_DIR, 'topics.json')
USERS_FILE = os.path.join(BASE_DIR, 'users.json')


def find_node(nodes, target_id):
    target_id = str(target_id)
    for node in nodes:
        if str(node.get('id')) == target_id:
            return node
        found = find_node(node.get('replies', []), target_id)
        if found:
            return found
    return None

def migrate_nodes(nodes):
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

def make_node(comment):
    time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    return {
        'id': str(uuid.uuid4())[:8],
        'name': session['username'],
        'comment': comment,
        'time': time,
        'likes': 0,
        'liked_by': [],
        'replies': []
    }

def get_like_key():
    if 'username' in session:
        return f'user:{session["username"]}'
    anon_key = session.get('anon_like_id')
    if not anon_key:
        anon_key = str(uuid.uuid4())
        session['anon_like_id'] = anon_key
    return f'anon:{anon_key}'


# ---------- Guestbook ----------

def load_entries():
    if not os.path.exists(GUESTBOOK_FILE):
        return []
    with open(GUESTBOOK_FILE, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    if migrate_nodes(entries):
        save_entries(entries)
    return entries

def save_entries(entries):
    with open(GUESTBOOK_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


# ---------- Forum ----------

def migrate_topics(topics):
    changed = False
    for topic in topics:
        if 'id' not in topic:
            topic['id'] = str(uuid.uuid4())[:8]
            changed = True
        if 'posts' not in topic:
            topic['posts'] = []
            changed = True
        if migrate_nodes(topic['posts']):
            changed = True
    return changed

def load_topics():
    if not os.path.exists(TOPICS_FILE):
        return []
    with open(TOPICS_FILE, 'r', encoding='utf-8') as f:
        topics = json.load(f)
    if migrate_topics(topics):
        save_topics(topics)
    return topics

def save_topics(topics):
    with open(TOPICS_FILE, 'w', encoding='utf-8') as f:
        json.dump(topics, f, ensure_ascii=False, indent=2)

def find_topic(topics, topic_id):
    return next((t for t in topics if str(t['id']) == str(topic_id)), None)


# ---------- Users ----------

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


# ---------- Guestbook routes ----------

@app.route('/', methods=['GET', 'POST'])
def index():
    entries = load_entries()

    if request.method == 'POST':
        if 'username' not in session:
            return redirect(url_for('login'))
        entries.append(make_node(request.form['comment']))
        save_entries(entries)
        return redirect(url_for('index'))

    return render_template(
        'index.html',
        entries=list(reversed(entries)),
        username=session.get('username'),
        current_like_key=get_like_key()
    )


@app.route('/reply/<parent_id>', methods=['POST'])
@login_required
def reply(parent_id):
    entries = load_entries()
    parent = find_node(entries, parent_id)
    if parent is not None:
        parent['replies'].append(make_node(request.form['comment']))
        save_entries(entries)
    return redirect(url_for('index'))


@app.route('/like/<node_id>', methods=['POST'])
def like(node_id):
    entries = load_entries()
    node = find_node(entries, node_id)
    if node is None:
        return jsonify({'error': 'Not found'}), 404

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


# ---------- Forum routes ----------

@app.route('/forum')
def forum():
    topics = load_topics()
    return render_template('topics.html', topics=list(reversed(topics)), username=session.get('username'))


@app.route('/forum/new', methods=['GET', 'POST'])
@login_required
def new_topic():
    if request.method == 'POST':
        title = request.form['title'].strip()
        comment = request.form['comment'].strip()

        if not title or not comment:
            return render_template('new_topic.html', error='Please fill in both a title and a message.')

        topics = load_topics()
        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        topics.append({
            'id': str(uuid.uuid4())[:8],
            'title': title,
            'creator': session['username'],
            'time': time,
            'posts': [make_node(comment)]
        })
        save_topics(topics)
        return redirect(url_for('forum'))

    return render_template('new_topic.html')


@app.route('/forum/<topic_id>', methods=['GET', 'POST'])
def view_topic(topic_id):
    topics = load_topics()
    topic = find_topic(topics, topic_id)
    if topic is None:
        return "Topic not found", 404

    if request.method == 'POST':
        if 'username' not in session:
            return redirect(url_for('login'))
        topic['posts'].append(make_node(request.form['comment']))
        save_topics(topics)
        return redirect(url_for('view_topic', topic_id=topic_id))

    return render_template(
        'topic.html',
        topic=topic,
        posts=list(reversed(topic['posts'])),
        username=session.get('username'),
        current_like_key=get_like_key()
    )


@app.route('/forum/<topic_id>/reply/<parent_id>', methods=['POST'])
@login_required
def topic_reply(topic_id, parent_id):
    topics = load_topics()
    topic = find_topic(topics, topic_id)
    if topic is None:
        return "Topic not found", 404

    parent = find_node(topic['posts'], parent_id)
    if parent is not None:
        parent['replies'].append(make_node(request.form['comment']))
        save_topics(topics)

    return redirect(url_for('view_topic', topic_id=topic_id))


@app.route('/forum/<topic_id>/like/<node_id>', methods=['POST'])
def topic_like(topic_id, node_id):
    topics = load_topics()
    topic = find_topic(topics, topic_id)
    if topic is None:
        return jsonify({'error': 'Not found'}), 404

    node = find_node(topic['posts'], node_id)
    if node is None:
        return jsonify({'error': 'Not found'}), 404

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

    save_topics(topics)
    return jsonify({'likes': node['likes'], 'liked': liked})


# ---------- Auth ----------

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

        users.append({'username': username, 'password_hash': generate_password_hash(password)})
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


if __name__ == '__main__':
    app.run(debug=True)