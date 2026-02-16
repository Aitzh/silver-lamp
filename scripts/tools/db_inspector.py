#!/usr/bin/env python3
"""
🔍 DB INSPECTOR - Профессиональный инструмент диагностики базы данных
Версия: 2.0
Автор: Coffee Books AI Team

Возможности:
- Полная статистика по всем типам контента
- Анализ качества данных (пропущенные поля, дубликаты)
- Проверка integrity (уникальность, валидация)
- Экспорт отчетов в JSON/CSV
- Поиск проблемных записей
- Рекомендации по улучшению
"""

import sqlite3
import argparse
import json
import csv
import sys
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple

# ==================== КОНСТАНТЫ ====================

DB_PATH = 'content.db'

EMOJI_MAP = {
    'book': '📖',
    'movie': '🎬',
    'music': '🎵'
}

# Критические поля для каждого типа
REQUIRED_FIELDS = {
    'book': ['title', 'creator', 'genre'],
    'movie': ['title', 'year', 'genre'],
    'music': ['title', 'creator', 'genre']
}

# ==================== ОСНОВНОЙ КЛАСС ====================

class DatabaseInspector:
    """Главный класс для инспекции базы данных"""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self.stats = {}
        
    def connect(self):
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
    
    # ==================== ОСНОВНАЯ СТАТИСТИКА ====================
    
    def get_total_stats(self) -> Dict:
        """Получить общую статистику"""
        stats = {}
        
        # Общее количество
        self.cursor.execute("SELECT COUNT(*) FROM content")
        stats['total'] = self.cursor.fetchone()[0]
        
        # По типам
        self.cursor.execute("""
            SELECT type, COUNT(*) as count
            FROM content
            GROUP BY type
            ORDER BY count DESC
        """)
        stats['by_type'] = dict(self.cursor.fetchall())
        
        # Средний рейтинг по типам
        self.cursor.execute("""
            SELECT type, ROUND(AVG(rating), 2) as avg_rating
            FROM content
            WHERE rating IS NOT NULL
            GROUP BY type
        """)
        stats['avg_rating'] = dict(self.cursor.fetchall())
        
        # Количество с needs_ai
        self.cursor.execute("SELECT COUNT(*) FROM content WHERE needs_ai = 1")
        stats['needs_ai'] = self.cursor.fetchone()[0]
        
        # Количество без описания
        self.cursor.execute("SELECT COUNT(*) FROM content WHERE description IS NULL OR description = ''")
        stats['no_description'] = self.cursor.fetchone()[0]
        
        # Количество без изображений
        self.cursor.execute("SELECT COUNT(*) FROM content WHERE image_url IS NULL OR image_url = ''")
        stats['no_image'] = self.cursor.fetchone()[0]
        
        return stats
    
    def get_genre_stats(self, limit: int = 10) -> List[Tuple]:
        """Топ жанров"""
        self.cursor.execute("""
            SELECT genre, COUNT(*) as count
            FROM content
            WHERE genre IS NOT NULL
            GROUP BY genre
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        return self.cursor.fetchall()
    
    def get_epoch_stats(self, limit: int = 10) -> List[Tuple]:
        """Статистика по эпохам"""
        self.cursor.execute("""
            SELECT epoch, COUNT(*) as count
            FROM content
            WHERE epoch IS NOT NULL
            GROUP BY epoch
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        return self.cursor.fetchall()
    
    def get_year_distribution(self) -> List[Tuple]:
        """Распределение по годам"""
        self.cursor.execute("""
            SELECT 
                CASE 
                    WHEN year >= 2020 THEN '2020s'
                    WHEN year >= 2010 THEN '2010s'
                    WHEN year >= 2000 THEN '2000s'
                    WHEN year >= 1990 THEN '90s'
                    WHEN year >= 1980 THEN '80s'
                    ELSE 'classics'
                END as decade,
                COUNT(*) as count
            FROM content
            WHERE year IS NOT NULL
            GROUP BY decade
            ORDER BY count DESC
        """)
        return self.cursor.fetchall()
    
    # ==================== АНАЛИЗ КАЧЕСТВА ====================
    
    def check_data_quality(self, content_type: str = None) -> Dict:
        """Проверка качества данных"""
        quality_report = {
            'missing_fields': {},
            'empty_ratings': 0,
            'duplicates': 0,
            'orphaned_records': 0
        }
        
        type_filter = f"WHERE type = '{content_type}'" if content_type else ""
        
        # Проверка пропущенных полей
        for field in ['title', 'creator', 'description', 'image_url', 'year', 'rating', 'genre']:
            self.cursor.execute(f"""
                SELECT COUNT(*) FROM content 
                {type_filter}
                {'AND' if content_type else 'WHERE'} ({field} IS NULL OR {field} = '')
            """)
            count = self.cursor.fetchone()[0]
            if count > 0:
                quality_report['missing_fields'][field] = count
        
        # Пустые рейтинги
        self.cursor.execute(f"""
            SELECT COUNT(*) FROM content 
            {type_filter}
            {'AND' if content_type else 'WHERE'} rating IS NULL
        """)
        quality_report['empty_ratings'] = self.cursor.fetchone()[0]
        
        # Дубликаты по source_id
        self.cursor.execute(f"""
            SELECT source_id, COUNT(*) as count
            FROM content
            {type_filter}
            GROUP BY source_id
            HAVING count > 1
        """)
        quality_report['duplicates'] = len(self.cursor.fetchall())
        
        return quality_report
    
    def find_duplicates(self, limit: int = 20) -> List[Dict]:
        """Найти дубликаты"""
        self.cursor.execute("""
            SELECT title, creator, type, COUNT(*) as count, GROUP_CONCAT(id) as ids
            FROM content
            GROUP BY LOWER(title), LOWER(creator), type
            HAVING count > 1
            ORDER BY count DESC
            LIMIT ?
        """, (limit,))
        
        duplicates = []
        for row in self.cursor.fetchall():
            duplicates.append({
                'title': row[0],
                'creator': row[1],
                'type': row[2],
                'count': row[3],
                'ids': row[4]
            })
        return duplicates
    
    def find_missing_critical_data(self, content_type: str, limit: int = 20) -> List[Dict]:
        """Найти записи с критически пропущенными данными"""
        if content_type not in REQUIRED_FIELDS:
            return []
        
        conditions = []
        for field in REQUIRED_FIELDS[content_type]:
            conditions.append(f"({field} IS NULL OR {field} = '')")
        
        query = f"""
            SELECT id, title, creator, type, genre, year
            FROM content
            WHERE type = ?
            AND ({' OR '.join(conditions)})
            LIMIT ?
        """
        
        self.cursor.execute(query, (content_type, limit))
        
        results = []
        for row in self.cursor.fetchall():
            results.append({
                'id': row[0],
                'title': row[1],
                'creator': row[2],
                'type': row[3],
                'genre': row[4],
                'year': row[5]
            })
        return results
    
    # ==================== СПЕЦИФИЧНАЯ СТАТИСТИКА ====================
    
    def get_type_specific_values(self, content_type: str) -> Dict:
        """Получить уникальные значения для типа контента"""
        values = {}
        
        # Жанры
        self.cursor.execute("""
            SELECT DISTINCT genre FROM content
            WHERE type = ? AND genre IS NOT NULL
            ORDER BY genre
        """, (content_type,))
        values['genres'] = [row[0] for row in self.cursor.fetchall()]
        
        # Эпохи
        self.cursor.execute("""
            SELECT DISTINCT epoch FROM content
            WHERE type = ? AND epoch IS NOT NULL
            ORDER BY epoch
        """, (content_type,))
        values['epochs'] = [row[0] for row in self.cursor.fetchall()]
        
        # Настроения (для музыки)
        if content_type == 'music':
            self.cursor.execute("""
                SELECT DISTINCT mood FROM content
                WHERE type = 'music' AND mood IS NOT NULL
                ORDER BY mood
            """)
            values['moods'] = [row[0] for row in self.cursor.fetchall()]
        
        return values
    
    # ==================== РЕКОМЕНДАЦИИ ====================
    
    def generate_recommendations(self) -> List[str]:
        """Генерация рекомендаций по улучшению БД"""
        recommendations = []
        
        stats = self.get_total_stats()
        quality = self.check_data_quality()
        
        # Проверка needs_ai
        if stats['needs_ai'] > 0:
            percentage = (stats['needs_ai'] / stats['total']) * 100
            recommendations.append(
                f"🤖 {stats['needs_ai']} записей ({percentage:.1f}%) нуждаются в AI-описаниях. "
                f"Запустите: python scripts/tools/ai_describer.py --limit=100"
            )
        
        # Проверка пропущенных описаний
        if stats['no_description'] > 500:
            recommendations.append(
                f"📝 {stats['no_description']} записей без описания. "
                f"Приоритизируйте элементы с высоким рейтингом."
            )
        
        # Проверка изображений
        if stats['no_image'] > 1000:
            recommendations.append(
                f"🖼️ {stats['no_image']} записей без изображений. "
                f"Проверьте API-ключи для Google Books, TMDB, Spotify."
            )
        
        # Проверка дубликатов
        duplicates = self.find_duplicates(limit=5)
        if len(duplicates) > 0:
            recommendations.append(
                f"🔄 Обнаружено {len(duplicates)} групп дубликатов. "
                f"Запустите: python scripts/migrations/fix_duplicates.py"
            )
        
        # Проверка качества по типам
        for content_type in ['book', 'movie', 'music']:
            missing = self.find_missing_critical_data(content_type, limit=1)
            if len(missing) > 0:
                recommendations.append(
                    f"⚠️ Тип '{content_type}': найдены записи с пропущенными критическими полями. "
                    f"Проверьте скрипты сбора данных."
                )
        
        return recommendations
    
    # ==================== ВЫВОД ОТЧЕТОВ ====================
    
    def print_full_report(self):
        """Вывести полный отчет в консоль"""
        print("\n" + "=" * 70)
        print("🔍 DATABASE INSPECTOR - ПОЛНЫЙ ОТЧЕТ".center(70))
        print("=" * 70)
        
        # Общая статистика
        stats = self.get_total_stats()
        print(f"\n📊 ОБЩАЯ СТАТИСТИКА")
        print(f"{'─' * 70}")
        print(f"📚 Всего записей: {stats['total']:,}")
        print(f"\n📋 По типам:")
        for content_type, count in stats['by_type'].items():
            emoji = EMOJI_MAP.get(content_type, '📄')
            avg_rating = stats['avg_rating'].get(content_type, 0)
            print(f"  {emoji} {content_type.capitalize()}: {count:,} (⭐ {avg_rating})")
        
        # Качество данных
        print(f"\n🎯 КАЧЕСТВО ДАННЫХ")
        print(f"{'─' * 70}")
        print(f"⚡ Нужно AI-описаний: {stats['needs_ai']:,}")
        print(f"📝 Без описания: {stats['no_description']:,}")
        print(f"🖼️ Без изображений: {stats['no_image']:,}")
        
        # Топ жанров
        print(f"\n🎭 ТОП-10 ЖАНРОВ")
        print(f"{'─' * 70}")
        for i, (genre, count) in enumerate(self.get_genre_stats(10), 1):
            print(f"  {i:2}. {genre:20} {count:,}")
        
        # Распределение по годам
        print(f"\n📅 РАСПРЕДЕЛЕНИЕ ПО ЭПОХАМ")
        print(f"{'─' * 70}")
        for decade, count in self.get_year_distribution():
            print(f"  {decade:15} {count:,}")
        
        # Проблемы качества
        print(f"\n⚠️ АНАЛИЗ КАЧЕСТВА")
        print(f"{'─' * 70}")
        quality = self.check_data_quality()
        
        if quality['missing_fields']:
            print("Пропущенные поля:")
            for field, count in quality['missing_fields'].items():
                print(f"  - {field:15} {count:,} записей")
        
        if quality['duplicates'] > 0:
            print(f"\n🔄 Дубликаты: {quality['duplicates']} групп")
            duplicates = self.find_duplicates(5)
            for dup in duplicates[:3]:
                print(f"  - '{dup['title']}' by {dup['creator']} ({dup['count']} копий)")
        
        # Рекомендации
        recommendations = self.generate_recommendations()
        if recommendations:
            print(f"\n💡 РЕКОМЕНДАЦИИ ({len(recommendations)})")
            print(f"{'─' * 70}")
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}\n")
        
        print("=" * 70)
        print(f"✅ Отчет сгенерирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70 + "\n")
    
    def print_type_report(self, content_type: str):
        """Отчет по конкретному типу контента"""
        if content_type not in ['book', 'movie', 'music']:
            print(f"❌ Неизвестный тип: {content_type}")
            return
        
        emoji = EMOJI_MAP[content_type]
        print(f"\n{emoji} ОТЧЕТ ПО ТИПУ: {content_type.upper()}")
        print("=" * 70)
        
        # Общие цифры
        self.cursor.execute("SELECT COUNT(*) FROM content WHERE type = ?", (content_type,))
        total = self.cursor.fetchone()[0]
        print(f"Всего записей: {total:,}")
        
        # Средний рейтинг
        self.cursor.execute("""
            SELECT ROUND(AVG(rating), 2) FROM content 
            WHERE type = ? AND rating IS NOT NULL
        """, (content_type,))
        avg_rating = self.cursor.fetchone()[0]
        print(f"Средний рейтинг: ⭐ {avg_rating or 0}")
        
        # Уникальные значения
        values = self.get_type_specific_values(content_type)
        print(f"\n📂 Уникальные значения:")
        print(f"  Жанры ({len(values['genres'])}): {', '.join(values['genres'][:10])}")
        if values['epochs']:
            print(f"  Эпохи ({len(values['epochs'])}): {', '.join(values['epochs'][:10])}")
        if 'moods' in values:
            print(f"  Настроения ({len(values['moods'])}): {', '.join(values['moods'][:10])}")
        
        # Проблемы качества
        quality = self.check_data_quality(content_type)
        print(f"\n⚠️ Проблемы качества:")
        for field, count in quality['missing_fields'].items():
            if count > 0:
                percentage = (count / total) * 100
                print(f"  - {field:15} {count:,} ({percentage:.1f}%)")
        
        # Критические пропуски
        missing = self.find_missing_critical_data(content_type, 5)
        if missing:
            print(f"\n🚨 Критические пропуски (топ-5):")
            for item in missing:
                print(f"  ID {item['id']:5} | {item['title'][:40]:40} | {item['creator'] or 'N/A'}")
        
        print("=" * 70 + "\n")
    
    def export_json(self, filename: str):
        """Экспорт отчета в JSON"""
        report = {
            'generated_at': datetime.now().isoformat(),
            'database': self.db_path,
            'stats': self.get_total_stats(),
            'quality': self.check_data_quality(),
            'duplicates': self.find_duplicates(50),
            'recommendations': self.generate_recommendations()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"✅ Отчет сохранен: {filename}")
    
    def export_csv(self, filename: str, content_type: str = None):
        """Экспорт проблемных записей в CSV"""
        type_filter = f"WHERE type = '{content_type}'" if content_type else ""
        
        self.cursor.execute(f"""
            SELECT id, type, title, creator, genre, year, rating,
                   CASE WHEN description IS NULL OR description = '' THEN 'YES' ELSE 'NO' END as missing_desc,
                   CASE WHEN image_url IS NULL OR image_url = '' THEN 'YES' ELSE 'NO' END as missing_image,
                   needs_ai
            FROM content
            {type_filter}
        """)
        
        rows = self.cursor.fetchall()
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Type', 'Title', 'Creator', 'Genre', 'Year', 'Rating', 
                           'Missing Desc', 'Missing Image', 'Needs AI'])
            writer.writerows(rows)
        
        print(f"✅ CSV экспортирован: {filename} ({len(rows)} записей)")

# ==================== CLI ====================

def main():
    parser = argparse.ArgumentParser(
        description='🔍 DB Inspector - Профессиональный инструмент диагностики БД',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python db_inspector.py                          # Полный отчет
  python db_inspector.py --type books             # Отчет по книгам
  python db_inspector.py --type music             # Отчет по музыке
  python db_inspector.py --missing-data           # Только проблемные записи
  python db_inspector.py --duplicates             # Найти дубликаты
  python db_inspector.py --export-json report.json
  python db_inspector.py --export-csv data.csv --type movies
        """
    )
    
    parser.add_argument('--type', 
                       choices=['books', 'movies', 'music'],
                       help='Тип контента для анализа')
    
    parser.add_argument('--missing-data',
                       action='store_true',
                       help='Показать только записи с пропущенными данными')
    
    parser.add_argument('--duplicates',
                       action='store_true',
                       help='Показать дубликаты')
    
    parser.add_argument('--export-json',
                       metavar='FILE',
                       help='Экспортировать отчет в JSON')
    
    parser.add_argument('--export-csv',
                       metavar='FILE',
                       help='Экспортировать данные в CSV')
    
    parser.add_argument('--db',
                       default=DB_PATH,
                       help=f'Путь к базе данных (по умолчанию: {DB_PATH})')
    
    args = parser.parse_args()
    
    # Создаем инспектор
    inspector = DatabaseInspector(args.db)
    
    if not inspector.connect():
        sys.exit(1)
    
    try:
        # Выбор режима работы
        if args.export_json:
            inspector.export_json(args.export_json)
        
        elif args.export_csv:
            content_type = args.type[:-1] if args.type else None  # books -> book
            inspector.export_csv(args.export_csv, content_type)
        
        elif args.duplicates:
            print("\n🔄 ПОИСК ДУБЛИКАТОВ")
            print("=" * 70)
            duplicates = inspector.find_duplicates(50)
            if duplicates:
                for i, dup in enumerate(duplicates, 1):
                    print(f"{i:2}. '{dup['title']}' by {dup['creator']}")
                    print(f"    Тип: {dup['type']} | Копий: {dup['count']} | IDs: {dup['ids']}\n")
            else:
                print("✅ Дубликаты не найдены!")
        
        elif args.missing_data:
            print("\n⚠️ ЗАПИСИ С ПРОПУЩЕННЫМИ ДАННЫМИ")
            print("=" * 70)
            for content_type in ['book', 'movie', 'music']:
                missing = inspector.find_missing_critical_data(content_type, 10)
                if missing:
                    emoji = EMOJI_MAP[content_type]
                    print(f"\n{emoji} {content_type.upper()} ({len(missing)} записей):")
                    for item in missing:
                        print(f"  ID {item['id']:5} | {item['title'][:50]}")
        
        elif args.type:
            content_type = args.type[:-1]  # books -> book
            inspector.print_type_report(content_type)
        
        else:
            # Полный отчет по умолчанию
            inspector.print_full_report()
    
    finally:
        inspector.close()

if __name__ == "__main__":
    main()
