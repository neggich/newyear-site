from flask import Flask, render_template, request, jsonify
import sqlite3
import requests as req

app = Flask(__name__)

# === БАЗА ДАННЫХ ===
def get_db():
    conn = sqlite3.connect('wishlist.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS wishlist
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     title TEXT, artist TEXT, album TEXT,
                     cover_url TEXT, added_by TEXT,
                     added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

init_db()

# === ГЛАВНАЯ СТРАНИЦА ===
@app.route('/')
def index():
    return render_template('index.html')

# === ПОИСК ТРЕКОВ ЧЕРЕЗ DEEZER ===
@app.route('/api/search')
def search():
    q = request.args.get('q', '')
    if len(q) < 2:
        return jsonify({'tracks': [], 'artists': []})

    # Ищем треки
    r1 = req.get('https://api.deezer.com/search', params={'q': q, 'limit': 15}).json()
    tracks = []
    for t in r1.get('data', []):
        if t.get('preview'):
            tracks.append({
                'id': t['id'],
                'title': t['title'],
                'artist': t['artist']['name'],
                'album': t['album']['title'],
                'cover': t['album']['cover_medium']
            })

    # Ищем исполнителей
    r2 = req.get('https://api.deezer.com/search/artist', params={'q': q, 'limit': 5}).json()
    artists = []
    for a in r2.get('data', []):
        artists.append({
            'id': a['id'],
            'name': a['name'],
            'picture': a['picture_medium']
        })

    return jsonify({'tracks': tracks, 'artists': artists})

# === ТОП ТРЕКИ ИСПОЛНИТЕЛЯ ===
@app.route('/api/artist/<int:artist_id>/top')
def artist_top(artist_id):
    # Получаем топ-треки (максимум 100)
    r = req.get(f'https://api.deezer.com/artist/{artist_id}/top', params={'limit': 100}).json()
    tracks = []
    for t in r.get('data', []):
        tracks.append({
            'id': t['id'],
            'title': t['title'],
            'artist': t['artist']['name'],
            'album': t['album']['title'],
            'cover': t['album']['cover_medium']
        })
    
    # Дополнительно ищем треки через альбомы исполнителя
    albums_r = req.get(f'https://api.deezer.com/artist/{artist_id}/albums', params={'limit': 50}).json()
    album_ids = [a['id'] for a in albums_r.get('data', [])[:10]]  # Берём первые 10 альбомов
    
    for album_id in album_ids:
        album_tracks_r = req.get(f'https://api.deezer.com/album/{album_id}/tracks').json()
        for t in album_tracks_r.get('data', []):
            # Проверяем что трек ещё не добавлен
            if not any(tr['id'] == t['id'] for tr in tracks):
                tracks.append({
                    'id': t['id'],
                    'title': t['title'],
                    'artist': t['artist']['name'],
                    'album': t.get('album', {}).get('title', 'Unknown'),
                    'cover': t.get('album', {}).get('cover_medium', '')
                })
    
    return jsonify(tracks)

# === ДОБАВИТЬ В ВИШЛИСТ ===
@app.route('/api/wishlist', methods=['POST'])
def add_song():
    data = request.get_json()
    conn = get_db()
    conn.execute(
        'INSERT INTO wishlist (title, artist, album, cover_url, added_by) VALUES (?,?,?,?,?)',
        (data['title'], data['artist'], data['album'], data['cover'], data['added_by'])
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# === ПОЛУЧИТЬ ВИШЛИСТ ===
@app.route('/api/wishlist')
def get_wishlist():
    conn = get_db()
    rows = conn.execute('SELECT * FROM wishlist ORDER BY added_at DESC').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

# === УДАЛИТЬ ИЗ ВИШЛИСТА ===
@app.route('/api/wishlist/<int:song_id>', methods=['DELETE'])
def delete_song(song_id):
    conn = get_db()
    conn.execute('DELETE FROM wishlist WHERE id=?', (song_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

# === ЗАПУСК ===
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
