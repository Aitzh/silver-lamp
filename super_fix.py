import sqlite3
import os

# 1. Определяем правильный путь к базе
# Мы ищем папку backend, если она есть — кладем базу туда.
if os.path.exists('backend'):
    db_folder = 'backend'
    db_path = os.path.join(db_folder, 'access.db')
else:
    # Если папки backend нет, кладем рядом со скриптом
    db_folder = '.'
    db_path = 'access.db'

print(f"🔧 Начинаем ремонт базы данных по пути: {db_path}")

# Создаем папку, если её нет (на всякий случай)
if not os.path.exists(db_folder) and db_folder != '.':
    os.makedirs(db_folder)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 2. Создаем таблицу ПРАВИЛЬНО (если её нет - ошибка 'no such table' уйдет)
# Мы сразу добавляем max_activations и current_activations
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
        max_activations INTEGER DEFAULT 1,
        current_activations INTEGER DEFAULT 0
    )
''')
print("✅ Таблица проверена/создана.")

# 3. Проверяем, есть ли новые колонки (для старых баз)
# Пытаемся добавить колонки, если их нет. Игнорируем ошибку, если они уже есть.
try:
    cursor.execute("ALTER TABLE access_codes ADD COLUMN max_activations INTEGER DEFAULT 1")
    print("✅ Добавлена колонка max_activations")
except sqlite3.OperationalError:
    pass # Колонка уже есть

try:
    cursor.execute("ALTER TABLE access_codes ADD COLUMN current_activations INTEGER DEFAULT 0")
    print("✅ Добавлена колонка current_activations")
except sqlite3.OperationalError:
    pass # Колонка уже есть

# 4. Чиним твой конкретный код VF6S-PA8E
code_to_fix = "VF6S-PA8E"

# Сначала проверим, существует ли он вообще
cursor.execute("SELECT count(*) FROM access_codes WHERE code = ?", (code_to_fix,))
exists = cursor.fetchone()[0]

if exists == 0:
    # Если кода нет (база была пустой), создадим его с нуля
    print(f"⚠️ Код {code_to_fix} не найден (база была пустой), создаю его заново...")
    cursor.execute('''
        INSERT INTO access_codes (code, code_type, duration_hours, max_activations, current_activations, is_used)
        VALUES (?, '1day', 24, 100, 0, 0)
    ''', (code_to_fix,))
else:
    # Если код есть, обновляем его
    print(f"🔄 Код {code_to_fix} найден, обновляем лимиты...")
    cursor.execute("""
        UPDATE access_codes 
        SET max_activations = 100, 
            is_used = 0,
            current_activations = 0,
            expires_at = NULL,
            used_at = NULL
        WHERE code = ?
    """, (code_to_fix,))

conn.commit()
conn.close()

print(f"\n🎉 ГОТОВО! Код {code_to_fix} теперь активен и имеет 100 попыток.")
print("❗ НЕ ЗАБУДЬ: Перезагрузи сервер (Ctrl+C -> node server.js), чтобы он увидел изменения.")