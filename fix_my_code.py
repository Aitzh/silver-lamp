import sqlite3
import os

# Путь к базе данных
db_path = 'backend/routes/access.db'

# Проверяем путь, чтобы точно найти базу
if not os.path.exists(db_path):
    print(f"❌ База не найдена по пути: {db_path}")
    print("Попробуй запустить скрипт из корневой папки проекта.")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Обновляем твой тестовый код VF6S-PA8E
    # Ставим ему 100 активаций и сбрасываем флаг использования
    code_to_fix = "VF6S-PA8E"
    
    try:
        cursor.execute("""
            UPDATE access_codes 
            SET max_activations = 100, 
                is_used = 0,
                current_activations = 0 
            WHERE code = ?
        """, (code_to_fix,))
        
        conn.commit()
        
        if cursor.rowcount > 0:
            print(f"✅ Код {code_to_fix} обновлен! Теперь у него 100 активаций.")
        else:
            print(f"⚠️ Код {code_to_fix} не найден в базе. Проверь, правильно ли он написан.")
            
    except Exception as e:
        print(f"Ошибка: {e}")
        
    conn.close()