# check_movies.py (ОБНОВЛЁННАЯ ВЕРСИЯ)
import sqlite3

conn = sqlite3.connect('content.db')
cursor = conn.cursor()

# Случайные фильмы
cursor.execute('''
    SELECT title, genre, epoch, criteria, rating 
    FROM content 
    WHERE type='movie' 
    ORDER BY RANDOM() 
    LIMIT 10
''')

print("🎬 Случайные фильмы:\n")
for row in cursor.fetchall():
    print(f"  {row[0]} - {row[1]} - {row[2]} - [{row[3]}] - ⭐{row[4]}")

# Статистика по критериям
print("\n📊 Статистика по критериям:")
cursor.execute('''
    SELECT criteria, COUNT(*) 
    FROM content 
    WHERE type='movie' 
    GROUP BY criteria
    ORDER BY COUNT(*) DESC
''')

for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} фильмов")

# Статистика по эпохам
print("\n📅 Статистика по эпохам:")
cursor.execute('''
    SELECT epoch, COUNT(*) 
    FROM content 
    WHERE type='movie' 
    GROUP BY epoch
    ORDER BY epoch DESC
''')

for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} фильмов")

conn.close()