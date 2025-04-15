import os
import json
import logging
import uuid
from typing import Dict, List, Optional, Set

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, 
    WebAppInfo, User as TelegramUser, Message
)
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Классы данных
class Room:
    def __init__(self, creator_id: int, video_url: str, title: str = ""):
        self.id = str(uuid.uuid4())
        self.creator_id = creator_id
        self.video_url = video_url
        self.title = title or f"Комната {self.id[:8]}"
        self.viewers: Set[int] = {creator_id}  # локеры (зрители)
        self.banned_users: Set[int] = set()
        self.messages: List[Dict] = []
    
    def to_dict(self):
        return {
            "id": self.id,
            "creator_id": self.creator_id,
            "video_url": self.video_url,
            "title": self.title,
            "viewers": list(self.viewers),
            "banned_users": list(self.banned_users),
            "messages": self.messages
        }
    
    @classmethod
    def from_dict(cls, data):
        room = cls(data["creator_id"], data["video_url"], data["title"])
        room.id = data["id"]
        room.viewers = set(data["viewers"])
        room.banned_users = set(data["banned_users"])
        room.messages = data["messages"]
        return room

# Глобальное хранилище комнат
rooms: Dict[str, Room] = {}
user_current_room: Dict[int, str] = {}  # user_id -> room_id

# Сохранение и загрузка состояния
def save_state():
    state = {
        "rooms": {room_id: room.to_dict() for room_id, room in rooms.items()},
        "user_current_room": user_current_room
    }
    with open("state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def load_state():
    global rooms, user_current_room
    try:
        with open("state.json", "r", encoding="utf-8") as f:
            state = json.load(f)
            rooms = {room_id: Room.from_dict(room_data) for room_id, room_data in state["rooms"].items()}
            user_current_room = state["user_current_room"]
    except (FileNotFoundError, json.JSONDecodeError):
        rooms = {}
        user_current_room = {}

# Команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Отправляет приветственное сообщение при команде /start."""
    user = update.effective_user
    
    # Проверяем, есть ли параметры у команды start (для глубоких ссылок)
    if context.args and context.args[0].startswith("join_"):
        # Импортируем здесь, чтобы избежать циклического импорта
        from message_handlers import handle_command_with_args
        await handle_command_with_args(update, context)
        return
    
    await update.message.reply_html(
        f"👋 Привет, {user.mention_html()}!\n\n"
        f"Это бот для совместного просмотра видео в стиле Rave.\n\n"
        f"Команды:\n"
        f"/create [ссылка] [название] - создать новую комнату\n"
        f"/join [id_комнаты] - присоединиться к комнате\n"
        f"/rooms - список доступных комнат\n"
        f"/help - показать помощь",
        reply_markup=get_main_keyboard()
    )

def get_main_keyboard():
    """Создаёт основную клавиатуру с кнопками действий."""
    keyboard = [
        [
            InlineKeyboardButton("🎥 Создать комнату", callback_data="create_room"),
            InlineKeyboardButton("🚪 Присоединиться", callback_data="join_room")
        ],
        [
            InlineKeyboardButton("🏠 Все комнаты", callback_data="list_rooms"),
            InlineKeyboardButton("❓ Помощь", callback_data="help")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_room_keyboard(room_id: str, is_creator: bool):
    """Создаёт клавиатуру комнаты."""
    keyboard = [
        [
            InlineKeyboardButton("💬 Чат", callback_data=f"chat_{room_id}"),
            InlineKeyboardButton("👥 Участники", callback_data=f"viewers_{room_id}")
        ],
        [
            InlineKeyboardButton("🔗 Поделиться", callback_data=f"share_{room_id}"),
            InlineKeyboardButton("🚪 Выйти", callback_data="leave_room")
        ]
    ]
    
    # Дополнительные кнопки для создателя комнаты
    if is_creator:
        keyboard.append([
            InlineKeyboardButton("🔄 Сменить видео", callback_data=f"change_video_{room_id}"),
            InlineKeyboardButton("⚙️ Настройки", callback_data=f"settings_{room_id}")
        ])
    
    return InlineKeyboardMarkup(keyboard)

async def create_room_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Создаёт новую комнату для просмотра."""
    user_id = update.effective_user.id
    args = context.args
    
    if not args or len(args) < 1:
        await update.message.reply_text(
            "📝 Пожалуйста, укажите ссылку на видео:\n"
            "/create [ссылка] [название - опционально]"
        )
        return
    
    video_url = args[0]
    title = " ".join(args[1:]) if len(args) > 1 else ""
    
    room = Room(user_id, video_url, title)
    rooms[room.id] = room
    user_current_room[user_id] = room.id
    
    # Сохраняем состояние
    save_state()
    
    await update.message.reply_text(
        f"🎬 Комната создана!\n\n"
        f"📝 Название: {room.title}\n"
        f"🔗 Видео: {video_url}\n"
        f"🆔 ID комнаты: `{room.id}`\n\n"
        f"👥 Участников: 1\n\n"
        f"Поделитесь этой ссылкой, чтобы пригласить друзей:\n"
        f"https://t.me/{context.bot.username}?start=join_{room.id}",
        parse_mode="Markdown",
        reply_markup=get_room_keyboard(room.id, True)
    )

async def join_room_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Присоединяется к существующей комнате."""
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "🔑 Пожалуйста, укажите ID комнаты:\n"
            "/join [id_комнаты]"
        )
        return
    
    room_id = args[0]
    
    if room_id not in rooms:
        await update.message.reply_text("❌ Комната не найдена. Проверьте ID и попробуйте снова.")
        return
    
    room = rooms[room_id]
    
    if user_id in room.banned_users:
        await update.message.reply_text("⛔ Вы были заблокированы в этой комнате.")
        return
    
    # Добавляем пользователя в комнату
    room.viewers.add(user_id)
    user_current_room[user_id] = room_id
    
    # Сохраняем состояние
    save_state()
    
    is_creator = user_id == room.creator_id
    
    await update.message.reply_text(
        f"✅ Вы присоединились к комнате!\n\n"
        f"📝 Название: {room.title}\n"
        f"🔗 Видео: {room.video_url}\n"
        f"👥 Участников: {len(room.viewers)}\n",
        reply_markup=get_room_keyboard(room_id, is_creator)
    )

async def list_rooms_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список всех доступных комнат."""
    if not rooms:
        await update.message.reply_text(
            "🏠 Нет активных комнат. Создайте новую с помощью /create [ссылка] [название]",
            reply_markup=get_main_keyboard()
        )
        return
    
    rooms_text = "🏠 Доступные комнаты:\n\n"
    
    for room_id, room in rooms.items():
        rooms_text += f"📝 {room.title}\n"
        rooms_text += f"👥 Участников: {len(room.viewers)}\n"
        rooms_text += f"🆔 ID: `{room_id}`\n\n"
    
    await update.message.reply_text(
        rooms_text,
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает справку по командам бота."""
    await update.message.reply_text(
        "🌟 *Rave Bot - совместный просмотр видео* 🌟\n\n"
        "Команды:\n"
        "/start - начать работу с ботом\n"
        "/create [ссылка] [название] - создать новую комнату\n"
        "/join [id_комнаты] - присоединиться к комнате\n"
        "/rooms - список доступных комнат\n"
        "/help - показать эту справку\n\n"
        "Находясь в комнате, вы можете:\n"
        "- Общаться в чате с другими участниками\n"
        "- Видеть, кто присоединился к комнате\n"
        "- Поделиться комнатой с друзьями\n\n"
        "Создатель комнаты может:\n"
        "- Менять видео для просмотра\n"
        "- Настраивать параметры комнаты\n"
        "- Блокировать пользователей с помощью /ban [user_id]\n"
        "- Разблокировать пользователей с помощью /unban [user_id]",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия на кнопки."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "create_room":
        await query.message.reply_text(
            "📝 Пожалуйста, отправьте ссылку на видео и название комнаты в формате:\n"
            "/create [ссылка] [название - опционально]"
        )
    
    elif data == "join_room":
        await query.message.reply_text(
            "🔑 Пожалуйста, отправьте ID комнаты в формате:\n"
            "/join [id_комнаты]"
        )
    
    elif data == "list_rooms":
        await list_rooms_command(update, context)
    
    elif data == "help":
        await help_command(update, context)
    
    elif data == "leave_room":
        if user_id not in user_current_room:
            await query.message.reply_text("❌ Вы не находитесь в комнате.")
            return
        
        room_id = user_current_room[user_id]
        room = rooms[room_id]
        
        # Удаляем пользователя из комнаты
        room.viewers.discard(user_id)
        del user_current_room[user_id]
        
        # Если комната пуста, удаляем её
        if not room.viewers:
            del rooms[room_id]
        
        # Сохраняем состояние
        save_state()
        
        await query.message.reply_text(
            "👋 Вы вышли из комнаты.",
            reply_markup=get_main_keyboard()
        )
    
    elif data.startswith("chat_"):
        room_id = data.split("_")[1]
        if room_id not in rooms:
            await query.message.reply_text("❌ Комната не найдена.")
            return
        
        room = rooms[room_id]
        
        if user_id in room.banned_users:
            await query.message.reply_text("⛔ Вы заблокированы в этой комнате и не можете писать в чат.")
            return
        
        # Получаем последние сообщения
        from message_handlers import get_room_messages
        messages = get_room_messages(room_id, 10)
        
        chat_text = f"💬 Чат комнаты {room.title}\n\n"
        
        if not messages:
            chat_text += "В чате пока нет сообщений. Напишите первое!\n\n"
        else:
            for msg in messages:
                chat_text += f"[{msg['user_name']}]: {msg['text']}\n"
            chat_text += "\n"
        
        chat_text += "Отправьте сообщение, чтобы добавить его в чат."
        
        await query.message.reply_text(chat_text)
    
    elif data.startswith("viewers_"):
        room_id = data.split("_")[1]
        if room_id not in rooms:
            await query.message.reply_text("❌ Комната не найдена.")
            return
        
        room = rooms[room_id]
        viewers_text = f"👥 Участники комнаты {room.title}:\n\n"
        
        for viewer_id in room.viewers:
            try:
                user = await context.bot.get_chat(viewer_id)
                name = user.first_name
                if user.last_name:
                    name += f" {user.last_name}"
                if viewer_id == room.creator_id:
                    name += " 👑"
                viewers_text += f"- {name}\n"
            except:
                viewers_text += f"- Пользователь {viewer_id}\n"
        
        await query.message.reply_text(viewers_text)
    
    elif data.startswith("share_"):
        room_id = data.split("_")[1]
        if room_id not in rooms:
            await query.message.reply_text("❌ Комната не найдена.")
            return
        
        room = rooms[room_id]
        
        await query.message.reply_text(
            f"🔗 Поделитесь этой ссылкой, чтобы пригласить друзей в комнату {room.title}:\n\n"
            f"https://t.me/{context.bot.username}?start=join_{room_id}\n\n"
            f"Или отправьте им ID комнаты: `{room_id}`",
            parse_mode="Markdown"
        )
    
    elif data.startswith("change_video_"):
        room_id = data.split("_")[2]
        if room_id not in rooms:
            await query.message.reply_text("❌ Комната не найдена.")
            return
        
        room = rooms[room_id]
        
        if user_id != room.creator_id:
            await query.message.reply_text("⛔ Только создатель комнаты может менять видео.")
            return
        
        await query.message.reply_text(
            "🔄 Отправьте новую ссылку на видео в формате:\n"
            "/change_video [ссылка]"
        )
    
    elif data.startswith("settings_"):
        room_id = data.split("_")[1]
        if room_id not in rooms:
            await query.message.reply_text("❌ Комната не найдена.")
            return
        
        room = rooms[room_id]
        
        if user_id != room.creator_id:
            await query.message.reply_text("⛔ Только создатель комнаты может изменять настройки.")
            return
        
        settings_keyboard = [
            [
                InlineKeyboardButton("🔒 Забанить пользователя", callback_data=f"ban_user_{room_id}"),
                InlineKeyboardButton("🔓 Разбанить пользователя", callback_data=f"unban_user_{room_id}")
            ],
            [
                InlineKeyboardButton("🗑️ Удалить комнату", callback_data=f"delete_room_{room_id}"),
                InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_room_{room_id}")
            ]
        ]
        
        await query.message.reply_text(
            f"⚙️ Настройки комнаты {room.title}\n\n"
            f"Выберите действие:",
            reply_markup=InlineKeyboardMarkup(settings_keyboard)
        )
    
    elif data.startswith("ban_user_"):
        room_id = data.split("_")[2]
        if room_id not in rooms:
            await query.message.reply_text("❌ Комната не найдена.")
            return
        
        room = rooms[room_id]
        
        if user_id != room.creator_id:
            await query.message.reply_text("⛔ Только создатель комнаты может блокировать пользователей.")
            return
        
        await query.message.reply_text(
            "🔒 Отправьте команду для блокировки пользователя в формате:\n"
            "/ban [user_id]"
        )
    
    elif data.startswith("unban_user_"):
        room_id = data.split("_")[2]
        if room_id not in rooms:
            await query.message.reply_text("❌ Комната не найдена.")
            return
        
        room = rooms[room_id]
        
        if user_id != room.creator_id:
            await query.message.reply_text("⛔ Только создатель комнаты может разблокировать пользователей.")
            return
        
        if not room.banned_users:
            await query.message.reply_text("✅ В комнате нет заблокированных пользователей.")
            return
        
        banned_text = "🔓 Заблокированные пользователи:\n\n"
        for banned_id in room.banned_users:
            banned_text += f"- ID: {banned_id}\n"
        
        banned_text += "\nОтправьте команду для разблокировки пользователя в формате:\n/unban [user_id]"
        
        await query.message.reply_text(banned_text)
    
    elif data.startswith("delete_room_"):
        room_id = data.split("_")[2]
        if room_id not in rooms:
            await query.message.reply_text("❌ Комната не найдена.")
            return
        
        room = rooms[room_id]
        
        if user_id != room.creator_id:
            await query.message.reply_text("⛔ Только создатель комнаты может удалить комнату.")
            return
        
        # Удаляем комнату и очищаем записи пользователей
        for viewer_id in list(room.viewers):
            if viewer_id in user_current_room and user_current_room[viewer_id] == room_id:
                del user_current_room[viewer_id]
        
        del rooms[room_id]
        save_state()
        
        await query.message.reply_text(
            "🗑️ Комната успешно удалена.",
            reply_markup=get_main_keyboard()
        )
    
    elif data.startswith("back_to_room_"):
        room_id = data.split("_")[3]
        if room_id not in rooms:
            await query.message.reply_text("❌ Комната не найдена.")
            return
        
        room = rooms[room_id]
        is_creator = user_id == room.creator_id
        
        await query.message.reply_text(
            f"🔙 Вернулись в комнату {room.title}",
            reply_markup=get_room_keyboard(room_id, is_creator)
        )

# Обработчик команды изменения видео
async def change_video_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Изменяет видео в комнате."""
    user_id = update.effective_user.id
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "❌ Пожалуйста, укажите ссылку на новое видео:\n"
            "/change_video [ссылка]"
        )
        return
    
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
            "⛔ Только создатель комнаты может менять видео."
        )
        return
    
    # Меняем видео
    old_video_url = room.video_url
    room.video_url = args[0]
    save_state()
    
    await update.message.reply_text(
        f"✅ Видео успешно изменено!\n\n"
        f"Старое видео: {old_video_url}\n"
        f"Новое видео: {room.video_url}",
        reply_markup=get_room_keyboard(room_id, True)
    )

# Основная функция
def main() -> None:
    """Запускает бота."""
    # Загружаем сохраненное состояние
    load_state()
    
    # Создаем приложение и передаем ему токен бота
    application = Application.builder().token(TOKEN).build()
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("create", create_room_command))
    application.add_handler(CommandHandler("join", join_room_command))
    application.add_handler(CommandHandler("rooms", list_rooms_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("change_video", change_video_command))
    application.add_handler(CommandHandler("ban", lambda update, context: handle_command_with_args(update, context)))
    application.add_handler(CommandHandler("unban", lambda update, context: handle_command_with_args(update, context)))
    
    # Импортируем обработчик текстовых сообщений
    from message_handlers import handle_text_message, handle_command_with_args
    
    # Обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    # Обработчик кнопок
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем бота
    application.run_polling()

if __name__ == "__main__":
    main() 