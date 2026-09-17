from flask import Flask, render_template, request, redirect, jsonify
import json
import os
from datetime import datetime

app = Flask(__name__)
DATA_FILE = 'guestbook.json'


def load_entries():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        entries = json.load(f)

    for index, entry in enumerate(entries):
        entry['id'] = entry.get('id', index + 1)
        entry['likes'] = entry.get('likes', 0)
        entry['liked'] = entry.get('liked', False)

    return entries


def save_entries(entries):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


@app.route('/', methods=['GET', 'POST'])
def index():
    entries = load_entries()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        comment = request.form['comment']
        time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        next_id = max((entry.get('id', 0) for entry in entries), default=0) + 1

        entries.append({
            'id': next_id,
            'name': name,
            'email': email,
            'comment': comment,
            'time': time,
            'likes': 0,
            'liked': False
        })
        save_entries(entries)
        return redirect('/')

    return render_template('index.html', entries=reversed(entries))


@app.route('/like/<int:entry_id>', methods=['POST'])
def like_entry(entry_id):
    entries = load_entries()
    for entry in entries:
        if entry.get('id') == entry_id:
            if entry.get('liked', False):
                entry['likes'] = max(0, entry.get('likes', 0) - 1)
                entry['liked'] = False
            else:
                entry['likes'] = entry.get('likes', 0) + 1
                entry['liked'] = True

            save_entries(entries)
            return jsonify({
                'likes': entry['likes'],
                'liked': entry['liked']
            })

    return jsonify({'likes': 0, 'liked': False}), 404


if __name__ == '__main__':
    app.run(debug=True)