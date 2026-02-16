# harvest_music.py
import sqlite3
import requests
from time import sleep
from dotenv import load_dotenv
import os
import base64

load_dotenv()

DB_PATH = 'content.db'
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Жанры Spotify
MUSIC_GENRES = [
    "pop", "rock", "hip-hop", "electronic", "jazz", 
    "classical", "indie", "metal", "country", "r-n-b",
    "latin", "blues"
]

def get_spotify_token():
    """Получить access token для Spotify API"""
    url = "https://accounts.spotify.com/api/token"
    
    # Кодируем credentials
    credentials = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {"grant_type": "client_credentials"}
    
    try:
        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print(f"❌ Ошибка получения токена: {e}")
        return None

def get_mood_from_features(features):
    """
    Определяем mood по audio features БЕЗ ИИ!
    
    Audio Features от Spotify:
    - energy: 0-1 (энергичность)
    - valence: 0-1 (позитивность)
    - danceability: 0-1 (танцевальность)
    - acousticness: 0-1 (акустичность)
    - tempo: BPM
    """
    if not features:
        return "unknown"
    
    energy = features.get("energy", 0)
    valence = features.get("valence", 0)
    danceability = features.get("danceability", 0)
    acousticness = features.get("acousticness", 0)
    tempo = features.get("tempo", 0)
    
    # Энергичная (high energy + high valence)
    if energy > 0.7 and valence > 0.6:
        return "energetic"
    
    # Чилл (low energy + high acousticness)
    if energy < 0.5 and acousticness > 0.5:
        return "chill"
    
    # Грустная (low valence + low energy)
    if valence < 0.4 and energy < 0.5:
        return "sad"
    
    # Танцевальная (high danceability)
    if danceability > 0.7:
        return "party"
    
    # Ночной драйв (medium energy + low valence)
    if 0.4 < energy < 0.7 and valence < 0.5:
        return "night_drive"
    
    # Тренировка (high energy + high tempo)
    if energy > 0.8 and tempo > 120:
        return "workout"
    
    # Фокус (low energy + low danceability)
    if energy < 0.5 and danceability < 0.5:
        return "focus"
    
    return "vibe"

def get_track_epoch(year):
    """Эпоха трека"""
    if not year: return "unknown"
    if year >= 2023: return "new_releases"
    if year >= 2020: return "2020s"
    if year >= 2010: return "2010s"
    if year >= 2000: return "2000s"
    if year >= 1990: return "90s"
    if year >= 1980: return "80s"
    return "retro"

def fetch_tracks(token, genre, limit=50, offset=0):
    """Получить треки по жанру"""
    url = "https://api.spotify.com/v1/search"
    
    headers = {"Authorization": f"Bearer {token}"}
    
    params = {
        "q": f"genre:{genre}",
        "type": "track",
        "limit": limit,
        "offset": offset,
        "market": "US"  # Для доступа к большему каталогу
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()["tracks"]["items"]
    except Exception as e:
        print(f"  ❌ Ошибка поиска: {e}")
        return []

def fetch_audio_features(token, track_id):
    """Получить audio features трека"""
    url = f"https://api.spotify.com/v1/audio-features/{track_id}"
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return None

def get_mood_from_genre(genre):
    """Fallback для mood по жанру"""
    genre_lower = genre.lower()
    
    if genre_lower in ["metal", "hip-hop", "electronic", "rock"]:
        return "energetic"
    if genre_lower in ["jazz", "classical", "blues"]:
        return "chill"
    if genre_lower in ["pop", "latin", "r-n-b"]:
        return "party"
    if genre_lower in ["indie", "country"]:
        return "focus"
    
    return "vibe"

def save_track(cursor, track, genre_name, token):
    """Сохранение трека в БД"""
    
    track_id = track["id"]
    title = track["name"]
    
    if not title or len(title) < 2:
        return False
    
    artists = ", ".join([artist["name"] for artist in track["artists"]])
    
    album = track["album"]
    year = None
    if album.get("release_date"):
        try:
            year = int(album["release_date"][:4])
        except:
            pass
    
    images = album.get("images", [])
    image_url = images[0]["url"] if images else None
    
    popularity = track.get("popularity", 0)
    
    # Получаем audio features
    features = fetch_audio_features(token, track_id)
    
    # НОВОЕ: Fallback на жанр, если features не работают
    if features and features.get("energy") is not None:
        mood = get_mood_from_features(features)
    else:
        # Определяем mood по жанру как fallback
        mood = get_mood_from_genre(genre_name)
    
    duration_ms = track.get("duration_ms", 0)
    minutes = duration_ms // 60000
    seconds = (duration_ms % 60000) // 1000
    duration = f"{minutes}:{seconds:02d}"
    
    if popularity >= 80:
        criteria = "hit"
    elif popularity >= 60:
        criteria = "popular"
    elif popularity >= 40:
        criteria = "rising"
    else:
        criteria = "underground"
    
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO content 
            (type, title, creator, description, image_url, year, rating, genre, epoch, mood, criteria, source_id, needs_ai)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "music",
            title,
            artists,
            duration,
            image_url,
            year,
            popularity / 10,
            genre_name,
            get_track_epoch(year),
            mood,
            criteria,
            f"spotify_{track_id}",
            0
        ))
        return True
    except Exception as e:
        return False

def harvest():
    print("🎵 Начинаю сбор музыки из Spotify...\n")
    
    # Получаем токен
    token = get_spotify_token()
    if not token:
        print("❌ Не удалось получить токен Spotify")
        return
    
    print("✅ Токен получен\n")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Очищаем старую музыку
    cursor.execute("DELETE FROM content WHERE type='music'")
    conn.commit()
    print("🗑️ Старая музыка удалена\n")
    
    total_saved = 0
    
    for genre in MUSIC_GENRES:
        print(f"🎸 Жанр: {genre}")
        genre_count = 0
        
        # 3 пачки по 50 треков = 150 на жанр
        for batch in range(3):
            tracks = fetch_tracks(token, genre, limit=50, offset=batch*50)
            
            if not tracks:
                break
            
            saved_count = 0
            for track in tracks:
                if save_track(cursor, track, genre, token):
                    saved_count += 1
                
                sleep(0.05)  # Небольшая пауза (audio features запрос)
            
            conn.commit()
            total_saved += saved_count
            genre_count += saved_count
            
            print(f"  Пачка {batch+1}: +{saved_count} треков")
            
            sleep(1)
            
            # Лимит 100 на жанр
            if genre_count >= 100:
                break
        
        print(f"  ✅ Итого: {genre_count} треков\n")
    
    conn.close()
    print(f"\n🎉 Готово! Сохранено: {total_saved} треков")
    
    # Статистика
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n🎸 По жанрам:")
    cursor.execute('''
        SELECT genre, COUNT(*) 
        FROM content 
        WHERE type='music' 
        GROUP BY genre
        ORDER BY COUNT(*) DESC
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} треков")
    
    print("\n🎭 По настроениям (MOOD):")
    cursor.execute('''
        SELECT mood, COUNT(*) 
        FROM content 
        WHERE type='music' 
        GROUP BY mood
        ORDER BY COUNT(*) DESC
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} треков")
    
    print("\n📊 По критериям:")
    cursor.execute('''
        SELECT criteria, COUNT(*) 
        FROM content 
        WHERE type='music' 
        GROUP BY criteria
        ORDER BY COUNT(*) DESC
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} треков")
    
    conn.close()



if __name__ == "__main__":
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print("❌ Нет Spotify credentials в .env")
        print("Добавь:")
        print("SPOTIFY_CLIENT_ID=...")
        print("SPOTIFY_CLIENT_SECRET=...")
    else:
        harvest()
