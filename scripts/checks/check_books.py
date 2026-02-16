# check_books.py
import sqlite3

conn = sqlite3.connect('content.db')
cursor = conn.cursor()

cursor.execute('''
    SELECT title, creator, genre, year, criteria 
    FROM content 
    WHERE type='book' 
    ORDER BY RANDOM() 
    LIMIT 10
''')

print("📚 Случайные книги:\n")
for row in cursor.fetchall():
    print(f"  {row[0][:50]} - {row[1][:30]} ({row[3]}) - [{row[4]}]")

print("\n📊 Статистика по критериям:")
cursor.execute('''
    SELECT criteria, COUNT(*) 
    FROM content 
    WHERE type='book' 
    GROUP BY criteria
''')
for row in cursor.fetchall():
    print(f"  {row[0]}: {row[1]} книг")

conn.close()