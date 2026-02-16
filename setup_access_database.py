#!/usr/bin/env python3
"""
🔐 SETUP ACCESS DATABASE - Настройка системы доступа Coffee Books AI

Создаёт таблицы для:
- Кодов доступа
- Сессий пользователей
- Логов активности
- Администраторов

Использование:
    python setup_access_database.py
    python setup_access_database.py --add-admin 123456789 "Имя Админа"
"""

import sqlite3
import os
import argparse
from datetime import datetime

DB_PATH = os.getenv('ACCESS_DB_PATH', 'access.db')

def create_access_database():
    """Создать базу данных для системы доступа"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
# ============ ТАБЛИЦА: access_codes ============
    # Обновленная версия с поддержкой многоразовых кодов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS access_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE NOT NULL,
            code_type TEXT NOT NULL CHECK(code_type IN ('1day', '7days', '30days')),
            duration_hours INTEGER NOT NULL,
            generated_by TEXT,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_used INTEGER DEFAULT 0,
            used_at TIMESTAMP,
            used_by_session TEXT,
            expires_at TIMESTAMP,
            notes TEXT,
            max_activations INTEGER DEFAULT 1,     -- Новое поле
            current_activations INTEGER DEFAULT 0  -- Новое поле
        )
    ''')
    
    # ============ ТАБЛИЦА: user_sessions ============
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_token TEXT UNIQUE NOT NULL,
            access_code_id INTEGER,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            is_active INTEGER DEFAULT 1,
            last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            codes_generated_count INTEGER DEFAULT 0,
            FOREIGN KEY (access_code_id) REFERENCES access_codes(id)
        )
    ''')
    
    # ============ ТАБЛИЦА: activity_logs ============
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activity_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_token TEXT,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_token) REFERENCES user_sessions(session_token)
        )
    ''')
    
    # ============ ТАБЛИЦА: admin_users ============
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id TEXT UNIQUE NOT NULL,
            username TEXT,
            full_name TEXT,
            is_active INTEGER DEFAULT 1,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP,
            codes_generated_total INTEGER DEFAULT 0
        )
    ''')
    
    # ============ ИНДЕКСЫ ============
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_codes_type ON access_codes(code_type)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_codes_used ON access_codes(is_used)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_codes_code ON access_codes(code)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_active ON user_sessions(is_active)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_expires ON user_sessions(expires_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_sessions_token ON user_sessions(session_token)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON activity_logs(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_admin_telegram ON admin_users(telegram_id)')
    
    conn.commit()
    
    print("✅ База данных создана: " + DB_PATH)
    print("\n📋 Созданные таблицы:")
    print("  1. access_codes - Коды доступа")
    print("  2. user_sessions - Сессии пользователей")
    print("  3. activity_logs - Логи активности")
    print("  4. admin_users - Администраторы")
    
    conn.close()

def add_admin(telegram_id, full_name=None, username=None):
    """Добавить администратора"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO admin_users (telegram_id, username, full_name)
            VALUES (?, ?, ?)
        ''', (str(telegram_id), username, full_name))
        
        conn.commit()
        print(f"\n✅ Администратор добавлен:")
        print(f"   Telegram ID: {telegram_id}")
        if full_name:
            print(f"   Имя: {full_name}")
        if username:
            print(f"   Username: @{username}")
        
    except sqlite3.IntegrityError:
        print(f"\n⚠️ Администратор {telegram_id} уже существует")
    
    finally:
        conn.close()

def list_admins():
    """Показать список админов"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT telegram_id, username, full_name, is_active, codes_generated_total, last_seen
        FROM admin_users
        ORDER BY is_active DESC, codes_generated_total DESC
    ''')
    
    admins = cursor.fetchall()
    conn.close()
    
    print("\n👥 Список администраторов:")
    print("-" * 60)
    
    if not admins:
        print("   Нет администраторов")
        return
    
    for admin in admins:
        tid, username, name, is_active, codes, last_seen = admin
        status = "✅ Активен" if is_active else "❌ Неактивен"
        print(f"\n   ID: {tid}")
        print(f"   Имя: {name or 'Не указано'}")
        if username:
            print(f"   Username: @{username}")
        print(f"   Статус: {status}")
        print(f"   Кодов создано: {codes}")

def show_stats():
    """Показать статистику"""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Статистика кодов
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN is_used = 1 THEN 1 ELSE 0 END) as used,
            SUM(CASE WHEN is_used = 0 THEN 1 ELSE 0 END) as unused
        FROM access_codes
    ''')
    stats = cursor.fetchone()
    
    # Активные сессии
    cursor.execute('''
        SELECT COUNT(*) FROM user_sessions 
        WHERE is_active = 1 AND expires_at > datetime('now')
    ''')
    active_sessions = cursor.fetchone()[0]
    
    # Админы
    cursor.execute('SELECT COUNT(*) FROM admin_users WHERE is_active = 1')
    admin_count = cursor.fetchone()[0]
    
    conn.close()
    
    print("\n📊 Статистика системы:")
    print("-" * 40)
    print(f"   Всего кодов: {stats[0] or 0}")
    print(f"   Использовано: {stats[1] or 0}")
    print(f"   Доступно: {stats[2] or 0}")
    print(f"   Активных сессий: {active_sessions}")
    print(f"   Администраторов: {admin_count}")

def main():
    parser = argparse.ArgumentParser(description='Настройка системы доступа Coffee Books AI')
    parser.add_argument('--add-admin', nargs='+', metavar=('ID', 'NAME'), 
                        help='Добавить администратора (ID и опционально имя)')
    parser.add_argument('--list-admins', action='store_true', 
                        help='Показать список админов')
    parser.add_argument('--stats', action='store_true', 
                        help='Показать статистику')
    
    args = parser.parse_args()
    
    print("🔐 Coffee Books AI - Настройка системы доступа")
    print("=" * 50)
    
    # Создаём базу данных если не существует
    if not os.path.exists(DB_PATH):
        create_access_database()
    else:
        print(f"✅ База данных найдена: {DB_PATH}")
    
    # Выполняем команды
    if args.add_admin:
        telegram_id = args.add_admin[0]
        full_name = ' '.join(args.add_admin[1:]) if len(args.add_admin) > 1 else None
        add_admin(telegram_id, full_name)
    
    if args.list_admins:
        list_admins()
    
    if args.stats:
        show_stats()
    
    # Если нет аргументов - показываем инструкцию
    if not any([args.add_admin, args.list_admins, args.stats]):
        # Добавляем дефолтного админа если БД только что создана
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM admin_users')
        admin_count = cursor.fetchone()[0]
        conn.close()
        
        if admin_count == 0:
            # Добавляем первого администратора
            SUPER_ADMIN_ID = os.getenv('SUPER_ADMIN_ID', '1530115915')
            add_admin(SUPER_ADMIN_ID, "Aitzhan", "itekwai")
        
        show_stats()
        list_admins()
        
        print("\n" + "=" * 50)
        print("💡 Команды:")
        print("   python setup_access_database.py --add-admin 123456 'Имя'")
        print("   python setup_access_database.py --list-admins")
        print("   python setup_access_database.py --stats")

if __name__ == "__main__":
    main()