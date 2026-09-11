from flask import Flask, render_template, request, redirect
import json
import os
from datetime import datetime

app = Flask(__name__)
DATA_FILE = 'guestbook.json'

def load_entries():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

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

        entries.append({
            'name': name,
            'email': email,
            'comment': comment,
            'time': time
        })
        save_entries(entries)
        return redirect('/')

    # Visa senaste inlägget först
    return render_template('index.html', entries=reversed(entries))

if __name__ == '__main__':
    app.run(debug=True)