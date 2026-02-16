#!/usr/bin/env python3
"""
🌍 TRANSLATOR - Универсальный переводчик описаний

Функции:
- Определяет язык существующих описаний
- Переводит на недостающие языки
- Использует дешевую модель llama-3.1-8b-instant
- Сохраняет в отдельные колонки: description_ru, description_en, description_kk

Автор: Coffee Books AI Team
Версия: 1.0
"""

import sqlite3
import os
import time
import re
import argparse
from typing import Dict, Optional, List
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
MODEL_TRANSLATE = 'openai/gpt-oss-120b'  # Проверено - работает!

# Настройки перевода
TEMPERATURE = 0.3  # Низкая температура = точный перевод
MAX_TOKENS = 300
MAX_RETRIES = 3
RETRY_DELAY = 2

# Языки
LANGUAGES = {
    'ru': 'Russian',
    'en': 'English', 
    'kk': 'Kazakh'
}

# ==================== КЛАСС ПЕРЕВОДЧИКА ====================

class UniversalTranslator:
    """Универсальный переводчик с определением языка"""
    
    def __init__(self, db_path: str = DB_PATH, api_key: str = API_KEY):
        self.db_path = db_path
        self.api_key = api_key
        self.client = None
        self.conn = None
        self.cursor = None
        self.stats = {
            'total': 0,
            'russian_original': 0,
            'english_original': 0,
            'unknown_original': 0,
            'no_description': 0,
            'translations': 0,
            'total_tokens': 0,
            'failed': 0
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
    
    def detect_language(self, text: str) -> str:
        """
        Определить язык текста
        Возвращает: 'ru', 'en', или 'unknown'
        """
        if not text or len(text) < 10:
            return 'unknown'
        
        # Подсчет символов разных алфавитов
        russian_chars = len(re.findall(r'[а-яА-ЯёЁ]', text))
        english_chars = len(re.findall(r'[a-zA-Z]', text))
        
        # Определяем преобладающий язык
        if russian_chars > english_chars * 2:  # Явное преобладание русского
            return 'ru'
        elif english_chars > russian_chars * 2:  # Явное преобладание английского
            return 'en'
        else:
            return 'unknown'
    
    def prepare_database(self) -> bool:
        """
        Подготовить базу данных: добавить колонки для переводов
        """
        try:
            # Проверяем существуют ли уже колонки
            self.cursor.execute("PRAGMA table_info(content)")
            columns = [row[1] for row in self.cursor.fetchall()]
            
            columns_to_add = []
            if 'description_ru' not in columns:
                columns_to_add.append('description_ru')
            if 'description_en' not in columns:
                columns_to_add.append('description_en')
            if 'description_kk' not in columns:
                columns_to_add.append('description_kk')
            
            if columns_to_add:
                print(f"\n📋 Добавляем колонки: {', '.join(columns_to_add)}")
                for col in columns_to_add:
                    self.cursor.execute(f"ALTER TABLE content ADD COLUMN {col} TEXT")
                self.conn.commit()
                print(f"✅ Колонки добавлены")
            else:
                print(f"\n✅ Все необходимые колонки уже существуют")
            
            return True
        
        except sqlite3.Error as e:
            print(f"❌ Ошибка подготовки БД: {e}")
            return False
    
    def translate_text(self, text: str, target_lang: str) -> Optional[str]:
        """
        Перевести текст на указанный язык
        
        Args:
            text: Текст для перевода
            target_lang: Целевой язык ('ru', 'en', 'kk')
        
        Returns:
            Переведенный текст или None при ошибке
        """
        
        target_language_name = LANGUAGES.get(target_lang, target_lang)
        
        # Простой и короткий промпт = меньше токенов!
        prompt = f"Translate to {target_language_name}:\n\n{text}"
        
        for attempt in range(MAX_RETRIES):
            try:
                completion = self.client.chat.completions.create(
                    model=MODEL_TRANSLATE,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS
                )
                
                if completion.choices and len(completion.choices) > 0:
                    translation = completion.choices[0].message.content.strip()
                    
                    # Подсчет токенов
                    if hasattr(completion, 'usage'):
                        self.stats['total_tokens'] += completion.usage.total_tokens
                    
                    self.stats['translations'] += 1
                    
                    return translation
                else:
                    return None
            
            except Exception as e:
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                    continue
                else:
                    print(f"      ❌ Ошибка перевода: {str(e)[:100]}")
                    return None
        
        return None
    
    def get_items_to_translate(self, limit: int = None) -> List[Dict]:
        """Получить элементы для перевода"""
        
        query = """
            SELECT 
                id,
                type,
                title,
                description,
                description_ru,
                description_en,
                description_kk
            FROM content
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        self.cursor.execute(query)
        
        items = []
        for row in self.cursor.fetchall():
            items.append({
                'id': row['id'],
                'type': row['type'],
                'title': row['title'],
                'description': row['description'],
                'description_ru': row['description_ru'],
                'description_en': row['description_en'],
                'description_kk': row['description_kk']
            })
        
        return items
    
    def update_translations(self, item_id: int, translations: Dict[str, str]) -> bool:
        """Обновить переводы в БД"""
        try:
            set_clauses = []
            values = []
            
            for lang, text in translations.items():
                if text:
                    set_clauses.append(f"description_{lang} = ?")
                    values.append(text)
            
            if not set_clauses:
                return True
            
            values.append(item_id)
            query = f"UPDATE content SET {', '.join(set_clauses)} WHERE id = ?"
            
            self.cursor.execute(query, values)
            self.conn.commit()
            
            return True
        
        except sqlite3.Error as e:
            print(f"❌ Ошибка обновления БД для ID {item_id}: {e}")
            return False
    
    def process_item(self, item: Dict, show_progress: bool = True) -> bool:
        """
        Обработать один элемент:
        1. Определить язык существующего описания
        2. Сохранить в соответствующую колонку
        3. Перевести на недостающие языки
        """
        
        self.stats['total'] += 1
        
        # Получаем оригинальное описание
        original_description = item['description']
        
        if not original_description:
            self.stats['no_description'] += 1
            if show_progress:
                print(f"      ⚠️ Нет описания, пропускаем")
            return False
        
        # Определяем язык оригинала
        original_lang = self.detect_language(original_description)
        
        if show_progress:
            lang_emoji = {'ru': '🇷🇺', 'en': '🇬🇧', 'unknown': '❓'}
            print(f"      {lang_emoji.get(original_lang, '❓')} Язык оригинала: {original_lang}")
        
        # Словарь для сохранения переводов
        translations = {}
        
        # СЦЕНАРИЙ 1: Оригинал на русском
        if original_lang == 'ru':
            self.stats['russian_original'] += 1
            translations['ru'] = original_description
            
            # Переводим на английский
            if not item['description_en']:
                if show_progress:
                    print(f"      📝 Перевод RU → EN...")
                translations['en'] = self.translate_text(original_description, 'en')
            else:
                translations['en'] = item['description_en']
            
            # Переводим на казахский
            if not item['description_kk']:
                if show_progress:
                    print(f"      📝 Перевод RU → KK...")
                translations['kk'] = self.translate_text(original_description, 'kk')
            else:
                translations['kk'] = item['description_kk']
        
        # СЦЕНАРИЙ 2: Оригинал на английском
        elif original_lang == 'en':
            self.stats['english_original'] += 1
            translations['en'] = original_description
            
            # Переводим на русский
            if not item['description_ru']:
                if show_progress:
                    print(f"      📝 Перевод EN → RU...")
                translations['ru'] = self.translate_text(original_description, 'ru')
            else:
                translations['ru'] = item['description_ru']
            
            # Переводим на казахский
            if not item['description_kk']:
                if show_progress:
                    print(f"      📝 Перевод EN → KK...")
                translations['kk'] = self.translate_text(original_description, 'kk')
            else:
                translations['kk'] = item['description_kk']
        
        # СЦЕНАРИЙ 3: Неопределенный язык
        else:
            self.stats['unknown_original'] += 1
            if show_progress:
                print(f"      ⚠️ Не удалось определить язык, пропускаем")
            return False
        
        # Проверяем успешность переводов
        if any(v is None for v in translations.values()):
            self.stats['failed'] += 1
            if show_progress:
                print(f"      ❌ Не все переводы успешны")
            return False
        
        # Сохраняем в БД
        if self.update_translations(item['id'], translations):
            if show_progress:
                print(f"      ✅ Сохранено")
            return True
        else:
            self.stats['failed'] += 1
            return False
    
    def process_all(self, limit: int = None):
        """Обработать все элементы"""
        
        print(f"\n🌍 УНИВЕРСАЛЬНЫЙ ПЕРЕВОДЧИК")
        print("=" * 70)
        print(f"Модель: {MODEL_TRANSLATE}")
        print(f"Языки: RU ⇄ EN ⇄ KK")
        print("=" * 70)
        
        items = self.get_items_to_translate(limit)
        total = len(items)
        
        print(f"\n📋 Найдено элементов: {total}")
        
        if not items:
            print(f"\n✅ Нет элементов для обработки!")
            return
        
        # Подтверждение
        print(f"\n⚠️ ВНИМАНИЕ!")
        print(f"   Будет обработано элементов: {total}")
        
        # Примерная стоимость
        avg_tokens_per_translation = 120
        estimated_translations = total * 2  # В среднем 2 перевода на элемент
        estimated_tokens = estimated_translations * avg_tokens_per_translation
        estimated_cost = (estimated_tokens / 1_000_000) * 0.065  # Средняя цена llama-3.1-8b
        
        print(f"   Примерное количество переводов: {estimated_translations}")
        print(f"   Примерная стоимость: ${estimated_cost:.4f}")
        
        response = input(f"\n❓ Начать перевод? (yes/no): ").strip().lower()
        
        if response not in ['yes', 'y', 'да', 'д']:
            print(f"\n❌ Операция отменена пользователем")
            return
        
        print(f"\n🚀 НАЧАЛО ПЕРЕВОДА")
        print("=" * 70)
        
        start_time = time.time()
        
        for i, item in enumerate(items, 1):
            emoji = {'book': '📖', 'movie': '🎬', 'music': '🎵'}[item['type']]
            
            print(f"\n[{i}/{total}] {emoji} {item['title']}")
            
            self.process_item(item, show_progress=True)
        
        elapsed_time = time.time() - start_time
        
        print("\n" + "=" * 70)
        
        # Статистика
        self.show_summary(elapsed_time)
    
    def show_summary(self, elapsed_time: float):
        """Показать итоговую статистику"""
        print("\n📊 ИТОГОВАЯ СТАТИСТИКА")
        print("=" * 70)
        print(f"Всего обработано: {self.stats['total']}")
        print(f"")
        print(f"📝 По языкам оригиналов:")
        print(f"   🇷🇺 Русские: {self.stats['russian_original']}")
        print(f"   🇬🇧 Английские: {self.stats['english_original']}")
        print(f"   ❓ Неопределенные: {self.stats['unknown_original']}")
        print(f"   ⚠️ Без описания: {self.stats['no_description']}")
        print(f"")
        print(f"🔄 Переводов выполнено: {self.stats['translations']}")
        print(f"❌ Ошибок: {self.stats['failed']}")
        print(f"📝 Всего токенов: {self.stats['total_tokens']:,}")
        
        # Стоимость
        if self.stats['total_tokens'] > 0:
            input_tokens = self.stats['total_tokens'] * 0.5
            output_tokens = self.stats['total_tokens'] * 0.5
            cost = (input_tokens / 1_000_000 * 0.05) + (output_tokens / 1_000_000 * 0.08)
            print(f"💰 Стоимость: ${cost:.4f}")
        
        print(f"⏱️ Время выполнения: {elapsed_time:.1f} секунд")
        print("=" * 70)
    
    def run(self, limit: int = None):
        """Запуск процесса перевода"""
        
        print("\n" + "=" * 70)
        print("🌍 УНИВЕРСАЛЬНЫЙ ПЕРЕВОДЧИК".center(70))
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
        
        if not self.prepare_database():
            return False
        
        try:
            self.process_all(limit)
            
            print(f"\n✅ ПЕРЕВОД ЗАВЕРШЕН!")
            print("=" * 70 + "\n")
            
            return True
        
        finally:
            self.close_db()

# ==================== CLI ====================

def main():
    parser = argparse.ArgumentParser(
        description='🌍 Универсальный переводчик описаний',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  python translate_descriptions.py --limit=10    # Тест на 10 элементах
  python translate_descriptions.py               # Все элементы
        """
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Максимальное количество элементов для обработки (для теста)'
    )
    
    parser.add_argument(
        '--db',
        default=DB_PATH,
        help=f'Путь к базе данных (по умолчанию: {DB_PATH})'
    )
    
    args = parser.parse_args()
    
    translator = UniversalTranslator(db_path=args.db)
    
    translator.run(limit=args.limit)

if __name__ == "__main__":
    main()