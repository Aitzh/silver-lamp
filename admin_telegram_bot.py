#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🤖 ADMIN TELEGRAM BOT v2.1 - ИСПРАВЛЕННАЯ версия с единой логикой

Изменения в v2.1:
- Убрана двойная логика (is_used / max_activations)
- Одноразовый код = max_activations: 1
- Многоразовый код = max_activations: N
- Единая система подсчёта через current_activations
"""

import os
import sys
import sqlite3
import secrets
import string
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    CallbackQueryHandler, 
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
from dotenv import load_dotenv

# Исправление кодировки для Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

os.environ['PYTHONIOENCODING'] = 'utf-8'

load_dotenv()

# Утилита безопасного вывода
def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        safe_args = []
        for arg in args:
            if isinstance(arg, str):
                safe_arg = arg.encode('ascii', 'ignore').decode('ascii')
                safe_args.append(safe_arg)
            else:
                safe_args.append(arg)
        print(*safe_args, **kwargs)

# Настройки
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ACCESS_DB = os.getenv('ACCESS_DB_PATH', 'access.db')
SUPER_ADMIN_ID = os.getenv('SUPER_ADMIN_ID', '1530115915')

CODE_TYPES = {
    '1day': {'hours': 24, 'name': '📅 1 День', 'emoji': '⚡'},
    '7days': {'hours': 168, 'name': '📅 7 Дней', 'emoji': '🔥'},
    '30days': {'hours': 720, 'name': '📅 30 Дней', 'emoji': '👑'}
}

WAITING_ADMIN_ID = 1
WAITING_ADMIN_NAME = 2

# База данных
class Database:
    def __init__(self, db_path=ACCESS_DB):
        self.db_path = db_path
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def generate_code(self, code_type, generated_by, max_activations=1):
        """
        Генерация кода с ЕДИНОЙ логикой
        max_activations = 1 для одноразового
        max_activations = N для многоразового
        """
        alphabet = 'ABCDEFGHJKMNPQRSTUVWXYZ23456789'
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        while True:
            code = ''.join(secrets.choice(alphabet) for _ in range(8))
            code = f"{code[:4]}-{code[4:]}"
            
            cursor.execute('SELECT id FROM access_codes WHERE code = ?', (code,))
            if not cursor.fetchone():
                break
        
        duration_hours = CODE_TYPES[code_type]['hours']
        expires_at = datetime.now() + timedelta(hours=duration_hours)
        
        # ВАЖНО: max_activations теперь ВСЕГДА число (никогда не NULL)
        cursor.execute('''
            INSERT INTO access_codes 
            (code, code_type, duration_hours, generated_by, expires_at, max_activations, current_activations)
            VALUES (?, ?, ?, ?, ?, ?, 0)
        ''', (code, code_type, duration_hours, generated_by, expires_at, max_activations))
        
        code_id = cursor.lastrowid
        
        cursor.execute('''
            UPDATE admin_users 
            SET codes_generated_total = codes_generated_total + 1,
                last_seen = CURRENT_TIMESTAMP
            WHERE telegram_id = ?
        ''', (str(generated_by),))
        
        conn.commit()
        conn.close()
        
        return {
            'id': code_id,
            'code': code,
            'type': code_type,
            'duration': duration_hours,
            'expires_at': expires_at,
            'max_activations': max_activations
        }
    
    def get_stats(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Используем current_activations для подсчёта использованных
# Используем COALESCE для обработки пустых значений (NULL)
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN current_activations >= COALESCE(max_activations, 1) THEN 1 ELSE 0 END) as used,
                SUM(CASE WHEN current_activations < COALESCE(max_activations, 1) THEN 1 ELSE 0 END) as unused
            FROM access_codes
        ''')
        total_stats = cursor.fetchone()
        
        cursor.execute('''
            SELECT 
                code_type,
                COUNT(*) as total,
                SUM(CASE WHEN current_activations >= max_activations THEN 1 ELSE 0 END) as used
            FROM access_codes
            GROUP BY code_type
        ''')
        type_stats = cursor.fetchall()
        
        cursor.execute('''
            SELECT COUNT(*) 
            FROM user_sessions 
            WHERE is_active = 1 AND expires_at > datetime('now')
        ''')
        active_sessions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM admin_users WHERE is_active = 1')
        admin_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total': total_stats[0] or 0,
            'used': total_stats[1] or 0,
            'unused': total_stats[2] or 0,
            'by_type': {row[0]: {'total': row[1], 'used': row[2] or 0} for row in type_stats},
            'active_sessions': active_sessions,
            'admin_count': admin_count
        }
    
    def is_admin(self, telegram_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT is_active FROM admin_users 
            WHERE telegram_id = ? AND is_active = 1
        ''', (str(telegram_id),))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def is_super_admin(self, telegram_id):
        return str(telegram_id) == str(SUPER_ADMIN_ID)
    
    def add_admin(self, telegram_id, username=None, full_name=None, added_by=None):
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO admin_users (telegram_id, username, full_name)
                VALUES (?, ?, ?)
            ''', (str(telegram_id), username, full_name))
            conn.commit()
            conn.close()
            return True, "Администратор успешно добавлен"
        except sqlite3.IntegrityError:
            conn.close()
            return False, "Этот пользователь уже является администратором"
    
    def remove_admin(self, telegram_id):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE admin_users 
            SET is_active = 0 
            WHERE telegram_id = ?
        ''', (str(telegram_id),))
        affected = cursor.rowcount
        conn.commit()
        conn.close()
        return affected > 0
    
    def get_admins(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT telegram_id, username, full_name, is_active, 
                   codes_generated_total, last_seen
            FROM admin_users
            ORDER BY is_active DESC, codes_generated_total DESC
        ''')
        admins = cursor.fetchall()
        conn.close()
        return admins

db = Database()

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    if not db.is_admin(user_id) and not db.is_super_admin(user_id):
        await update.message.reply_text(
            "❌ *Доступ запрещён*\n\n"
            "Этот бот предназначен только для администраторов Coffee Books AI.\n\n"
            f"Ваш Telegram ID: `{user_id}`",
            parse_mode='Markdown'
        )
        return
    
    keyboard = [
        [
            InlineKeyboardButton("⚡ 1 День", callback_data="gen_1day"),
            InlineKeyboardButton("🔥 7 Дней", callback_data="gen_7days")
        ],
        [InlineKeyboardButton("👑 30 Дней", callback_data="gen_30days")],
        [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
    ]
    
    if db.is_super_admin(user_id):
        keyboard.append([InlineKeyboardButton("👥 Управление админами", callback_data="admin_manage")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    is_super = "👑 SUPER ADMIN" if db.is_super_admin(user_id) else "🔐 Администратор"
    
    await update.message.reply_text(
        f"🤖 *Coffee Books AI - Админ Панель*\n\n"
        f"Привет, {user_name}! {is_super}\n\n"
        f"Выберите тип кода доступа для генерации:\n\n"
        f"⚡ *1 День* - быстрый доступ\n"
        f"🔥 *7 Дней* - стандартный доступ\n"
        f"👑 *30 Дней* - премиум доступ",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    action = query.data
    
    if not db.is_admin(user_id) and not db.is_super_admin(user_id):
        await query.edit_message_text("❌ У вас нет доступа к этой функции.")
        return
    
    # ГЕНЕРАЦИЯ КОДОВ
    if action.startswith('gen_'):
        code_type = action.replace('gen_', '')
        
        if code_type not in CODE_TYPES:
            await query.edit_message_text("❌ Неверный тип кода")
            return
        
        context.user_data['selected_code_type'] = code_type
        
        keyboard = [
            [InlineKeyboardButton("🎫 Одноразовый код", callback_data=f"activation_single_{code_type}")],
            [
                InlineKeyboardButton("1 активация", callback_data=f"activation_1_{code_type}"),
                InlineKeyboardButton("5 активаций", callback_data=f"activation_5_{code_type}")
            ],
            [
                InlineKeyboardButton("10 активаций", callback_data=f"activation_10_{code_type}"),
                InlineKeyboardButton("20 активаций", callback_data=f"activation_20_{code_type}")
            ],
            [InlineKeyboardButton("50 активаций", callback_data=f"activation_50_{code_type}")],
            [InlineKeyboardButton("« Назад", callback_data="menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        type_info = CODE_TYPES[code_type]
        await query.edit_message_text(
            f"{type_info['emoji']} *{type_info['name']}*\n\n"
            f"Выберите количество активаций:\n\n"
            f"🎫 *Одноразовый* - 1 человек\n"
            f"🎫 *Многоразовый* - несколько человек\n\n"
            f"Каждая активация даёт доступ на {type_info['hours']} часов.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    # ВЫБОР КОЛИЧЕСТВА АКТИВАЦИЙ
    elif action.startswith('activation_'):
        parts = action.split('_')
        activation_count = parts[1]
        code_type = parts[2]
        
        # ИСПРАВЛЕНО: одноразовый = max_activations: 1 (не NULL!)
        if activation_count == 'single':
            max_activations = 1
        else:
            max_activations = int(activation_count)
        
        try:
            result = db.generate_code(code_type, user_id, max_activations)
            type_info = CODE_TYPES[code_type]
            
            message = (
                f"✅ *Код успешно создан!*\n\n"
                f"🎫 Код: `{result['code']}`\n"
                f"{type_info['emoji']} Тип: {type_info['name']}\n"
                f"⏱ Длительность: {result['duration']} часов\n"
                f"🔐 Активаций: {max_activations}\n"
                f"📅 Действителен до: {result['expires_at'].strftime('%d.%m.%Y %H:%M')}\n\n"
                f"Отправьте этот код пользователю для доступа к системе."
            )
            
            # Логирование (убрана переменная activation_text)
            safe_print(f"✅ [{user_id}] создал код {result['code']} ({code_type}, {max_activations} акт.)")
            
            keyboard = [
                [InlineKeyboardButton("🔄 Создать ещё", callback_data=f"gen_{code_type}")],
                [InlineKeyboardButton("« Главное меню", callback_data="menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    
    # СТАТИСТИКА
    elif action == 'stats':
        stats = db.get_stats()
        
        message = (
            "📊 *Статистика системы*\n\n"
            f"📝 Всего кодов: {stats['total']}\n"
            f"✅ Исчерпано: {stats['used']}\n"
            f"⏳ Доступно: {stats['unused']}\n"
            f"🔥 Активных сессий: {stats['active_sessions']}\n"
            f"👥 Администраторов: {stats['admin_count']}\n\n"
            "*По типам:*\n"
        )
        
        for code_type, data in stats['by_type'].items():
            type_info = CODE_TYPES.get(code_type, {})
            emoji = type_info.get('emoji', '📄')
            name = type_info.get('name', code_type)
            message += f"{emoji} {name}: {data['used']}/{data['total']}\n"
        
        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    # УПРАВЛЕНИЕ АДМИНАМИ
    elif action == 'admin_manage':
        if not db.is_super_admin(user_id):
            await query.edit_message_text("❌ Эта функция доступна только супер-админу.")
            return
        
        admins = db.get_admins()
        
        message = "👥 *Управление администраторами*\n\n"
        
        if admins:
            for admin in admins:
                tid, username, name, is_active, codes, last_seen = admin
                status = "✅" if is_active else "❌"
                username_str = f"@{username}" if username else "без username"
                name_str = name or "Без имени"
                is_super = " 👑" if str(tid) == str(SUPER_ADMIN_ID) else ""
                message += f"{status} `{tid}` - {name_str} ({username_str}){is_super}\n"
                message += f"   📊 Кодов создано: {codes}\n\n"
        else:
            message += "_Нет администраторов_\n"
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить админа", callback_data="admin_add")],
            [InlineKeyboardButton("➖ Удалить админа", callback_data="admin_remove")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif action == 'admin_add':
        if not db.is_super_admin(user_id):
            await query.edit_message_text("❌ Эта функция доступна только супер-админу.")
            return
        
        context.user_data['waiting_for'] = 'admin_id'
        
        await query.edit_message_text(
            "➕ *Добавление администратора*\n\n"
            "Отправьте Telegram ID нового админа.\n\n"
            "💡 Пользователь может узнать свой ID через бота @userinfobot\n\n"
            "Для отмены отправьте /cancel",
            parse_mode='Markdown'
        )
    
    elif action == 'admin_remove':
        if not db.is_super_admin(user_id):
            await query.edit_message_text("❌ Эта функция доступна только супер-админу.")
            return
        
        context.user_data['waiting_for'] = 'admin_remove_id'
        
        admins = db.get_admins()
        message = "➖ *Удаление администратора*\n\n"
        message += "Отправьте Telegram ID админа для удаления:\n\n"
        
        for admin in admins:
            tid, username, name, is_active, codes, _ = admin
            if is_active and str(tid) != str(SUPER_ADMIN_ID):
                username_str = f"@{username}" if username else ""
                name_str = name or "Без имени"
                message += f"• `{tid}` - {name_str} {username_str}\n"
        
        message += "\nДля отмены отправьте /cancel"
        
        await query.edit_message_text(message, parse_mode='Markdown')
    
    elif action == 'menu':
        keyboard = [
            [
                InlineKeyboardButton("⚡ 1 День", callback_data="gen_1day"),
                InlineKeyboardButton("🔥 7 Дней", callback_data="gen_7days")
            ],
            [InlineKeyboardButton("👑 30 Дней", callback_data="gen_30days")],
            [InlineKeyboardButton("📊 Статистика", callback_data="stats")]
        ]
        
        if db.is_super_admin(user_id):
            keyboard.append([InlineKeyboardButton("👥 Управление админами", callback_data="admin_manage")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "🤖 *Coffee Books AI - Админ Панель*\n\n"
            "Выберите действие:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    if not db.is_super_admin(user_id):
        return
    
    waiting_for = context.user_data.get('waiting_for')
    
    if waiting_for == 'admin_id':
        try:
            new_admin_id = int(text)
            context.user_data['new_admin_id'] = new_admin_id
            context.user_data['waiting_for'] = 'admin_name'
            
            await update.message.reply_text(
                f"📝 ID: `{new_admin_id}`\n\n"
                "Теперь отправьте имя нового админа (или /skip чтобы пропустить):",
                parse_mode='Markdown'
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат. Telegram ID должен быть числом.\n"
                "Попробуйте ещё раз или отправьте /cancel для отмены."
            )
    
    elif waiting_for == 'admin_name':
        new_admin_id = context.user_data.get('new_admin_id')
        name = text if text != '/skip' else None
        
        success, message = db.add_admin(new_admin_id, full_name=name)
        
        context.user_data.clear()
        
        if success:
            await update.message.reply_text(
                f"✅ *Администратор добавлен!*\n\n"
                f"ID: `{new_admin_id}`\n"
                f"Имя: {name or 'Не указано'}\n\n"
                f"Теперь этот пользователь может использовать бота для генерации кодов.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(f"❌ {message}")
    
    elif waiting_for == 'admin_remove_id':
        try:
            remove_id = int(text)
            
            if str(remove_id) == str(SUPER_ADMIN_ID):
                await update.message.reply_text("❌ Нельзя удалить супер-админа!")
                context.user_data.clear()
                return
            
            success = db.remove_admin(remove_id)
            context.user_data.clear()
            
            if success:
                await update.message.reply_text(
                    f"✅ Администратор `{remove_id}` удалён.",
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text("❌ Администратор не найден.")
                
        except ValueError:
            await update.message.reply_text(
                "❌ Неверный формат. Telegram ID должен быть числом."
            )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Операция отменена.\n\nОтправьте /start для возврата в меню."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    message = (
        "📚 *Справка по боту Coffee Books AI*\n\n"
        "*Команды:*\n"
        "/start - Главное меню\n"
        "/stats - Статистика\n"
        "/help - Эта справка\n"
        "/cancel - Отмена операции\n\n"
    )
    
    if db.is_super_admin(user_id):
        message += (
            "*Команды супер-админа:*\n"
            "/addadmin <id> - Добавить админа\n"
            "/removeadmin <id> - Удалить админа\n"
            "/admins - Список админов\n"
        )
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not db.is_admin(user_id) and not db.is_super_admin(user_id):
        await update.message.reply_text("❌ Нет доступа.")
        return
    
    stats = db.get_stats()
    
    message = (
        "📊 *Статистика Coffee Books AI*\n\n"
        f"📝 Всего кодов: {stats['total']}\n"
        f"✅ Исчерпано: {stats['used']}\n"
        f"⏳ Доступно: {stats['unused']}\n"
        f"🔥 Активных сессий: {stats['active_sessions']}\n"
        f"👥 Админов: {stats['admin_count']}\n"
    )
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not db.is_super_admin(user_id):
        await update.message.reply_text("❌ Эта команда доступна только супер-админу.")
        return
    
    admins = db.get_admins()
    
    message = "👥 *Список администраторов:*\n\n"
    
    for admin in admins:
        tid, username, name, is_active, codes, last_seen = admin
        status = "✅" if is_active else "❌"
        is_super = " 👑" if str(tid) == str(SUPER_ADMIN_ID) else ""
        message += f"{status} `{tid}` - {name or 'N/A'}{is_super} ({codes} кодов)\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

def main():
    if not BOT_TOKEN:
        safe_print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN не найден!")
        safe_print("\nДобавьте в .env файл:")
        safe_print("TELEGRAM_BOT_TOKEN=your_bot_token_here")
        safe_print("SUPER_ADMIN_ID=your_telegram_id")
        return
    
    safe_print("🤖 ═══════════════════════════════════════════")
    safe_print("🤖 Coffee Books AI - Admin Bot v2.1")
    safe_print("🤖 ═══════════════════════════════════════════")
    safe_print(f"👑 Super Admin ID: {SUPER_ADMIN_ID}")
    safe_print(f"📁 База данных: {ACCESS_DB}")
    safe_print("🤖 ═══════════════════════════════════════════\n")
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("admins", admins_command))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    safe_print("✅ Бот запущен и готов к работе!")
    safe_print("📱 Отправьте /start боту для начала\n")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()