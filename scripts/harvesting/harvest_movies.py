# harvest_movies.py (ФИНАЛЬНАЯ ВЕРСИЯ С ДЕТАЛЯМИ)
import sqlite3
import requests
from time import sleep
from dotenv import load_dotenv
import os

load_dotenv()

TMDB_API_KEY = os.getenv('TMDB_API_KEY')
DB_PATH = 'content.db'

GENRE_MAP = {
    28: "action",
    12: "adventure",
    16: "animation",
    35: "comedy",
    80: "crime",
    99: "documentary",
    18: "drama",
    10751: "family",
    14: "fantasy",
    36: "history",
    27: "horror",
    10402: "music",
    9648: "mystery",
    10749: "romance",
    878: "sci-fi",
    53: "thriller",
    10752: "war",
    37: "western"
}

def get_epoch(year):
    if not year: return "unknown"
    if year >= 2023: return "new_releases"
    if year >= 2020: return "2020s"
    if year >= 2010: return "2010s"
    if year >= 2000: return "2000s"
    if year >= 1990: return "90s"
    if year >= 1980: return "80s"
    return "retro"

def get_criteria(rating, vote_count, popularity, year, genre_ids):
    """
    Улучшенная логика критериев
    
    Приоритет (сверху вниз):
    1. Оскар: рейтинг >= 8.2
    2. Культовый: возраст > 25 лет И рейтинг >= 7.8
    3. Хит проката: популярность > 80
    4. Скрытый шедевр: рейтинг >= 7.8 И голосов < 2000
    5. Артхаус: драма/документальный И рейтинг >= 7.5 И голосов < 1000
    6. Высокий рейтинг: рейтинг >= 7.5
    7. Популярный: всё остальное
    """
    
    # Оскар (топовые фильмы)
    if rating >= 8.2:
        return "oscar"
    
    # Культовый (старые хорошие)
    if year and (2024 - year) > 25 and rating >= 7.8:
        return "cult"
    
    # Хит проката (очень популярные)
    if popularity > 80:
        return "blockbuster"
    
    # Скрытый шедевр (недооценённые)
    if rating >= 7.8 and vote_count < 2000:
        return "hidden_gem"
    
    # Артхаус
    if (18 in genre_ids or 99 in genre_ids) and rating >= 7.5 and vote_count < 1000:
        return "arthouse"
    
    # Высокий рейтинг
    if rating >= 7.5:
        return "high_rated"
    
    return "popular"

def fetch_movie_details(movie_id):
    """
    Получить детальную информацию о фильме
    (включая vote_count и popularity)
    """
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {
        "api_key": TMDB_API_KEY,
        "language": "ru-RU"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"  ⚠️ Ошибка получения деталей: {e}")
        return None

def fetch_movies(genre_id, page=1):
    url = "https://api.themoviedb.org/3/discover/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "with_genres": genre_id,
        "sort_by": "vote_count.desc",
        "vote_count.gte": 500,
        "page": page,
        "language": "ru-RU"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("results", [])
    except Exception as e:
        print(f"❌ Ошибка API: {e}")
        return []

def save_movie(cursor, movie):
    """Сохранение фильма с детальной информацией"""
    
    # Получаем детали фильма
    details = fetch_movie_details(movie["id"])
    if not details:
        return False
    
    sleep(0.1)  # Пауза между запросами деталей
    
    year = None
    if details.get("release_date"):
        try:
            year = int(details["release_date"][:4])
        except:
            pass
    
    genre_ids = [g["id"] for g in details.get("genres", [])]
    genre = GENRE_MAP.get(genre_ids[0], "unknown") if genre_ids else "unknown"
    
    image_url = f"https://image.tmdb.org/t/p/w500{details['poster_path']}" if details.get("poster_path") else None
    description = details.get("overview", "")
    needs_ai = 1 if len(description) < 50 else 0
    
    # КРИТИЧНО: теперь у нас есть реальные данные
    rating = details.get("vote_average", 0)
    vote_count = details.get("vote_count", 0)
    popularity = details.get("popularity", 0)
    
    # Определяем критерий
    criteria = get_criteria(rating, vote_count, popularity, year, genre_ids)
    
    try:
        cursor.execute('''
            INSERT OR IGNORE INTO content 
            (type, title, description, image_url, year, rating, genre, epoch, criteria, source_id, needs_ai, creator)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "movie",
            details["title"],
            description,
            image_url,
            year,
            rating,
            genre,
            get_epoch(year),
            criteria,
            f"tmdb_{details['id']}",
            needs_ai,
            "TMDb"
        ))
        return True
    except Exception as e:
        print(f"  ⚠️ Ошибка БД: {e}")
        return False

def harvest():
    print("🎬 Начинаю сбор фильмов (с детальной информацией)...\n")
    print("⚠️ ВНИМАНИЕ: Это займёт больше времени из-за запроса деталей каждого фильма\n")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    total_saved = 0
    
    for genre_id, genre_name in GENRE_MAP.items():
        print(f"📂 Жанр: {genre_name}")
        
        # Уменьшаем до 3 страниц, чтобы не было слишком долго
        for page in range(1, 4):
            movies = fetch_movies(genre_id, page)
            if not movies:
                break
            
            saved_count = 0
            for i, movie in enumerate(movies, 1):
                print(f"  [{i}/{len(movies)}] {movie['title'][:40]}...", end=" ")
                
                if save_movie(cursor, movie):
                    saved_count += 1
                    print("✅")
                else:
                    print("⏭️")
            
            conn.commit()
            total_saved += saved_count
            print(f"  Страница {page}: сохранено {saved_count}/{len(movies)}")
            sleep(0.5)
        
        print()
    
    conn.close()
    print(f"\n🎉 Сбор окончен! Всего сохранено: {total_saved}")

if __name__ == "__main__":
    if not TMDB_API_KEY:
        print("❌ Нет ключа TMDB_API_KEY в .env")
    else:
        harvest()