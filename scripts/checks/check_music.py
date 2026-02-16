# check_music.py
import sqlite3

conn = sqlite3.connect('content.db')
cursor = conn.cursor()

# Случайные 10 треков
cursor.execute('''
    SELECT title, creator, genre, year, mood, criteria 
    FROM content 
    WHERE type='music' 
    ORDER BY RANDOM() 
    LIMIT 10
''')

print("🎵 Случайные треки:\n")
for row in cursor.fetchall():
    print(f"  {row[0][:40]} - {row[1][:30]} ({row[3]}) [{row[2]}] - {row[4]} - {row[5]}")

# По жанрам
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

# По mood
print("\n🎭 По настроениям:")
cursor.execute('''
    SELECT mood, COUNT(*) 
    FROM content 
    WHERE type='music' 
    GROUP BY mood
    ORDER BY COUNT(*) DESC
''')
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} треков")

# По критериям
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

# По эпохам
print("\n📅 По эпохам:")
cursor.execute('''
    SELECT epoch, COUNT(*) 
    FROM content 
    WHERE type='music' 
    GROUP BY epoch
    ORDER BY epoch DESC
''')
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} треков")

# Итоговая статистика по всему контенту
print("\n" + "="*50)
print("📊 ИТОГОВАЯ СТАТИСТИКА БАЗЫ ДАННЫХ")
print("="*50)

cursor.execute('''
    SELECT type, COUNT(*) 
    FROM content 
    GROUP BY type
''')
print("\n📦 По типам контента:")
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} элементов")

cursor.execute('SELECT COUNT(*) FROM content')
total = cursor.fetchone()[0]
print(f"\n🎉 ВСЕГО В БАЗЕ: {total} элементов контента!")

conn.close()