#!/usr/bin/env python3
# check_stats.py - Быстрая статистика БД

import sqlite3

DB_PATH = 'content.db'

def show_stats():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 50)
    print("📊 СТАТИСТИКА БАЗЫ ДАННЫХ")
    print("=" * 50)
    
    # Общее количество
    cursor.execute("SELECT COUNT(*) FROM content")
    total = cursor.fetchone()[0]
    print(f"\n📚 ВСЕГО ЭЛЕМЕНТОВ: {total:,}")
    
    # По типам
    print("\n📋 По типам:")
    cursor.execute("""
        SELECT 
            CASE type
                WHEN 'book' THEN '📖 Книги'
                WHEN 'movie' THEN '🎬 Фильмы'
                WHEN 'music' THEN '🎵 Музыка'
                ELSE type
            END as type_name,
            COUNT(*) as count
        FROM content 
        GROUP BY type
        ORDER BY count DESC
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,}")
    
    # Топ жанров
    print("\n🎭 Топ-5 жанров:")
    cursor.execute("""
        SELECT genre, COUNT(*) as count 
        FROM content 
        GROUP BY genre 
        ORDER BY count DESC 
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,}")
    
    # По эпохам
    print("\n📅 По эпохам:")
    cursor.execute("""
        SELECT epoch, COUNT(*) as count 
        FROM content 
        GROUP BY epoch 
        ORDER BY count DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]:,}")
    
    # Нужен AI
    cursor.execute("SELECT COUNT(*) FROM content WHERE needs_ai = 1")
    needs_ai = cursor.fetchone()[0]
    print(f"\n⚡ Нужно AI-описаний: {needs_ai:,}")
    
    print("\n" + "=" * 50)
    
    conn.close()

if __name__ == "__main__":
    try:
        show_stats()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
