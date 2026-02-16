# harvest_books.py (УПРОЩЁННАЯ ВЕРСИЯ v1.0)
import sqlite3
import requests
from time import sleep
from dotenv import load_dotenv
import os
import re

load_dotenv()

DB_PATH = 'content.db'
GOOGLE_BOOKS_KEY = os.getenv('GOOGLE_BOOKS_API_KEY')

BOOK_GENRES = {
    "fantasy": "subject:fantasy",
    "sci-fi": "subject:science+fiction",
    "mystery": "subject:mystery",
    "thriller": "subject:thriller",
    "classics": "subject:classics",
    "non-fiction": "subject:nonfiction",
    "romance": "subject:romance",
    "adventure": "subject:adventure",
    "historical": "subject:historical+fiction",
    "philosophy": "subject:philosophy",
    "psychology": "subject:psychology",
    "dystopian": "subject:dystopian"
}

# Список известных авторов для определения бестселлеров
BESTSELLER_AUTHORS = [
    "stephen king", "j.k. rowling", "agatha christie", "dan brown",
    "john grisham", "james patterson", "george r.r. martin",
    "neil gaiman", "haruki murakami", "paulo coelho", "tolkien",
    "asimov", "bradbury", "herbert", "orwell", "huxley"
]

def get_book_epoch(year):
    if not year: return "unknown"
    if year >= 2024: return "bestsellers_2025"
    if year >= 2020: return "2020s"
    if year >= 2010: return "2010s"
    if year >= 2000: return "2000s"
    if year >= 1990: return "90s"
    if year >= 1980: return "80s"
    if year >= 1950: return "golden_classics"
    return "retro"

def get_book_criteria(year, genre_name, authors, description):
    """
    Упрощённые критерии для v1.0
    """
    authors_lower = authors.lower()
    
    # Бестселлер (известный автор)
    if any(author in authors_lower for author in BESTSELLER_AUTHORS):
        return "bestseller"
    
    # Классика (старые книги)
    if year and year < 1990:
        return "classic"
    
    # Интеллектуальная (нон-фикшн, философия, психология)
    if genre_name in ["philosophy", "psychology", "non-fiction"]:
        return "intellectual"
    
    # Культовая (фантастика/фэнтези 90-2000-х)
    if genre_name in ["sci-fi", "fantasy", "dystopian"] and year and 1990 <= year < 2010:
        return "cult"
    
    # Современная (новинки)
    if year and year >= 2020:
        return "modern"
    
    # Скрытый шедевр (длинное описание + малоизвестный автор)
    if len(description) > 500 and not any(author in authors_lower for author in BESTSELLER_AUTHORS):
        return "hidden_gem"
    
    return "popular"

def normalize_title(title):
    normalized = re.sub(r'[^a-z0-9\s]', '', title.lower())
    normalized = ' '.join(normalized.split())
    return normalized

def is_duplicate(cursor, title, authors):
    norm_title = normalize_title(title)
    first_author = authors.split(',')[0].strip() if authors != "Unknown" else ""
    
    if not first_author:
        return False
    
    cursor.execute('''
        SELECT COUNT(*) FROM content 
        WHERE type='book' 
        AND LOWER(REPLACE(REPLACE(REPLACE(title, ':', ''), '.', ''), ',', '')) LIKE ?
        AND creator LIKE ?
    ''', (f"%{norm_title}%", f"%{first_author}%"))
    
    count = cursor.fetchone()[0]
    return count > 0

def fetch_books(query, max_results=40, start_index=0):
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {
        "q": query,
        "maxResults": max_results,
        "startIndex": start_index,
        "orderBy": "relevance",
        "printType": "books",
        "langRestrict": "en"
    }
    
    if GOOGLE_BOOKS_KEY:
        params["key"] = GOOGLE_BOOKS_KEY
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        return response.json().get("items", [])
    except Exception as e:
        print(f"❌ Ошибка API: {e}")
        return []

def save_book(cursor, item, genre_name):
    info = item.get("volumeInfo", {})
    
    title = info.get("title")
    if not title or len(title) < 2:
        return False
    
    authors = ", ".join(info.get("authors", [])) if info.get("authors") else "Unknown"
    
    # Проверка на дубль
    if is_duplicate(cursor, title, authors):
        return False
    
    description = info.get("description", "")
    
    # Пропускаем без описания
    if len(description) < 50:
        return False
    
    # Год
    pub_date = info.get("publishedDate", "")
    year = None
    if pub_date:
        try:
            year = int(pub_date[:4])
        except:
            pass
    
    # Фильтр по году
    if year and (year < 1900 or year > 2025):
        return False
    
    # Картинка
    image_links = info.get("imageLinks", {})
    image_url = None
    if image_links:
        image_url = (
            image_links.get("large") or 
            image_links.get("medium") or 
            image_links.get("small") or 
            image_links.get("thumbnail")
        )
        if image_url:
            image_url = image_url.replace("http://", "https://")
            # Убираем &edge=curl (некрасивый эффект)
            image_url = image_url.split("&edge=")[0]
    
    # Рейтинг (может быть None)
    rating = info.get("averageRating", 0) or 0
    
    # НОВАЯ ЛОГИКА критериев
    criteria = get_book_criteria(year, genre_name, authors, description)
    
    needs_ai = 1
    
    try:
        cursor.execute('''
            INSERT INTO content 
            (type, title, creator, description, image_url, year, rating, genre, epoch, criteria, source_id, needs_ai)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "book",
            title,
            authors,
            description[:500],  # Обрезаем длинные описания
            image_url,
            year,
            rating,
            genre_name,
            get_book_epoch(year),
            criteria,
            f"gb_{item['id']}",
            needs_ai
        ))
        return True
    except Exception as e:
        return False

def harvest():
    print("📚 Начинаю сбор книг (упрощённые критерии)...\n")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Очищаем старые книги
    cursor.execute("DELETE FROM content WHERE type='book'")
    conn.commit()
    print("🗑️ Старые книги удалены\n")
    
    total_saved = 0
    
    for genre_name, api_query in BOOK_GENRES.items():
        print(f"📖 Жанр: {genre_name}")
        genre_count = 0
        
        for page in range(5):
            books = fetch_books(api_query, max_results=40, start_index=page*40)
            
            if not books:
                break
            
            saved_count = 0
            for book in books:
                if save_book(cursor, book, genre_name):
                    saved_count += 1
            
            conn.commit()
            total_saved += saved_count
            genre_count += saved_count
            
            print(f"  Страница {page+1}: +{saved_count} книг")
            
            sleep(1)
            
            # Лимит 100 на жанр
            if genre_count >= 100:
                break
        
        print(f"  ✅ Итого: {genre_count} книг\n")
    
    conn.close()
    print(f"\n🎉 Готово! Сохранено: {total_saved} книг")
    
    # Статистика
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("\n📚 По жанрам:")
    cursor.execute('''
        SELECT genre, COUNT(*) 
        FROM content 
        WHERE type='book' 
        GROUP BY genre
        ORDER BY COUNT(*) DESC
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} книг")
    
    print("\n📊 По критериям:")
    cursor.execute('''
        SELECT criteria, COUNT(*) 
        FROM content 
        WHERE type='book' 
        GROUP BY criteria
        ORDER BY COUNT(*) DESC
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} книг")
    
    print("\n📅 По эпохам:")
    cursor.execute('''
        SELECT epoch, COUNT(*) 
        FROM content 
        WHERE type='book' 
        GROUP BY epoch
        ORDER BY epoch DESC
    ''')
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} книг")
    
    conn.close()

if __name__ == "__main__":
    harvest()