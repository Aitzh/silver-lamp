#!/usr/bin/env python3
"""
🔄 FIX DUPLICATES - Удаление дубликатов из базы данных

Назначение:
- Находит дубликаты по (title + creator + type)
- Выбирает лучшую версию (наибольшее количество заполненных полей)
- Удаляет остальные копии
- Создает детальный отчет об удаленных записях

Автор: Coffee Books AI Team
Версия: 1.0
"""

import sqlite3
import shutil
import os
import json
from datetime import datetime
from typing import List, Dict, Tuple
from collections import defaultdict

# ==================== КОНСТАНТЫ ====================

DB_PATH = 'content.db'
BACKUP_DIR = 'backups'
REPORT_DIR = 'reports'

# Поля для оценки качества записи
QUALITY_FIELDS = [
    'description',
    'image_url',
    'year',
    'rating',
    'mood',
    'genre',
    'epoch'
]

# ==================== КЛАСС ДЛЯ РАБОТЫ С ДУБЛИКАТАМИ ====================

class DuplicateFixer:
    """Класс для поиска и удаления дубликатов"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.backup_path = None
        self.report_path = None
        self.conn = None
        self.cursor = None
        self.duplicates = []
        self.deleted_records = []
        self.stats = {
            'total_duplicate_groups': 0,
            'total_records_before': 0,
            'total_records_after': 0,
            'records_deleted': 0,
            'records_kept': 0
        }
    
    def create_backup(self) -> bool:
        """Создание резервной копии базы данных"""
        try:
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.backup_path = os.path.join(BACKUP_DIR, f'content_backup_{timestamp}.db')
            
            shutil.copy2(self.db_path, self.backup_path)
            
            print(f"✅ Backup создан: {self.backup_path}")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания backup: {e}")
            return False
    
    def connect(self) -> bool:
        """Подключение к базе данных"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            return True
        except sqlite3.Error as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            return False
    
    def close(self):
        """Закрытие соединения"""
        if self.conn:
            self.conn.close()
    
    def normalize_string(self, s: str) -> str:
        """Нормализация строки для сравнения"""
        if not s:
            return ""
        # Приводим к нижнему регистру и убираем пробелы по краям
        return s.lower().strip()
    
    def calculate_record_quality(self, record: sqlite3.Row) -> int:
        """Вычислить качество записи (количество заполненных полей)"""
        quality_score = 0
        
        for field in QUALITY_FIELDS:
            if field in record.keys():
                value = record[field]
                # Проверяем что поле не пустое
                if value is not None and str(value).strip():
                    quality_score += 1
        
        # Дополнительные баллы за AI описание
        if record['needs_ai'] == 0:
            quality_score += 2
        
        # Дополнительный балл за source_id (оригинальный ID из API)
        if record['source_id']:
            quality_score += 1
        
        return quality_score
    
    def find_duplicates(self) -> List[Dict]:
        """Найти все группы дубликатов"""
        print("\n🔍 ПОИСК ДУБЛИКАТОВ")
        print("=" * 70)
        
        # Находим группы дубликатов по normalized title + creator + type
        self.cursor.execute("""
            SELECT 
                LOWER(TRIM(title)) as normalized_title,
                LOWER(TRIM(COALESCE(creator, ''))) as normalized_creator,
                type,
                COUNT(*) as count,
                GROUP_CONCAT(id) as ids
            FROM content
            GROUP BY normalized_title, normalized_creator, type
            HAVING count > 1
            ORDER BY count DESC, type, normalized_title
        """)
        
        duplicate_groups = self.cursor.fetchall()
        
        print(f"Найдено групп дубликатов: {len(duplicate_groups)}")
        
        # Для каждой группы получаем детальную информацию
        for group in duplicate_groups:
            ids = [int(id_str) for id_str in group['ids'].split(',')]
            
            # Получаем полную информацию о каждой записи
            placeholders = ','.join(['?' for _ in ids])
            self.cursor.execute(f"""
                SELECT * FROM content 
                WHERE id IN ({placeholders})
                ORDER BY id
            """, ids)
            
            records = self.cursor.fetchall()
            
            # Создаем группу дубликатов
            duplicate_group = {
                'title': group['normalized_title'],
                'creator': group['normalized_creator'],
                'type': group['type'],
                'count': group['count'],
                'records': []
            }
            
            # Оцениваем качество каждой записи
            for record in records:
                quality_score = self.calculate_record_quality(record)
                
                record_info = {
                    'id': record['id'],
                    'title': record['title'],
                    'creator': record['creator'],
                    'type': record['type'],
                    'quality_score': quality_score,
                    'description': record['description'][:50] + '...' if record['description'] else None,
                    'image_url': 'Yes' if record['image_url'] else 'No',
                    'year': record['year'],
                    'rating': record['rating'],
                    'needs_ai': record['needs_ai'],
                    'source_id': record['source_id']
                }
                
                duplicate_group['records'].append(record_info)
            
            # Сортируем записи по качеству (лучшие первыми)
            duplicate_group['records'].sort(key=lambda x: x['quality_score'], reverse=True)
            
            self.duplicates.append(duplicate_group)
        
        self.stats['total_duplicate_groups'] = len(self.duplicates)
        
        return self.duplicates
    
    def show_duplicates(self):
        """Показать найденные дубликаты"""
        print("\n📋 ДЕТАЛЬНАЯ ИНФОРМАЦИЯ О ДУБЛИКАТАХ")
        print("=" * 70)
        
        for i, group in enumerate(self.duplicates, 1):
            emoji = {'book': '📖', 'movie': '🎬', 'music': '🎵'}[group['type']]
            
            print(f"\n{i}. {emoji} '{group['title']}'")
            if group['creator']:
                print(f"   Автор/Исполнитель: {group['creator']}")
            print(f"   Тип: {group['type']} | Копий: {group['count']}")
            print(f"   ─" * 35)
            
            for j, record in enumerate(group['records'], 1):
                status = "✅ ОСТАВИТЬ" if j == 1 else "❌ УДАЛИТЬ"
                print(f"   {j}. ID {record['id']} - Качество: {record['quality_score']}/10 - {status}")
                print(f"      Описание: {record['description'] or 'Нет'}")
                print(f"      Изображение: {record['image_url']} | Год: {record['year'] or 'N/A'}")
                print(f"      Rating: {record['rating'] or 'N/A'} | AI: {'Нужен' if record['needs_ai'] else 'Есть'}")
                if j < len(group['records']):
                    print()
        
        print("\n" + "=" * 70)
    
    def remove_duplicates(self) -> bool:
        """Удалить дубликаты (оставить лучшую версию)"""
        print("\n🧹 УДАЛЕНИЕ ДУБЛИКАТОВ")
        print("=" * 70)
        
        try:
            self.cursor.execute("SELECT COUNT(*) FROM content")
            self.stats['total_records_before'] = self.cursor.fetchone()[0]
            
            deleted_count = 0
            kept_count = 0
            
            for group in self.duplicates:
                # Первая запись (лучшая) - оставляем
                best_record = group['records'][0]
                kept_count += 1
                
                print(f"\n✅ Оставляем: ID {best_record['id']} - '{group['title']}' (качество: {best_record['quality_score']})")
                
                # Остальные удаляем
                for record in group['records'][1:]:
                    print(f"   ❌ Удаляем: ID {record['id']} (качество: {record['quality_score']})")
                    
                    # Сохраняем информацию об удаленной записи
                    self.deleted_records.append({
                        'id': record['id'],
                        'title': group['title'],
                        'creator': group['creator'],
                        'type': group['type'],
                        'quality_score': record['quality_score'],
                        'kept_instead': best_record['id']
                    })
                    
                    # Удаляем запись
                    self.cursor.execute("DELETE FROM content WHERE id = ?", (record['id'],))
                    deleted_count += 1
            
            # Сохраняем изменения
            self.conn.commit()
            
            self.cursor.execute("SELECT COUNT(*) FROM content")
            self.stats['total_records_after'] = self.cursor.fetchone()[0]
            self.stats['records_deleted'] = deleted_count
            self.stats['records_kept'] = kept_count
            
            print("\n" + "=" * 70)
            print(f"✅ Удалено записей: {deleted_count}")
            print(f"✅ Оставлено лучших версий: {kept_count}")
            print("=" * 70)
            
            return True
            
        except sqlite3.Error as e:
            print(f"\n❌ Ошибка при удалении: {e}")
            self.conn.rollback()
            return False
    
    def create_report(self):
        """Создать JSON отчет об удаленных записях"""
        try:
            if not os.path.exists(REPORT_DIR):
                os.makedirs(REPORT_DIR)
            
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.report_path = os.path.join(REPORT_DIR, f'duplicates_removed_{timestamp}.json')
            
            report = {
                'timestamp': datetime.now().isoformat(),
                'database': self.db_path,
                'backup': self.backup_path,
                'statistics': self.stats,
                'duplicate_groups': len(self.duplicates),
                'deleted_records': self.deleted_records
            }
            
            with open(self.report_path, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2, ensure_ascii=False)
            
            print(f"\n📄 Отчет сохранен: {self.report_path}")
            
        except Exception as e:
            print(f"\n⚠️ Не удалось создать отчет: {e}")
    
    def show_summary(self):
        """Показать итоговую сводку"""
        print("\n📊 ИТОГОВАЯ СВОДКА")
        print("=" * 70)
        print(f"Групп дубликатов найдено: {self.stats['total_duplicate_groups']}")
        print(f"Всего записей ДО: {self.stats['total_records_before']:,}")
        print(f"Всего записей ПОСЛЕ: {self.stats['total_records_after']:,}")
        print(f"Удалено дубликатов: {self.stats['records_deleted']}")
        print(f"Оставлено лучших версий: {self.stats['records_kept']}")
        
        if self.stats['total_records_before'] > 0:
            saved_percentage = (self.stats['records_deleted'] / self.stats['total_records_before']) * 100
            print(f"Очищено: {saved_percentage:.2f}% базы данных")
        
        print("=" * 70)
    
    def show_recommendations(self):
        """Показать рекомендации"""
        print("\n💡 РЕКОМЕНДАЦИИ")
        print("=" * 70)
        
        print("\n1️⃣ Проверьте результаты:")
        print("   python scripts/tools/db_inspector.py")
        print("   python scripts/tools/db_inspector.py --duplicates")
        
        print("\n2️⃣ Предотвращение дубликатов в будущем:")
        print("   - Используйте source_id как UNIQUE ключ")
        print("   - Добавьте проверку перед вставкой новых записей")
        print("   - Обновляйте существующие записи вместо создания новых")
        
        print("\n3️⃣ Улучшение скриптов сбора:")
        print("   harvest_books.py: проверка по ISBN/Google Books ID")
        print("   harvest_movies.py: проверка по TMDB ID")
        print("   harvest_music.py: проверка по Spotify Track ID")
        
        print("\n4️⃣ Следующие шаги:")
        print("   📝 Обновите скрипты сбора данных")
        print("   🤖 Запустите ai_describer.py для оставшихся записей")
        print("   ✅ Добавьте UNIQUE constraint на source_id")
        
        print("\n" + "=" * 70)
    
    def run(self):
        """Запуск полного процесса удаления дубликатов"""
        print("\n" + "=" * 70)
        print("🔄 FIX DUPLICATES - Удаление дубликатов".center(70))
        print("=" * 70)
        
        # 1. Создаем backup
        print("\n1️⃣ Создание резервной копии...")
        if not self.create_backup():
            print("❌ Не удалось создать backup. Операция отменена.")
            return False
        
        # 2. Подключаемся к БД
        print("\n2️⃣ Подключение к базе данных...")
        if not self.connect():
            return False
        
        try:
            # 3. Ищем дубликаты
            print("\n3️⃣ Поиск дубликатов...")
            duplicates = self.find_duplicates()
            
            if not duplicates:
                print("\n✅ Дубликаты не найдены! База данных чиста.")
                return True
            
            # 4. Показываем дубликаты
            self.show_duplicates()
            
            # 5. Подтверждение пользователя
            print("\n⚠️  ВНИМАНИЕ!")
            print(f"   Найдено {len(duplicates)} групп дубликатов")
            print(f"   Будет удалено записей: {sum(len(g['records']) - 1 for g in duplicates)}")
            print(f"   Будет оставлено лучших версий: {len(duplicates)}")
            print(f"\n💾 Backup сохранен: {self.backup_path}")
            
            response = input("\n❓ Продолжить удаление? (yes/no): ").strip().lower()
            
            if response not in ['yes', 'y', 'да', 'д']:
                print("\n❌ Операция отменена пользователем")
                return False
            
            # 6. Удаляем дубликаты
            print("\n4️⃣ Удаление дубликатов...")
            if not self.remove_duplicates():
                return False
            
            # 7. Создаем отчет
            print("\n5️⃣ Создание отчета...")
            self.create_report()
            
            # 8. Показываем сводку
            self.show_summary()
            
            # 9. Показываем рекомендации
            self.show_recommendations()
            
            print("\n" + "=" * 70)
            print("✅ ВСЕ ОПЕРАЦИИ ЗАВЕРШЕНЫ УСПЕШНО!")
            print("=" * 70)
            print(f"\n💾 Backup: {self.backup_path}")
            if self.report_path:
                print(f"📄 Отчет: {self.report_path}")
            print(f"📊 Проверить результат: python scripts/tools/db_inspector.py --duplicates")
            print("\n")
            
            return True
            
        finally:
            self.close()

# ==================== CLI ====================

def main():
    """Точка входа"""
    fixer = DuplicateFixer()
    fixer.run()

if __name__ == "__main__":
    main()
