#!/usr/bin/env python3
"""
🌍 CHECK TRANSLATIONS - Проверка переводов описаний
Версия: 1.0
Автор: Coffee Books AI Team

Проверяет наличие и качество переводов в базе данных:
- Статистика по всем языкам (RU, EN, KK)
- Какие записи переведены, какие нет
- Качество переводов (длина, пустые значения)
- Поиск проблемных записей
- Экспорт отчетов
"""

import sqlite3
import os
import argparse
from collections import defaultdict

DB_PATH = 'content.db'

class TranslationChecker:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        
    def connect(self):
        """Подключение к БД"""
        if not os.path.exists(self.db_path):
            print(f"❌ База данных не найдена: {self.db_path}")
            return False
        
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    def close(self):
        """Закрытие соединения"""
        if self.conn:
            self.conn.close()
    
    def get_overall_stats(self):
        """Общая статистика по переводам"""
        print("\n" + "="*70)
        print("🌍 СТАТИСТИКА ПЕРЕВОДОВ")
        print("="*70)
        
        # Общее количество
        self.cursor.execute("SELECT COUNT(*) FROM content")
        total = self.cursor.fetchone()[0]
        
        # Переводы по языкам
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN description IS NOT NULL AND description != '' THEN 1 ELSE 0 END) as has_base,
                SUM(CASE WHEN description_ru IS NOT NULL AND description_ru != '' THEN 1 ELSE 0 END) as has_ru,
                SUM(CASE WHEN description_en IS NOT NULL AND description_en != '' THEN 1 ELSE 0 END) as has_en,
                SUM(CASE WHEN description_kk IS NOT NULL AND description_kk != '' THEN 1 ELSE 0 END) as has_kk
            FROM content
        """)
        
        stats = self.cursor.fetchone()
        
        print(f"\n📊 Общая статистика:")
        print(f"  Всего записей: {total:,}")
        print(f"\n📝 Описания по языкам:")
        
        langs = [
            ('Base (description)', stats['has_base']),
            ('🇷🇺 Русский (description_ru)', stats['has_ru']),
            ('🇬🇧 Английский (description_en)', stats['has_en']),
            ('🇰🇿 Казахский (description_kk)', stats['has_kk'])
        ]
        
        for lang_name, count in langs:
            percent = (count / total * 100) if total > 0 else 0
            bar = '█' * int(percent / 2)
            print(f"  {lang_name:35} {count:>6,} ({percent:>5.1f}%) {bar}")
        
        # Недостающие переводы
        missing_ru = total - stats['has_ru']
        missing_en = total - stats['has_en']
        missing_kk = total - stats['has_kk']
        
        print(f"\n⚠️  Отсутствуют переводы:")
        print(f"  Русский:    {missing_ru:>6,} записей")
        print(f"  Английский: {missing_en:>6,} записей")
        print(f"  Казахский:  {missing_kk:>6,} записей")
        
        return stats
    
    def get_stats_by_type(self):
        """Статистика по типам контента"""
        print("\n" + "="*70)
        print("📚 СТАТИСТИКА ПО ТИПАМ КОНТЕНТА")
        print("="*70)
        
        self.cursor.execute("""
            SELECT 
                type,
                COUNT(*) as total,
                SUM(CASE WHEN description_ru IS NOT NULL AND description_ru != '' THEN 1 ELSE 0 END) as has_ru,
                SUM(CASE WHEN description_en IS NOT NULL AND description_en != '' THEN 1 ELSE 0 END) as has_en,
                SUM(CASE WHEN description_kk IS NOT NULL AND description_kk != '' THEN 1 ELSE 0 END) as has_kk
            FROM content
            GROUP BY type
        """)
        
        type_icons = {'book': '📖', 'movie': '🎬', 'music': '🎵'}
        
        for row in self.cursor.fetchall():
            type_name = row['type']
            icon = type_icons.get(type_name, '📄')
            total = row['total']
            
            print(f"\n{icon} {type_name.upper()} (всего: {total:,})")
            
            langs = [
                ('Русский', row['has_ru']),
                ('Английский', row['has_en']),
                ('Казахский', row['has_kk'])
            ]
            
            for lang_name, count in langs:
                percent = (count / total * 100) if total > 0 else 0
                bar = '█' * int(percent / 3)
                status = '✅' if percent == 100 else '⚠️' if percent > 50 else '❌'
                print(f"  {status} {lang_name:12} {count:>5,}/{total:,} ({percent:>5.1f}%) {bar}")
    
    def find_missing_translations(self, lang='kk', limit=20):
        """Найти записи без перевода"""
        lang_names = {'ru': 'русского', 'en': 'английского', 'kk': 'казахского'}
        lang_name = lang_names.get(lang, lang)
        
        print(f"\n" + "="*70)
        print(f"🔍 ЗАПИСИ БЕЗ {lang_name.upper()} ПЕРЕВОДА (первые {limit})")
        print("="*70)
        
        self.cursor.execute(f"""
            SELECT id, type, title, creator
            FROM content
            WHERE (description_{lang} IS NULL OR description_{lang} = '')
            LIMIT ?
        """, (limit,))
        
        records = self.cursor.fetchall()
        
        if not records:
            print(f"\n✅ Все записи имеют {lang_name} перевод!")
            return
        
        type_icons = {'book': '📖', 'movie': '🎬', 'music': '🎵'}
        
        for i, row in enumerate(records, 1):
            icon = type_icons.get(row['type'], '📄')
            creator = f" - {row['creator']}" if row['creator'] else ""
            print(f"{i:3}. {icon} [{row['id']}] {row['title']}{creator}")
    
    def check_translation_quality(self):
        """Проверка качества переводов"""
        print("\n" + "="*70)
        print("🔬 ПРОВЕРКА КАЧЕСТВА ПЕРЕВОДОВ")
        print("="*70)
        
        # Слишком короткие переводы
        self.cursor.execute("""
            SELECT 
                COUNT(*) as count,
                'Русский' as lang
            FROM content
            WHERE description_ru IS NOT NULL 
              AND description_ru != ''
              AND LENGTH(description_ru) < 20
            UNION ALL
            SELECT 
                COUNT(*),
                'Английский'
            FROM content
            WHERE description_en IS NOT NULL 
              AND description_en != ''
              AND LENGTH(description_en) < 20
            UNION ALL
            SELECT 
                COUNT(*),
                'Казахский'
            FROM content
            WHERE description_kk IS NOT NULL 
              AND description_kk != ''
              AND LENGTH(description_kk) < 20
        """)
        
        print("\n⚠️  Слишком короткие описания (< 20 символов):")
        for row in self.cursor.fetchall():
            if row[0] > 0:
                print(f"  {row[1]}: {row[0]:,} записей")
        
        # Дубликаты переводов
        print("\n🔄 Проверка на дубликаты...")
        
        for lang in ['ru', 'en', 'kk']:
            self.cursor.execute(f"""
                SELECT description_{lang}, COUNT(*) as count
                FROM content
                WHERE description_{lang} IS NOT NULL 
                  AND description_{lang} != ''
                GROUP BY description_{lang}
                HAVING count > 5
                ORDER BY count DESC
                LIMIT 5
            """)
            
            dupes = self.cursor.fetchall()
            if dupes:
                lang_names = {'ru': 'Русский', 'en': 'Английский', 'kk': 'Казахский'}
                print(f"\n  {lang_names[lang]} - топ дубликатов:")
                for desc, count in dupes:
                    preview = desc[:60] + "..." if len(desc) > 60 else desc
                    print(f"    [{count:>3}x] {preview}")
    
    def get_translation_progress(self):
        """Прогресс переводов"""
        print("\n" + "="*70)
        print("📈 ПРОГРЕСС ПЕРЕВОДОВ")
        print("="*70)
        
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN description_ru IS NOT NULL AND description_ru != '' THEN 1 ELSE 0 END) as has_ru,
                SUM(CASE WHEN description_en IS NOT NULL AND description_en != '' THEN 1 ELSE 0 END) as has_en,
                SUM(CASE WHEN description_kk IS NOT NULL AND description_kk != '' THEN 1 ELSE 0 END) as has_kk,
                SUM(CASE WHEN 
                    (description_ru IS NOT NULL AND description_ru != '') AND
                    (description_en IS NOT NULL AND description_en != '') AND
                    (description_kk IS NOT NULL AND description_kk != '')
                THEN 1 ELSE 0 END) as has_all
            FROM content
        """)
        
        stats = self.cursor.fetchone()
        total = stats[0]
        has_all = stats[4]
        
        percent_all = (has_all / total * 100) if total > 0 else 0
        
        print(f"\n✅ Полностью переведены (все 3 языка): {has_all:,}/{total:,} ({percent_all:.1f}%)")
        
        bar_length = 50
        filled = int(percent_all / 100 * bar_length)
        bar = '█' * filled + '░' * (bar_length - filled)
        print(f"\n[{bar}] {percent_all:.1f}%")
        
        if percent_all < 100:
            remaining = total - has_all
            print(f"\n⏳ Осталось перевести: {remaining:,} записей")
    
    def export_missing(self, lang='kk', output='missing_translations.txt'):
        """Экспорт списка записей без перевода"""
        print(f"\n💾 Экспорт записей без {lang.upper()} перевода...")
        
        self.cursor.execute(f"""
            SELECT id, type, title, creator, source_id
            FROM content
            WHERE (description_{lang} IS NULL OR description_{lang} = '')
            ORDER BY type, title
        """)
        
        records = self.cursor.fetchall()
        
        with open(output, 'w', encoding='utf-8') as f:
            f.write(f"Записи без {lang.upper()} перевода\n")
            f.write(f"Всего: {len(records)}\n")
            f.write("="*70 + "\n\n")
            
            for row in records:
                creator = f" | {row['creator']}" if row['creator'] else ""
                f.write(f"[{row['id']}] {row['type']} | {row['title']}{creator} | {row['source_id']}\n")
        
        print(f"✅ Сохранено в {output} ({len(records):,} записей)")

def main():
    parser = argparse.ArgumentParser(description='Проверка переводов в базе данных')
    parser.add_argument('--missing', choices=['ru', 'en', 'kk'], 
                       help='Показать записи без перевода на указанном языке')
    parser.add_argument('--limit', type=int, default=20,
                       help='Количество записей для показа (по умолчанию: 20)')
    parser.add_argument('--export', choices=['ru', 'en', 'kk'],
                       help='Экспортировать список записей без перевода')
    parser.add_argument('--quality', action='store_true',
                       help='Проверить качество переводов')
    parser.add_argument('--by-type', action='store_true',
                       help='Статистика по типам контента')
    
    args = parser.parse_args()
    
    checker = TranslationChecker()
    
    if not checker.connect():
        return
    
    try:
        # Всегда показываем общую статистику
        checker.get_overall_stats()
        
        # Дополнительные опции
        if args.by_type:
            checker.get_stats_by_type()
        
        if args.missing:
            checker.find_missing_translations(args.missing, args.limit)
        
        if args.quality:
            checker.check_translation_quality()
        
        if args.export:
            output = f"missing_{args.export}_translations.txt"
            checker.export_missing(args.export, output)
        
        # Всегда показываем прогресс
        checker.get_translation_progress()
        
        print("\n" + "="*70)
        print("✅ Проверка завершена!")
        print("="*70 + "\n")
        
    finally:
        checker.close()

if __name__ == '__main__':
    main()