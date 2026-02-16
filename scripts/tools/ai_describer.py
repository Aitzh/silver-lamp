#!/usr/bin/env python3
"""
🤖 AI DESCRIBER FINAL - Финальная версия с системным промптом

Назначение:
- Генерирует СТРОГО 2 предложения через системный промпт
- Автоматическая очистка незаконченных предложений
- Умный выбор промпта (короткий/длинный)
- Шаблоны по жанрам для неизвестного контента

Автор: Coffee Books AI Team
Версия: 3.0 (Final Edition)
"""

import sqlite3
import os
import time
import argparse
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

try:
    from groq import Groq
except ImportError:
    print("❌ ОШИБКА: Библиотека groq не установлена!")
    print("Установите: pip install groq --break-system-packages")
    exit(1)

# ==================== КОНСТАНТЫ ====================

DB_PATH = 'content.db'
API_KEY = os.getenv('GROQ_API_KEY')
MODEL = 'openai/gpt-oss-120b'  # OpenAI reasoning модель

# Лимиты для генерации (разумный запас)
MAX_TOKENS_SHORT = 200   # Запас для коротких
MAX_TOKENS_LONG = 250    # Запас для длинных
TEMPERATURE = 0.8

# Лимиты обработки
MAX_RETRIES = 3
RETRY_DELAY = 2
RATE_LIMIT_DELAY = 0.5
API_TIMEOUT = 30

# Пороги популярности
POPULAR_MOVIE_RATING = 7.0
POPULAR_GENRES = ['drama', 'classics', 'pop', 'rock', 'action', 'comedy', 'thriller']
RECENT_YEAR = 2015

# ==================== СИСТЕМНЫЙ ПРОМПТ ====================

SYSTEM_PROMPT = """Ты — лаконичный культурный обозреватель. 

СТРОГИЕ ПРАВИЛА:
- Пиши СТРОГО 2 предложения
- Каждое предложение ДОЛЖНО заканчиваться точкой
- Сразу переходи к сути, без вступлений
- НЕ используй вводные фразы ("Этот фильм рассказывает...", "Представляем вам...")
- Пиши эмоционально и привлекательно
- Всегда на русском языке"""

# ==================== ШАБЛОНЫ ОПИСАНИЙ ПО ЖАНРАМ ====================

GENRE_TEMPLATES = {
    # Фильмы
    'drama': 'эмоциональная история о человеческих отношениях',
    'action': 'динамичное действие с захватывающими сценами',
    'comedy': 'веселая и легкая история',
    'horror': 'атмосферный и пугающий опыт',
    'thriller': 'напряженный сюжет с неожиданными поворотами',
    'sci-fi': 'увлекательное исследование будущего',
    'romance': 'трогательная история о любви',
    'fantasy': 'магическое путешествие в фантастический мир',
    
    # Музыка
    'pop': 'запоминающиеся мелодии и современное звучание',
    'rock': 'энергичные гитарные риффы',
    'jazz': 'изысканные импровизации',
    'classical': 'величественная музыка',
    'hip-hop': 'ритмичные биты',
    'electronic': 'современное электронное звучание',
    'latin': 'страстные ритмы',
    
    # Книги
    'classics': 'литературный шедевр',
    'fiction': 'увлекательная история',
    'non-fiction': 'познавательное исследование',
    'mystery': 'захватывающая детективная история',
}

# ==================== КЛАСС AI DESCRIBER FINAL ====================

class AIDescriberFinal:
    """Финальная версия генератора описаний"""
    
    def __init__(self, db_path: str = DB_PATH, api_key: str = API_KEY):
        self.db_path = db_path
        self.api_key = api_key
        self.client = None
        self.conn = None
        self.cursor = None
        self.stats = {
            'total_processed': 0,
            'successful': 0,
            'failed': 0,
            'skipped': 0,
            'api_calls': 0,
            'total_tokens': 0,
            'short_prompts': 0,
            'long_prompts': 0,
            'cleaned': 0  # Количество очищенных описаний
        }
    
    def connect_db(self) -> bool:
        """Подключение к базе данных"""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self.cursor = self.conn.cursor()
            return True
        except sqlite3.Error as e:
            print(f"❌ Ошибка подключения к БД: {e}")
            return False
    
    def close_db(self):
        """Закрытие соединения с БД"""
        if self.conn:
            self.conn.close()
    
    def validate_api_key(self) -> bool:
        """Проверка наличия API ключа"""
        if not self.api_key:
            print("❌ ОШИБКА: GROQ_API_KEY не найден в .env файле!")
            print("\nДобавьте в .env файл:")
            print("GROQ_API_KEY=your_key_here")
            return False
        return True
    
    def init_groq_client(self) -> bool:
        """Инициализация Groq клиента"""
        try:
            self.client = Groq(api_key=self.api_key)
            return True
        except Exception as e:
            print(f"❌ Ошибка инициализации Groq: {e}")
            return False
    
    def clean_description(self, text: str) -> str:
        """
        Обрезает текст до последнего знака препинания
        Гарантирует завершенность предложений
        """
        if not text:
            return ""
        
        # Находим все позиции финальных знаков препинания
        punctuation_marks = [m.start() for m in re.finditer(r'[.!?]', text)]
        
        if punctuation_marks:
            # Берем последний знак препинания
            last_mark_pos = punctuation_marks[-1]
            # Возвращаем текст до этого знака включительно
            cleaned = text[:last_mark_pos + 1].strip()
            
            # Проверяем что текст изменился
            if len(cleaned) < len(text.strip()):
                self.stats['cleaned'] += 1
            
            return cleaned
        
        # Если знаков препинания нет - возвращаем как есть
        return text.strip()
    
    def get_items_needing_descriptions(
        self, 
        content_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Получить элементы нуждающиеся в описаниях"""
        
        query = """
            SELECT 
                id,
                type,
                title,
                creator,
                genre,
                year,
                rating,
                mood,
                epoch
            FROM content
            WHERE needs_ai = 1
        """
        
        params = []
        
        if content_type:
            query += " AND type = ?"
            params.append(content_type)
        
        query += """
            ORDER BY 
                CASE 
                    WHEN type = 'movie' AND rating IS NOT NULL THEN rating
                    ELSE 0
                END DESC,
                CASE 
                    WHEN genre IN ('drama', 'classics', 'pop', 'rock', 'action') THEN 1
                    ELSE 0
                END DESC,
                year DESC
            LIMIT ?
        """
        params.append(limit)
        
        self.cursor.execute(query, params)
        
        items = []
        for row in self.cursor.fetchall():
            items.append({
                'id': row['id'],
                'type': row['type'],
                'title': row['title'],
                'creator': row['creator'],
                'genre': row['genre'],
                'year': row['year'],
                'rating': row['rating'],
                'mood': row['mood'],
                'epoch': row['epoch']
            })
        
        return items
    
    def is_likely_known(self, item: Dict) -> bool:
        """Определить, известен ли контент модели"""
        
        if item['type'] == 'movie' and item['rating']:
            if item['rating'] >= POPULAR_MOVIE_RATING:
                return True
        
        if item['genre'] and item['genre'].lower() in POPULAR_GENRES:
            if item['year'] and item['year'] >= RECENT_YEAR:
                return True
        
        if item['genre'] and 'classic' in item['genre'].lower():
            return True
        
        if item['epoch'] and 'classic' in item['epoch'].lower():
            return True
        
        return False
    
    def create_short_prompt(self, item: Dict) -> str:
        """Короткий промпт для известного контента"""
        
        content_type_ru = {
            'book': 'книгу',
            'movie': 'фильм',
            'music': 'трек'
        }[item['type']]
        
        prompt = f"Опиши {content_type_ru} \"{item['title']}\""
        
        if item['creator']:
            if item['type'] == 'book':
                prompt += f" автора {item['creator']}"
            elif item['type'] == 'movie':
                prompt += f" режиссера {item['creator']}"
            else:
                prompt += f" исполнителя {item['creator']}"
        
        if item['year']:
            prompt += f" ({item['year']})"
        
        prompt += "."
        
        return prompt
    
    def create_long_prompt(self, item: Dict) -> str:
        """Подробный промпт для неизвестного контента"""
        
        content_type_ru = {
            'book': 'книга',
            'movie': 'фильм',
            'music': 'музыкальный трек'
        }[item['type']]
        
        prompt = f"Опиши {content_type_ru}:\n"
        prompt += f"Название: {item['title']}\n"
        
        if item['creator']:
            creator_label = {
                'book': 'Автор',
                'movie': 'Режиссер', 
                'music': 'Исполнитель'
            }[item['type']]
            prompt += f"{creator_label}: {item['creator']}\n"
        
        if item['genre']:
            prompt += f"Жанр: {item['genre']}"
            
            # Контекст жанра
            genre_key = item['genre'].lower()
            if genre_key in GENRE_TEMPLATES:
                prompt += f" (обычно {GENRE_TEMPLATES[genre_key]})"
            prompt += "\n"
        
        if item['year']:
            prompt += f"Год: {item['year']}\n"
        
        if item['mood']:
            prompt += f"Настроение: {item['mood']}\n"
        
        prompt += "\nОпиши атмосферу и эмоции."
        
        return prompt
    
    def create_smart_prompt(self, item: Dict) -> Tuple[str, str]:
        """Умный выбор промпта"""
        
        if self.is_likely_known(item):
            return self.create_short_prompt(item), 'short'
        else:
            return self.create_long_prompt(item), 'long'
    
    def call_groq_api(
        self, 
        prompt: str, 
        prompt_type: str,
        retries: int = MAX_RETRIES
    ) -> Optional[str]:
        """Вызов Groq API с системным промптом"""
        
        max_tokens = MAX_TOKENS_SHORT if prompt_type == 'short' else MAX_TOKENS_LONG
        
        for attempt in range(retries):
            try:
                self.stats['api_calls'] += 1
                
                # Вызов Groq API с системным промптом
                completion = self.client.chat.completions.create(
                    model=MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=max_tokens,
                    top_p=1,
                    stream=False
                )
                
                # Извлечение и очистка текста
                if completion.choices and len(completion.choices) > 0:
                    choice = completion.choices[0]
                    raw_description = choice.message.content if choice.message.content else None
                    
                    # ДЕТАЛЬНОЕ ЛОГИРОВАНИЕ
                    if not raw_description:
                        print(f"⚠️ API вернул пустое описание!")
                        print(f"   finish_reason: {choice.finish_reason}")
                        print(f"   message.role: {choice.message.role if hasattr(choice.message, 'role') else 'N/A'}")
                        
                        # Проверяем есть ли reasoning (модель объясняет почему отказала)
                        if hasattr(choice.message, 'reasoning'):
                            print(f"   reasoning: {choice.message.reasoning}")
                        
                        return None
                    
                    # ОЧИСТКА ТЕКСТА
                    description = self.clean_description(raw_description)
                    
                    if not description:
                        print(f"⚠️ После очистки описание стало пустым!")
                        return None
                    
                    # Подсчет токенов
                    if hasattr(completion, 'usage'):
                        self.stats['total_tokens'] += completion.usage.total_tokens
                    
                    # Статистика по типу промпта
                    if prompt_type == 'short':
                        self.stats['short_prompts'] += 1
                    else:
                        self.stats['long_prompts'] += 1
                    
                    return description
                else:
                    print(f"⚠️ Неожиданный формат ответа API")
                    return None
            
            except Exception as e:
                error_msg = str(e)
                
                # Обработка rate limit
                if 'rate_limit' in error_msg.lower() or '429' in error_msg:
                    wait_time = RETRY_DELAY * (2 ** attempt)
                    print(f"⚠️ Rate limit. Ожидание {wait_time}с...")
                    if attempt < retries - 1:
                        time.sleep(wait_time)
                        continue
                
                # Обработка других ошибок
                if attempt < retries - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    print(f"❌ Ошибка API: {error_msg[:100]}")
                
                return None
        
        return None
    
    def update_description(self, item_id: int, description: str) -> bool:
        """Обновить описание и пометить needs_ai = 0"""
        try:
            self.cursor.execute("""
                UPDATE content
                SET description = ?,
                    needs_ai = 0
                WHERE id = ?
            """, (description, item_id))
            
            self.conn.commit()
            return True
        
        except sqlite3.Error as e:
            print(f"❌ Ошибка обновления БД для ID {item_id}: {e}")
            return False
    
    def process_items(self, items: List[Dict], show_progress: bool = True):
        """Обработка списка элементов"""
        
        total = len(items)
        print(f"\n🤖 ФИНАЛЬНАЯ ГЕНЕРАЦИЯ AI-ОПИСАНИЙ")
        print("=" * 70)
        print(f"Элементов для обработки: {total}")
        print(f"Модель: {MODEL}")
        print(f"Системный промпт: СТРОГО 2 предложения")
        print(f"Автоочистка: Включена")
        print("=" * 70)
        
        for i, item in enumerate(items, 1):
            emoji = {'book': '📖', 'movie': '🎬', 'music': '🎵'}[item['type']]
            
            if show_progress:
                print(f"\n[{i}/{total}] {emoji} {item['title']}")
                if item['creator']:
                    print(f"        by {item['creator']}")
            
            # Создаем умный промпт
            prompt, prompt_type = self.create_smart_prompt(item)
            
            # Показываем тип промпта
            if show_progress:
                prompt_icon = "⚡" if prompt_type == 'short' else "📝"
                print(f"        {prompt_icon} Промпт: {'популярный' if prompt_type == 'short' else 'детальный'}")
            
            # Генерируем описание
            description = self.call_groq_api(prompt, prompt_type)
            
            if description:
                # Обновляем в БД
                if self.update_description(item['id'], description):
                    self.stats['successful'] += 1
                    if show_progress:
                        preview = description[:70] + '...' if len(description) > 70 else description
                        print(f"        ✅ {preview}")
                else:
                    self.stats['failed'] += 1
                    if show_progress:
                        print(f"        ❌ Ошибка сохранения")
            else:
                self.stats['failed'] += 1
                if show_progress:
                    print(f"        ❌ Ошибка генерации")
            
            self.stats['total_processed'] += 1
            
            # Задержка между запросами
            if i < total:
                time.sleep(RATE_LIMIT_DELAY)
        
        print("\n" + "=" * 70)
    
    def show_summary(self):
        """Показать итоговую статистику"""
        print("\n📊 ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 70)
        print(f"Всего обработано: {self.stats['total_processed']}")
        print(f"✅ Успешно: {self.stats['successful']}")
        print(f"❌ Ошибки: {self.stats['failed']}")
        print(f"🔌 API вызовов: {self.stats['api_calls']}")
        print(f"📝 Всего токенов: {self.stats['total_tokens']:,}")
        print(f"✂️ Очищено описаний: {self.stats['cleaned']}")
        print(f"")
        print(f"⚡ Коротких промптов: {self.stats['short_prompts']}")
        print(f"📝 Длинных промптов: {self.stats['long_prompts']}")
        
        if self.stats['total_processed'] > 0:
            success_rate = (self.stats['successful'] / self.stats['total_processed']) * 100
            known_rate = (self.stats['short_prompts'] / self.stats['total_processed']) * 100
            print(f"📈 Успешность: {success_rate:.1f}%")
            print(f"🎯 Известный контент: {known_rate:.1f}%")
        
        # Примерная стоимость
        if self.stats['total_tokens'] > 0:
            input_tokens = self.stats['total_tokens'] * 0.6
            output_tokens = self.stats['total_tokens'] * 0.4
            cost = (input_tokens / 1_000_000 * 0.59) + (output_tokens / 1_000_000 * 0.79)
            print(f"💰 Примерная стоимость: ${cost:.4f}")
        
        print("=" * 70)
    
    def show_recommendations(self):
        """Показать рекомендации"""
        print("\n💡 РЕКОМЕНДАЦИИ")
        print("=" * 70)
        
        self.cursor.execute("SELECT COUNT(*) FROM content WHERE needs_ai = 1")
        remaining = self.cursor.fetchone()[0]
        
        if remaining > 0:
            print(f"\n📝 Осталось элементов без описаний: {remaining}")
            print(f"   Запустите еще раз:")
            print(f"   python scripts/tools/ai_describer.py --limit=100")
        else:
            print(f"\n🎉 ВСЕ ЭЛЕМЕНТЫ ИМЕЮТ ОПИСАНИЯ!")
        
        print(f"\n📊 Проверьте результаты:")
        print(f"   python scripts/tools/db_inspector.py")
        
        print("\n" + "=" * 70)
    
    def run(
        self,
        content_type: Optional[str] = None,
        limit: int = 100,
        dry_run: bool = False
    ):
        """Запуск процесса генерации описаний"""
        
        print("\n" + "=" * 70)
        print("🤖 AI DESCRIBER FINAL - System Prompt Edition".center(70))
        print("=" * 70)
        
        if not self.validate_api_key():
            return False
        
        print(f"✅ API ключ найден")
        
        if not self.init_groq_client():
            return False
        
        print(f"✅ Groq клиент инициализирован")
        
        if not self.connect_db():
            return False
        
        print(f"✅ Подключение к БД успешно")
        
        try:
            print(f"\n🔍 Поиск элементов нуждающихся в описаниях...")
            if content_type:
                print(f"   Фильтр: тип = {content_type}")
            print(f"   Лимит: {limit}")
            
            items = self.get_items_needing_descriptions(content_type, limit)
            
            if not items:
                print(f"\n✅ Не найдено элементов нуждающихся в описаниях!")
                return True
            
            print(f"\n📋 Найдено элементов: {len(items)}")
            
            # Распределение по типам
            type_counts = {}
            for item in items:
                type_counts[item['type']] = type_counts.get(item['type'], 0) + 1
            
            print(f"\n📊 Распределение по типам:")
            for ct, count in sorted(type_counts.items()):
                emoji = {'book': '📖', 'movie': '🎬', 'music': '🎵'}[ct]
                print(f"   {emoji} {ct}: {count}")
            
            # Анализ популярности
            known_count = sum(1 for item in items if self.is_likely_known(item))
            unknown_count = len(items) - known_count
            print(f"\n🎯 Анализ популярности:")
            print(f"   ⚡ Известный контент: {known_count}")
            print(f"   📝 Неизвестный контент: {unknown_count}")
            
            if dry_run:
                print(f"\n⚠️ DRY RUN режим - описания НЕ будут сохранены")
                return True
            
            print(f"\n⚠️ ВНИМАНИЕ!")
            print(f"   Будет обработано: {len(items)}")
            print(f"   Примерное время: ~{len(items) * 2} секунд")
            
            # Примерная стоимость
            avg_tokens = (known_count * 120) + (unknown_count * 180)
            estimated_cost = (avg_tokens / 1_000_000) * 0.7
            print(f"   Примерная стоимость: ${estimated_cost:.4f}")
            
            response = input(f"\n❓ Начать генерацию описаний? (yes/no): ").strip().lower()
            
            if response not in ['yes', 'y', 'да', 'д']:
                print(f"\n❌ Операция отменена пользователем")
                return False
            
            start_time = time.time()
            self.process_items(items)
            elapsed_time = time.time() - start_time
            
            self.show_summary()
            print(f"\n⏱️ Время выполнения: {elapsed_time:.1f} секунд")
            
            self.show_recommendations()
            
            print(f"\n✅ ГЕНЕРАЦИЯ ЗАВЕРШЕНА!")
            print("=" * 70 + "\n")
            
            return True
        
        finally:
            self.close_db()

# ==================== CLI ====================

def main():
    parser = argparse.ArgumentParser(
        description='🤖 AI Describer FINAL - Системный промпт + Автоочистка',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python ai_describer.py --limit=50
  python ai_describer.py --type books --limit=100
  python ai_describer.py --dry-run
        """
    )
    
    parser.add_argument(
        '--type',
        choices=['books', 'movies', 'music'],
        help='Тип контента для обработки'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=100,
        help='Максимальное количество элементов'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Предпросмотр без генерации'
    )
    
    parser.add_argument(
        '--db',
        default=DB_PATH,
        help=f'Путь к базе данных'
    )
    
    args = parser.parse_args()
    
    content_type = None
    if args.type:
        content_type = args.type[:-1]
    
    describer = AIDescriberFinal(db_path=args.db)
    
    describer.run(
        content_type=content_type,
        limit=args.limit,
        dry_run=args.dry_run
    )

if __name__ == "__main__":
    main()