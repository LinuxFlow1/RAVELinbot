import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

# Импортируем структуры данных из основного файла бота
from bot import Room, rooms, user_current_room, save_state

# Создаем Flask-приложение
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24).hex())

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Функция для форматирования времени в шаблонах
@app.template_filter('format_time')
def format_time(timestamp_str):
    if not timestamp_str:
        return ""
    try:
        dt = datetime.fromisoformat(timestamp_str)
        return dt.strftime("%H:%M:%S")
    except (ValueError, TypeError):
        return timestamp_str

# Главная страница
@app.route('/')
def index():
    return render_template('index.html', rooms=rooms.values())

# Создание комнаты
@app.route('/create_room', methods=['GET', 'POST'])
def create_room():
    if request.method == 'POST':
        video_url = request.form.get('video_url')
        title = request.form.get('title', "")
        
        if not video_url:
            flash('Пожалуйста, укажите ссылку на видео.')
            return redirect(url_for('create_room'))
        
        # Для веб-интерфейса используем временный ID пользователя
        user_id = request.remote_addr.replace('.', '')
        
        # Создаем комнату
        room = Room(int(user_id), video_url, title)
        rooms[room.id] = room
        user_current_room[int(user_id)] = room.id
        
        # Сохраняем состояние
        save_state()
        
        return redirect(url_for('view_room', room_id=room.id))
    
    return render_template('create_room.html')

# Просмотр комнаты
@app.route('/room/<room_id>')
def view_room(room_id):
    if room_id not in rooms:
        flash('Комната не найдена.')
        return redirect(url_for('index'))
    
    room = rooms[room_id]
    
    # Для веб-интерфейса используем временный ID пользователя
    user_id = int(request.remote_addr.replace('.', ''))
    
    # Проверяем, не заблокирован ли пользователь
    is_banned = user_id in room.banned_users
    
    # Если пользователь не заблокирован, добавляем его в список зрителей
    if not is_banned and user_id not in room.viewers:
        room.viewers.add(user_id)
        save_state()
    
    # Проверяем, является ли пользователь создателем комнаты
    is_creator = user_id == room.creator_id
    
    # Формируем ссылку для приглашения
    share_link = request.host_url.rstrip('/') + url_for('join_room', room_id=room_id)
    
    return render_template(
        'room.html',
        room=room,
        user_id=user_id,
        is_creator=is_creator,
        is_banned=is_banned,
        share_link=share_link
    )

# Присоединение к комнате
@app.route('/join/<room_id>')
def join_room(room_id):
    if room_id not in rooms:
        flash('Комната не найдена.')
        return redirect(url_for('index'))
    
    return redirect(url_for('view_room', room_id=room_id))

# API для отправки сообщений
@app.route('/send_message', methods=['POST'])
def send_message():
    data = request.json
    room_id = data.get('room_id')
    message_text = data.get('message')
    
    if not room_id or not message_text or room_id not in rooms:
        return jsonify({'success': False, 'error': 'Неверные параметры'})
    
    room = rooms[room_id]
    user_id = int(request.remote_addr.replace('.', ''))
    
    # Проверяем, не заблокирован ли пользователь
    if user_id in room.banned_users:
        return jsonify({'success': False, 'error': 'Вы заблокированы в этой комнате'})
    
    # Создаем сообщение
    message = {
        'user_id': user_id,
        'text': message_text,
        'timestamp': datetime.now().isoformat(),
        'user_name': f"Пользователь {user_id % 1000}"  # Для веб-интерфейса используем упрощенное имя
    }
    
    # Добавляем сообщение в комнату
    room.messages.append(message)
    save_state()
    
    return jsonify({'success': True, 'message': message})

# API для обновления видео
@app.route('/update_video', methods=['POST'])
def update_video():
    data = request.json
    room_id = data.get('room_id')
    video_url = data.get('video_url')
    
    if not room_id or not video_url or room_id not in rooms:
        return jsonify({'success': False, 'error': 'Неверные параметры'})
    
    room = rooms[room_id]
    user_id = int(request.remote_addr.replace('.', ''))
    
    # Проверяем, является ли пользователь создателем комнаты
    if user_id != room.creator_id:
        return jsonify({'success': False, 'error': 'Только создатель комнаты может менять видео'})
    
    # Обновляем видео
    room.video_url = video_url
    save_state()
    
    return jsonify({'success': True})

# API для разблокировки пользователя
@app.route('/unban_user', methods=['POST'])
def unban_user():
    data = request.json
    room_id = data.get('room_id')
    target_user_id = data.get('user_id')
    
    if not room_id or not target_user_id or room_id not in rooms:
        return jsonify({'success': False, 'error': 'Неверные параметры'})
    
    room = rooms[room_id]
    user_id = int(request.remote_addr.replace('.', ''))
    target_user_id = int(target_user_id)
    
    # Проверяем, является ли пользователь создателем комнаты
    if user_id != room.creator_id:
        return jsonify({'success': False, 'error': 'Только создатель комнаты может разблокировать пользователей'})
    
    # Разблокируем пользователя
    if target_user_id in room.banned_users:
        room.banned_users.discard(target_user_id)
        save_state()
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Пользователь не был заблокирован'})

# Запуск приложения
if __name__ == '__main__':
    # Загружаем существующие комнаты из файла состояния
    app.run(debug=True) 