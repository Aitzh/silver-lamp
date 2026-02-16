# check_all_values.py
import sqlite3

conn = sqlite3.connect('content.db')
cursor = conn.cursor()

print("=" * 60)
print("📊 АКТУАЛЬНЫЕ ЗНАЧЕНИЯ В БАЗЕ ДАННЫХ")
print("=" * 60)

# === ФИЛЬМЫ ===
print("\n🎬 ФИЛЬМЫ:")
print("\nЖанры:")
cursor.execute('''
    SELECT DISTINCT genre FROM content 
    WHERE type='movie' AND genre IS NOT NULL
    ORDER BY genre
''')
for row in cursor.fetchall():
    print(f"  - {row[0]}")

print("\nЭпохи:")
cursor.execute('''
    SELECT DISTINCT epoch FROM content 
    WHERE type='movie' AND epoch IS NOT NULL
    ORDER BY epoch
''')
for row in cursor.fetchall():
    print(f"  - {row[0]}")

print("\nКритерии:")
cursor.execute('''
    SELECT DISTINCT criteria FROM content 
    WHERE type='movie' AND criteria IS NOT NULL
    ORDER BY criteria
''')
for row in cursor.fetchall():
    print(f"  - {row[0]}")

# === КНИГИ ===
print("\n\n📚 КНИГИ:")
print("\nЖанры:")
cursor.execute('''
    SELECT DISTINCT genre FROM content 
    WHERE type='book' AND genre IS NOT NULL
    ORDER BY genre
''')
for row in cursor.fetchall():
    print(f"  - {row[0]}")

print("\nЭпохи:")
cursor.execute('''
    SELECT DISTINCT epoch FROM content 
    WHERE type='book' AND epoch IS NOT NULL
    ORDER BY epoch
''')
for row in cursor.fetchall():
    print(f"  - {row[0]}")

print("\nКритерии:")
cursor.execute('''
    SELECT DISTINCT criteria FROM content 
    WHERE type='book' AND criteria IS NOT NULL
    ORDER BY criteria
''')
for row in cursor.fetchall():
    print(f"  - {row[0]}")

# === МУЗЫКА ===
print("\n\n🎵 МУЗЫКА:")
print("\nЖанры:")
cursor.execute('''
    SELECT DISTINCT genre FROM content 
    WHERE type='music' AND genre IS NOT NULL
    ORDER BY genre
''')
for row in cursor.fetchall():
    print(f"  - {row[0]}")

print("\nНастроения (MOOD):")
cursor.execute('''
    SELECT DISTINCT mood FROM content 
    WHERE type='music' AND mood IS NOT NULL
    ORDER BY mood
''')
for row in cursor.fetchall():
    print(f"  - {row[0]}")

print("\nКритерии:")
cursor.execute('''
    SELECT DISTINCT criteria FROM content 
    WHERE type='music' AND criteria IS NOT NULL
    ORDER BY criteria
''')
for row in cursor.fetchall():
    print(f"  - {row[0]}")

conn.close()

print("\n" + "=" * 60)
print("✅ ГОТОВО! Используй эти значения для обновления фронтенда")
print("=" * 60)