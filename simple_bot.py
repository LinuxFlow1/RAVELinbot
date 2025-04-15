import os
import flask
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import telebot
from telebot.types import WebAppInfo, InlineKeyboardButton, InlineKeyboardMarkup
import threading
import time

# Конфигурация
BOT_TOKEN = '7227637125:AAFYcYk68mqvqJ7DJdFZgX9txtTvUpeWCIo'
WEBHOOK_HOST = 'https://linuxflow.pythonanywhere.com'  # Ваш точный домен

# Инициализация бота и Flask
bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__, template_folder='templates')
CORS(app)

# Хранилище данных (для примера, в реальном приложении нужна база данных)
rooms = {}
users = {}

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    # Создаем кнопку для создания новой комнаты
    create_room_button = InlineKeyboardButton(
        text="Создать комнату",
        callback_data="create_room"
    )
    
    # Создаем кнопку для диагностики
    diagnostic_button = InlineKeyboardButton(
        text="Диагностика",
        web_app=WebAppInfo(url=f"{WEBHOOK_HOST}/webapp/diagnostic")
    )
    
    keyboard = InlineKeyboardMarkup([
        [create_room_button],
        [diagnostic_button]
    ])
    
    bot.send_message(
        message.chat.id,
        "Привет! Выберите действие:",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data == "create_room")
def create_room_callback(call):
    try:
        # Генерируем уникальный ID для комнаты
        import uuid
        room_id = str(uuid.uuid4())[:8]
        
        # Создаем комнату
        rooms[room_id] = {
            "id": room_id,
            "title": f"Комната {room_id}",
            "creator_id": str(call.from_user.id),
            "viewers": [],
            "messages": [],
            "banned_users": []
        }
        
        # Создаем кнопку для входа в комнату
        join_button = InlineKeyboardButton(
            text="Войти в комнату",
            web_app=WebAppInfo(url=f"{WEBHOOK_HOST}/webapp/room/{room_id}?user_id={call.from_user.id}")
        )
        
        # Создаем кнопку для приглашения других пользователей
        share_button = InlineKeyboardButton(
            text="Пригласить друзей",
            switch_inline_query=f"join_{room_id}"
        )
        
        keyboard = InlineKeyboardMarkup([
            [join_button],
            [share_button]
        ])
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"Комната создана!\nID комнаты: {room_id}\n\nОтправьте команду /join {room_id} чтобы присоединиться.",
            reply_markup=keyboard
        )
    except Exception as e:
        bot.answer_callback_query(call.id, f"Ошибка: {str(e)}")

# Обработчик команды /join для присоединения к комнате
@bot.message_handler(commands=['join'])
def join_command(message):
    try:
        # Извлекаем ID комнаты из команды
        command_parts = message.text.split()
        if len(command_parts) != 2:
            bot.reply_to(message, "Использование: /join ROOM_ID")
            return
            
        room_id = command_parts[1]
        if room_id not in rooms:
            bot.reply_to(message, f"Комната {room_id} не найдена")
            return
        
        # Создаем кнопку для присоединения к комнате
        web_app_button = InlineKeyboardButton(
            text="Присоединиться к комнате",
            web_app=WebAppInfo(url=f"{WEBHOOK_HOST}/webapp/room/{room_id}?user_id={message.from_user.id}")
        )
        keyboard = InlineKeyboardMarkup([[web_app_button]])
        
        bot.send_message(
            message.chat.id,
            f"Комната: {rooms[room_id].get('title', 'Без названия')}\nНажмите кнопку чтобы присоединиться.",
            reply_markup=keyboard
        )
    except Exception as e:
        bot.reply_to(message, f"Произошла ошибка: {str(e)}")

# Обработчик для данных, отправленных из веб-приложения
@bot.message_handler(content_types=['web_app_data'])
def web_app_data(message):
    try:
        # Обработка данных от WebApp
        data = message.web_app_data.data
        bot.send_message(message.chat.id, f"Получены данные из WebApp: {data}")
    except Exception as e:
        bot.reply_to(message, f"Ошибка обработки данных: {str(e)}")

# Маршруты Flask для WebApp

@app.route('/webapp', methods=['GET'])
def webapp_index():
    user_id = request.args.get('user_id', '')
    return render_template('webapp/webapp_index.html', user_id=user_id, rooms=list(rooms.values()))

@app.route('/webapp/room/<room_id>', methods=['GET'])
def webapp_room(room_id):
    user_id = request.args.get('user_id', '')
    
    if room_id not in rooms:
        return jsonify({"error": "Комната не найдена"}), 404
        
    room = rooms[room_id]
    is_creator = user_id == room.get('creator_id')
    is_banned = user_id in room.get('banned_users', [])
    
    return render_template(
        'webapp/webapp_room.html',
        room=room,
        user_id=user_id,
        is_creator=is_creator,
        is_banned=is_banned,
        bot_username=bot.get_me().username
    )

# API маршруты для WebApp

@app.route('/webapp/create_room', methods=['POST'])
def create_room():
    try:
        data = request.json
        user_id = data.get('user_id')
        video_url = data.get('video_url')
        title = data.get('title', 'Новая комната')
        
        if not user_id or not video_url:
            return jsonify({"success": False, "error": "Не указан пользователь или URL видео"})
        
        # Генерируем уникальный ID для комнаты
        import uuid
        room_id = str(uuid.uuid4())[:8]
        
        # Создаем комнату
        rooms[room_id] = {
            "id": room_id,
            "title": title,
            "video_url": video_url,
            "creator_id": user_id,
            "viewers": [{"id": user_id, "name": "Создатель"}],
            "messages": [],
            "banned_users": []
        }
        
        return jsonify({
            "success": True,
            "room_id": room_id,
            "need_vpn": "youtube" in video_url.lower()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/webapp/join_room/<room_id>', methods=['GET'])
def join_room(room_id):
    try:
        user_id = request.args.get('user_id')
        
        if not user_id:
            return jsonify({"success": False, "error": "Не указан ID пользователя"})
        
        if room_id not in rooms:
            return jsonify({"success": False, "error": "Комната не найдена"})
        
        room = rooms[room_id]
        
        # Проверяем бан
        if user_id in room.get('banned_users', []):
            return jsonify({"success": True, "is_banned": True})
        
        # Добавляем пользователя в список зрителей, если его ещё нет
        viewer_exists = False
        for viewer in room['viewers']:
            if viewer['id'] == user_id:
                viewer_exists = True
                break
                
        if not viewer_exists:
            room['viewers'].append({
                "id": user_id,
                "name": f"Пользователь {user_id}"
            })
        
        return jsonify({
            "success": True,
            "need_vpn": "youtube" in room['video_url'].lower()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/webapp/send_message', methods=['POST'])
def send_message():
    try:
        data = request.json
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        message_text = data.get('message')
        
        if not room_id or not user_id or not message_text:
            return jsonify({"success": False, "error": "Неполные данные"})
        
        if room_id not in rooms:
            return jsonify({"success": False, "error": "Комната не найдена"})
        
        room = rooms[room_id]
        
        # Проверяем бан
        if user_id in room.get('banned_users', []):
            return jsonify({"success": False, "error": "Вы заблокированы в этой комнате"})
        
        # Находим имя пользователя
        user_name = "Пользователь"
        for viewer in room['viewers']:
            if viewer['id'] == user_id:
                user_name = viewer.get('name', 'Пользователь')
                break
        
        # Добавляем сообщение
        import time
        message = {
            "user_id": user_id,
            "user_name": user_name,
            "text": message_text,
            "timestamp": int(time.time())
        }
        
        room['messages'].append(message)
        
        # Ограничиваем историю сообщений
        if len(room['messages']) > 100:
            room['messages'] = room['messages'][-100:]
        
        return jsonify({"success": True, "message": message})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/webapp/get_messages', methods=['GET'])
def get_messages():
    try:
        room_id = request.args.get('room_id')
        after_timestamp = request.args.get('after', 0)
        
        if not room_id:
            return jsonify({"success": False, "error": "Не указан ID комнаты"})
        
        if room_id not in rooms:
            return jsonify({"success": False, "error": "Комната не найдена"})
        
        # Находим сообщения после указанного времени
        after_timestamp = int(after_timestamp)
        new_messages = []
        
        for message in rooms[room_id]['messages']:
            if message['timestamp'] > after_timestamp:
                new_messages.append(message)
        
        return jsonify({"success": True, "messages": new_messages})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/webapp/update_video', methods=['POST'])
def update_video():
    try:
        data = request.json
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        video_url = data.get('video_url')
        
        if not room_id or not user_id or not video_url:
            return jsonify({"success": False, "error": "Неполные данные"})
        
        if room_id not in rooms:
            return jsonify({"success": False, "error": "Комната не найдена"})
        
        room = rooms[room_id]
        
        # Проверяем, является ли пользователь создателем комнаты
        if user_id != room.get('creator_id'):
            return jsonify({"success": False, "error": "Только создатель может менять видео"})
        
        # Обновляем URL видео
        room['video_url'] = video_url
        
        return jsonify({
            "success": True,
            "need_vpn": "youtube" in video_url.lower()
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/webapp/sync_video', methods=['POST'])
def sync_video():
    try:
        data = request.json
        room_id = data.get('room_id')
        user_id = data.get('user_id')
        current_time = data.get('current_time', 0)
        
        if not room_id or not user_id:
            return jsonify({"success": False, "error": "Неполные данные"})
        
        if room_id not in rooms:
            return jsonify({"success": False, "error": "Комната не найдена"})
        
        room = rooms[room_id]
        
        # Сохраняем время для синхронизации
        room['sync_time'] = current_time
        room['sync_timestamp'] = int(time.time())
        room['sync_user_id'] = user_id
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/webapp/check_sync', methods=['GET'])
def check_sync():
    try:
        room_id = request.args.get('room_id')
        user_id = request.args.get('user_id')
        
        if not room_id or not user_id:
            return jsonify({"success": False, "error": "Неполные данные"})
        
        if room_id not in rooms:
            return jsonify({"success": False, "error": "Комната не найдена"})
        
        room = rooms[room_id]
        
        # Проверяем, нужна ли синхронизация
        need_sync = False
        sync_time = room.get('sync_time', 0)
        
        if 'sync_timestamp' in room and 'sync_user_id' in room:
            # Синхронизируемся, если запрос не от инициатора синхронизации
            # и прошло не более 10 секунд с момента синхронизации
            if room['sync_user_id'] != user_id and (int(time.time()) - room['sync_timestamp']) < 10:
                need_sync = True
        
        return jsonify({
            "success": True,
            "need_sync": need_sync,
            "time": sync_time
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/webapp/test', methods=['GET'])
def test_webapp():
    """Тестовый маршрут для проверки доступности API."""
    return "API доступен. Время сервера: " + time.strftime("%H:%M:%S")

# Маршрут для обслуживания статических файлов
@app.route('/static/<path:path>')
def serve_static(path):
    response = send_from_directory('static', path)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

@app.route('/webapp/diagnostic')
def diagnostic():
    """Страница диагностики"""
    return render_template('webapp/diagnostic.html')

@app.route('/_ah/start')
def start():
    """App Engine start handler"""
    return 'OK'

@app.route('/_ah/stop')
def stop():
    """App Engine stop handler"""
    return 'OK'

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """Установка вебхука для бота"""
    try:
        webhook_url = f"{WEBHOOK_HOST}/webhook"
        bot.remove_webhook()
        bot.set_webhook(url=webhook_url)
        return f"Webhook установлен на {webhook_url}"
    except Exception as e:
        return f"Ошибка установки webhook: {str(e)}"

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обработчик вебхуков от Telegram"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        return ''

def run_bot():
    """Функция для запуска бота в отдельном потоке"""
    bot.remove_webhook()
    bot.infinity_polling()

if __name__ == '__main__':
    # Запускаем Flask
    app.run(host='0.0.0.0', port=5000) 