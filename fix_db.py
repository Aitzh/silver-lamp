import sqlite3
conn = sqlite3.connect('access.db')
# Это сделает ВСЕ коды в базе многоразовыми на 20 раз для теста
conn.execute("UPDATE access_codes SET max_activations = 20, current_activations = 0, is_used = 0")
conn.commit()
conn.close()
print("База зачищена, все коды теперь на 20 входов!")