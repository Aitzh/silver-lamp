#!/usr/bin/env python3
"""
🧹 REMOVE UNRELIABLE RATINGS - Очистка ненадежных рейтингов

Назначение:
- Удаляет рейтинги у книг (Google Books - ненадежные данные)
- Удаляет рейтинги у музыки (Spotify popularity ≠ качество)
- Сохраняет рейтинги фильмов (TMDB - надежные данные)

Автор: Coffee Books AI Team
Версия: 1.0
"""

import sqlite3
import shutil
import os
from datetime import datetime
from typing import Dict

# ==================== КОНСТАНТЫ ====================

DB_PATH = 'content.db'
BACKUP_DIR = 'backups'

# ==================== КЛАСС МИГРАЦИИ ====================

class RatingCleaner:
    """Класс для очистки ненадежных рейтингов"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.backup_path = None
        self.conn = None
        self.cursor = None
        self.stats_before = {}
        self.stats_after = {}
    
    def create_backup(self) -> bool:
        """Создание резервной копии базы данных"""
        try:
            # Создаем директорию для бэкапов
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)
            
            # Генерируем имя файла с timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.backup_path = os.path.join(BACKUP_DIR, f'content_backup_{timestamp}.db')
            
            # Копируем базу
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
    
    def get_rating_stats(self, content_type: str) -> Dict:
        """Получить статистику рейтингов для типа контента"""
        stats = {}
        
        # Общее количество
        self.cursor.execute(
            "SELECT COUNT(*) FROM content WHERE type = ?", 
            (content_type,)
        )
        stats['total'] = self.cursor.fetchone()[0]
        
        # С рейтингом
        self.cursor.execute(
            "SELECT COUNT(*) FROM content WHERE type = ? AND rating IS NOT NULL AND rating > 0",
            (content_type,)
        )
        stats['with_rating'] = self.cursor.fetchone()[0]
        
        # Без рейтинга
        stats['without_rating'] = stats['total'] - stats['with_rating']
        
        # Процент
        if stats['total'] > 0:
            stats['percentage_with_rating'] = (stats['with_rating'] / stats['total']) * 100
        else:
            stats['percentage_with_rating'] = 0
        
        # Средний рейтинг
        self.cursor.execute(
            "SELECT AVG(rating) FROM content WHERE type = ? AND rating IS NOT NULL AND rating > 0",
            (content_type,)
        )
        avg = self.cursor.fetchone()[0]
        stats['avg_rating'] = round(avg, 2) if avg else 0
        
        # Мин/Макс
        self.cursor.execute(
            "SELECT MIN(rating), MAX(rating) FROM content WHERE type = ? AND rating IS NOT NULL AND rating > 0",
            (content_type,)
        )
        min_r, max_r = self.cursor.fetchone()
        stats['min_rating'] = min_r if min_r else 0
        stats['max_rating'] = max_r if max_r else 0
        
        return stats
    
    def collect_stats_before(self):
        """Собрать статистику ДО очистки"""
        print("\n📊 СТАТИСТИКА ДО ОЧИСТКИ")
        print("=" * 70)
        
        for content_type in ['book', 'movie', 'music']:
            emoji = {'book': '📖', 'movie': '🎬', 'music': '🎵'}[content_type]
            stats = self.get_rating_stats(content_type)
            self.stats_before[content_type] = stats
            
            print(f"\n{emoji} {content_type.upper()}:")
            print(f"  Всего записей: {stats['total']:,}")
            print(f"  С рейтингом: {stats['with_rating']:,} ({stats['percentage_with_rating']:.1f}%)")
            print(f"  Без рейтинга: {stats['without_rating']:,}")
            if stats['avg_rating'] > 0:
                print(f"  Средний рейтинг: ⭐ {stats['avg_rating']:.2f}")
                print(f"  Диапазон: {stats['min_rating']:.2f} - {stats['max_rating']:.2f}")
        
        print("\n" + "=" * 70)
    
    def clean_ratings(self):
        """Удаление ненадежных рейтингов"""
        print("\n🧹 НАЧИНАЮ ОЧИСТКУ РЕЙТИНГОВ")
        print("=" * 70)
        
        try:
            # 1. Удаляем рейтинги у КНИГ
            print("\n📖 Удаляю рейтинги у книг...")
            self.cursor.execute("""
                UPDATE content 
                SET rating = NULL 
                WHERE type = 'book'
            """)
            books_updated = self.cursor.rowcount
            print(f"   ✅ Обновлено {books_updated:,} книг")
            
            # 2. Удаляем рейтинги у МУЗЫКИ
            print("\n🎵 Удаляю рейтинги у музыки...")
            self.cursor.execute("""
                UPDATE content 
                SET rating = NULL 
                WHERE type = 'music'
            """)
            music_updated = self.cursor.rowcount
            print(f"   ✅ Обновлено {music_updated:,} треков")
            
            # 3. ФИЛЬМЫ не трогаем
            print("\n🎬 Фильмы - рейтинги сохранены (TMDB надежен)")
            
            # Сохраняем изменения
            self.conn.commit()
            
            print("\n" + "=" * 70)
            print("✅ ОЧИСТКА ЗАВЕРШЕНА УСПЕШНО!")
            
            return True
            
        except sqlite3.Error as e:
            print(f"\n❌ Ошибка при очистке: {e}")
            self.conn.rollback()
            return False
    
    def collect_stats_after(self):
        """Собрать статистику ПОСЛЕ очистки"""
        print("\n📊 СТАТИСТИКА ПОСЛЕ ОЧИСТКИ")
        print("=" * 70)
        
        for content_type in ['book', 'movie', 'music']:
            emoji = {'book': '📖', 'movie': '🎬', 'music': '🎵'}[content_type]
            stats = self.get_rating_stats(content_type)
            self.stats_after[content_type] = stats
            
            print(f"\n{emoji} {content_type.upper()}:")
            print(f"  Всего записей: {stats['total']:,}")
            print(f"  С рейтингом: {stats['with_rating']:,} ({stats['percentage_with_rating']:.1f}%)")
            print(f"  Без рейтинга: {stats['without_rating']:,}")
            if stats['avg_rating'] > 0:
                print(f"  Средний рейтинг: ⭐ {stats['avg_rating']:.2f}")
                print(f"  Диапазон: {stats['min_rating']:.2f} - {stats['max_rating']:.2f}")
        
        print("\n" + "=" * 70)
    
    def show_summary(self):
        """Показать итоговую сводку изменений"""
        print("\n📋 ИТОГОВАЯ СВОДКА ИЗМЕНЕНИЙ")
        print("=" * 70)
        
        for content_type in ['book', 'movie', 'music']:
            emoji = {'book': '📖', 'movie': '🎬', 'music': '🎵'}[content_type]
            
            before = self.stats_before[content_type]
            after = self.stats_after[content_type]
            
            # Изменение количества рейтингов
            rating_change = after['with_rating'] - before['with_rating']
            
            print(f"\n{emoji} {content_type.upper()}:")
            
            if content_type in ['book', 'music']:
                # Должны быть удалены
                if rating_change < 0:
                    print(f"   ✅ Удалено рейтингов: {abs(rating_change):,}")
                    print(f"   📊 До: {before['with_rating']:,} → После: {after['with_rating']:,}")
                else:
                    print(f"   ⚠️ Неожиданно: изменение = {rating_change}")
            
            elif content_type == 'movie':
                # Должны остаться без изменений
                if rating_change == 0:
                    print(f"   ✅ Рейтинги сохранены: {after['with_rating']:,}")
                    print(f"   ⭐ Средний рейтинг: {after['avg_rating']:.2f}")
                else:
                    print(f"   ⚠️ Неожиданное изменение: {rating_change:,}")
        
        print("\n" + "=" * 70)
    
    def show_recommendations(self):
        """Показать рекомендации после очистки"""
        print("\n💡 РЕКОМЕНДАЦИИ")
        print("=" * 70)
        
        print("\n1️⃣ Для КНИГ используйте альтернативные метрики:")
        print("   - Жанр (genre)")
        print("   - Эпоха (epoch: 'classics', 'modern')")
        print("   - AI-описание (качественное описание)")
        print("   - Популярность автора")
        
        print("\n2️⃣ Для МУЗЫКИ используйте альтернативные метрики:")
        print("   - Жанр (genre)")
        print("   - Настроение (mood: 'energetic', 'chill', 'romantic')")
        print("   - Эпоха (epoch: '80s', '90s', '2020s')")
        print("   - AI-описание (эмоциональное описание)")
        
        print("\n3️⃣ Для ФИЛЬМОВ:")
        print("   ✅ Рейтинги TMDB надежны - используйте их!")
        print("   ✅ Можно фильтровать по rating >= 7.0 для качественных фильмов")
        
        print("\n4️⃣ Следующие шаги:")
        print("   📝 Обновите фронтенд (уберите сортировку по рейтингу для книг/музыки)")
        print("   🤖 Запустите ai_describer.py для генерации описаний")
        print("   🔧 Обновите recommend.js (уберите фильтрацию по rating для books/music)")
        
        print("\n" + "=" * 70)
    
    def run(self):
        """Запуск полного процесса очистки"""
        print("\n" + "=" * 70)
        print("🧹 REMOVE UNRELIABLE RATINGS".center(70))
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
            # 3. Собираем статистику ДО
            print("\n3️⃣ Сбор статистики ДО очистки...")
            self.collect_stats_before()
            
            # 4. Подтверждение пользователя
            print("\n⚠️  ВНИМАНИЕ! Сейчас будут удалены рейтинги:")
            print("   - Все рейтинги КНИГ (ненадежны)")
            print("   - Все рейтинги МУЗЫКИ (popularity ≠ качество)")
            print("   - Рейтинги ФИЛЬМОВ останутся БЕЗ ИЗМЕНЕНИЙ")
            print(f"\n💾 Backup сохранен: {self.backup_path}")
            
            response = input("\n❓ Продолжить? (yes/no): ").strip().lower()
            
            if response not in ['yes', 'y', 'да', 'д']:
                print("\n❌ Операция отменена пользователем")
                return False
            
            # 5. Выполняем очистку
            print("\n4️⃣ Выполнение очистки...")
            if not self.clean_ratings():
                return False
            
            # 6. Собираем статистику ПОСЛЕ
            print("\n5️⃣ Сбор статистики ПОСЛЕ очистки...")
            self.collect_stats_after()
            
            # 7. Показываем сводку
            self.show_summary()
            
            # 8. Показываем рекомендации
            self.show_recommendations()
            
            print("\n" + "=" * 70)
            print("✅ ВСЕ ОПЕРАЦИИ ЗАВЕРШЕНЫ УСПЕШНО!")
            print("=" * 70)
            print(f"\n💾 Backup: {self.backup_path}")
            print(f"📊 Проверить результат: python scripts/tools/db_inspector.py")
            print("\n")
            
            return True
            
        finally:
            self.close()

# ==================== CLI ====================

def main():
    """Точка входа"""
    cleaner = RatingCleaner()
    cleaner.run()

if __name__ == "__main__":
    main()
