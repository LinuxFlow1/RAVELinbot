import json
from datetime import datetime
from typing import Dict, Optional

from telegram import Update
from telegram.ext import ContextTypes

# Импортируем структуры данных из основного файла
from bot import rooms, user_current_room, save_state, get_room_keyboard

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает текстовые сообщения, отправленные в бота."""
    user_id = update.effective_user.id
    text = update.message.text
    
    # Проверяем, находится ли пользователь в комнате
    if user_id not in user_current_room:
        await update.message.reply_text(
            "❌ Вы не находитесь в комнате. Используйте /join [id_комнаты], чтобы войти в комнату."
        )
        return
    
    room_id = user_current_room[user_id]
    if room_id not in rooms:
        # Комната была удалена, сбрасываем состояние пользователя
        del user_current_room[user_id]
        save_state()
        await update.message.reply_text(
            "❌ Комната, в которой вы находились, больше не существует."
        )
        return
    
    room = rooms[room_id]
    
    # Проверяем, не заблокирован ли пользователь
    if user_id in room.banned_users:
        await update.message.reply_text(
            "⛔ Вы заблокированы в этой комнате и не можете отправлять сообщения."
        )
        return
    
    # Сохраняем сообщение
    message = {
        "user_id": user_id,
        "text": text,
        "timestamp": datetime.now().isoformat(),
        "user_name": update.effective_user.first_name
    }
    room.messages.append(message)
    save_state()
    
    # Отправляем сообщение всем участникам комнаты (в будущей реализации через webhook)
    # В текущей реализации просто подтверждаем отправку
    await update.message.reply_text(
        f"✅ Сообщение отправлено в комнату {room.title}.",
        reply_markup=get_room_keyboard(room_id, user_id == room.creator_id)
    )

async def handle_command_with_args(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает команды с аргументами в формате /command arg1 arg2..."""
    message = update.message.text
    user_id = update.effective_user.id
    
    # Обработка команды /start с аргументами (для глубоких ссылок)
    if message.startswith("/start join_"):
        # Извлекаем ID комнаты из команды
        parts = message.split("_")
        if len(parts) > 1:
            room_id = parts[1]
            # Имитируем команду /join
            context.args = [room_id]
            from bot import join_room_command
            await join_room_command(update, context)
    
    # Команда для модерации - бан пользователя (только для создателя комнаты)
    elif message.startswith("/ban"):
        if len(context.args) < 1:
            await update.message.reply_text(
                "❌ Укажите ID пользователя для блокировки: /ban [user_id]"
            )
            return
        
        target_user_id = int(context.args[0])
        
        # Проверяем, что пользователь находится в комнате
        if user_id not in user_current_room:
            await update.message.reply_text(
                "❌ Вы не находитесь в комнате."
            )
            return
        
        room_id = user_current_room[user_id]
        room = rooms.get(room_id)
        
        if not room:
            await update.message.reply_text(
                "❌ Комната не найдена."
            )
            return
        
        # Проверяем, что пользователь является создателем комнаты
        if user_id != room.creator_id:
            await update.message.reply_text(
                "⛔ Только создатель комнаты может блокировать пользователей."
            )
            return
        
        # Проверяем, что целевой пользователь находится в комнате
        if target_user_id not in room.viewers:
            await update.message.reply_text(
                "❌ Указанный пользователь не находится в комнате."
            )
            return
        
        # Блокируем пользователя
        room.banned_users.add(target_user_id)
        room.viewers.discard(target_user_id)
        if target_user_id in user_current_room and user_current_room[target_user_id] == room_id:
            del user_current_room[target_user_id]
        
        save_state()
        
        await update.message.reply_text(
            f"⛔ Пользователь с ID {target_user_id} заблокирован в комнате."
        )
    
    # Команда для разблокировки пользователя
    elif message.startswith("/unban"):
        if len(context.args) < 1:
            await update.message.reply_text(
                "❌ Укажите ID пользователя для разблокировки: /unban [user_id]"
            )
            return
        
        target_user_id = int(context.args[0])
        
        # Проверяем, что пользователь находится в комнате
        if user_id not in user_current_room:
            await update.message.reply_text(
                "❌ Вы не находитесь в комнате."
            )
            return
        
        room_id = user_current_room[user_id]
        room = rooms.get(room_id)
        
        if not room:
            await update.message.reply_text(
                "❌ Комната не найдена."
            )
            return
        
        # Проверяем, что пользователь является создателем комнаты
        if user_id != room.creator_id:
            await update.message.reply_text(
                "⛔ Только создатель комнаты может разблокировать пользователей."
            )
            return
        
        # Разблокируем пользователя, если он был заблокирован
        if target_user_id in room.banned_users:
            room.banned_users.discard(target_user_id)
            save_state()
            await update.message.reply_text(
                f"✅ Пользователь с ID {target_user_id} разблокирован в комнате."
            )
        else:
            await update.message.reply_text(
                "❌ Указанный пользователь не был заблокирован в этой комнате."
            )

# Функция для получения сообщений в комнате
def get_room_messages(room_id: str, limit: int = 20) -> list:
    """Возвращает последние сообщения в комнате."""
    if room_id not in rooms:
        return []
    
    room = rooms[room_id]
    messages = room.messages[-limit:] if limit > 0 else room.messages
    
    return messages 