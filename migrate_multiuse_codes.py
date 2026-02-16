#!/usr/bin/env python3
"""
🔄 МИГРАЦИЯ: Поддержка многоразовых кодов

Добавляет новые поля в таблицу access_codes:
- max_activations: максимальное количество активаций (NULL = одноразовый код)
- current_activations: текущее количество активаций

Использование:
    python migrate_multiuse_codes.py
"""

import sqlite3
import os

DB_PATH = os.getenv('ACCESS_DB_PATH', 'access.db')

def migrate():
    """Выполнить миграцию базы данных"""
    
    print("🔄 Начинаем миграцию базы данных...")
    print(f"📁 База данных: {DB_PATH}\n")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ ОШИБКА: База данных не найдена: {DB_PATH}")
        print("💡 Запустите сначала: python setup_access_database.py")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Проверяем существование полей
        cursor.execute("PRAGMA table_info(access_codes)")
        columns = [row[1] for row in cursor.fetchall()]
        
        changes_made = False
        
        # 1. Добавляем колонки, если их нет
        if 'max_activations' not in columns:
            print("➕ Добавляем поле: max_activations")
            cursor.execute('''
                ALTER TABLE access_codes 
                ADD COLUMN max_activations INTEGER DEFAULT NULL
            ''')
            changes_made = True
        else:
            print("✓ Поле max_activations уже существует")
        
        if 'current_activations' not in columns:
            print("➕ Добавляем поле: current_activations")
            cursor.execute('''
                ALTER TABLE access_codes 
                ADD COLUMN current_activations INTEGER DEFAULT 0
            ''')
            changes_made = True
        else:
            print("✓ Поле current_activations уже существует")
        
        if changes_made:
            print("✅ Структура таблицы обновлена (добавлены новые колонки).")
        else:
            print("ℹ️ Структура таблицы уже актуальна.")

        # 2. БЕЗУСЛОВНОЕ ОБНОВЛЕНИЕ ДАННЫХ
        # Исправляем NULL значения для старых кодов, чтобы они стали корректными одноразовыми
        print("🔧 Проверка и исправление данных в существующих кодах...")
        cursor.execute('''
            UPDATE access_codes 
            SET 
                max_activations = 1,
                current_activations = CASE WHEN is_used = 1 THEN 1 ELSE 0 END
            WHERE max_activations IS NULL
        ''')
        
        conn.commit()
        print("✅ Данные синхронизированы.")
        
        # 3. Показываем статистику
        cursor.execute('SELECT COUNT(*) FROM access_codes')
        total_codes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM access_codes WHERE max_activations IS NOT NULL')
        processed_codes = cursor.fetchone()[0]
        
        print(f"\n📊 Статистика после миграции:")
        print(f"   Всего кодов в базе: {total_codes}")
        print(f"   Кодов с настроенным лимитом: {processed_codes}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ ОШИБКА при миграции: {e}")
        conn.rollback()
        conn.close()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔧 Coffee Books AI - Миграция базы данных")
    print("=" * 60)
    print()
    
    success = migrate()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ Готово! Теперь база поддерживает многоразовые коды.")
    else:
        print("❌ Миграция завершилась с ошибкой.")
    print("=" * 60)