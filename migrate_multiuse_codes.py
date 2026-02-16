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
        
        # Добавляем max_activations если не существует
        if 'max_activations' not in columns:
            print("➕ Добавляем поле: max_activations")
            cursor.execute('''
                ALTER TABLE access_codes 
                ADD COLUMN max_activations INTEGER DEFAULT NULL
            ''')
            changes_made = True
        else:
            print("✓ Поле max_activations уже существует")
        
        # Добавляем current_activations если не существует
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
            # Обновляем существующие коды: ставим лимит 1 и текущие активации
            print("🔧 Обновляем существующие коды...")
            cursor.execute('''
                UPDATE access_codes 
                SET 
                    max_activations = 1,
                    current_activations = CASE WHEN is_used = 1 THEN 1 ELSE 0 END
                WHERE max_activations IS NULL
            ''')
            
            conn.commit()
            print("\n✅ Миграция успешно выполнена!")
        else:
            print("\n✅ База данных уже актуальна, изменения не требуются")
        
        # Показываем статистику
        cursor.execute('SELECT COUNT(*) FROM access_codes')
        total_codes = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM access_codes WHERE max_activations IS NOT NULL')
        multiuse_codes = cursor.fetchone()[0]
        
        print(f"\n📊 Статистика:")
        print(f"   Всего кодов: {total_codes}")
        print(f"   Многоразовых кодов: {multiuse_codes}")
        print(f"   Одноразовых кодов: {total_codes - multiuse_codes}")
        
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
        print("✅ Готово! Теперь можно генерировать многоразовые коды.")
    else:
        print("❌ Миграция не выполнена. Проверьте ошибки выше.")
    print("=" * 60)
