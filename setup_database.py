import sqlite3
import os

# Получаем абсолютный путь к текущей папке
current_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(current_dir, 'content.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# (Ваш код создания таблицы остается прежним)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS content (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT NOT NULL,
        title TEXT NOT NULL,
        creator TEXT,
        description TEXT,
        image_url TEXT,
        year INTEGER,
        rating REAL,
        mood TEXT,
        genre TEXT,
        epoch TEXT,
        needs_ai INTEGER DEFAULT 0,
        source_id TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

conn.commit()
conn.close()

print(f"✅ База данных создана успешно!")
print(f"📍 Путь к файлу: {db_path}")