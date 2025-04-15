import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_cors import CORS

# Импортируем структуры данных из основного файла бота
from bot import Room, rooms, user_current_room, save_state, load_state

# Создаем Flask-приложение для Telegram WebApp
app = Flask(__name__, static_folder='static', template_folder='templates/webapp')
CORS(app)  # Разрешаем кросс-доменные запросы для WebApp
app.secret_key = os.getenv("FLASK_SECRET_KEY", os.urandom(24).hex())

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Функция проверки, является ли ссылка YouTube-ссылкой
def is_youtube_link(url):
    youtube_domains = [
        'youtube.com', 
        'youtu.be', 
        'm.youtube.com', 
        'www.youtube.com', 
        'youtube-nocookie.com', 
        'www.youtube-nocookie.com'
    ]
    return any(domain in url for domain in youtube_domains)

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

# Главная страница WebApp
@app.route('/webapp')
def webapp_index():
    # Получаем данные от Telegram WebApp
    init_data = request.args.get('tgWebAppData', '')
    user_id = request.args.get('user_id', 0)
    
    if user_id:
        user_id = int(user_id)
    else:
        # Если ID пользователя не передан, используем временный
        user_id = int(request.remote_addr.replace('.', ''))
    
    # Сохраняем ID пользователя в сессии
    session['user_id'] = user_id
    
    return render_template('webapp_index.html', rooms=rooms.values(), user_id=user_id)

# Создание комнаты через WebApp
@app.route('/webapp/create_room', methods=['GET', 'POST'])
def webapp_create_room():
    if request.method == 'POST':
        # Получаем данные формы или JSON запроса
        if request.is_json:
            data = request.get_json()
            video_url = data.get('video_url', '')
            title = data.get('title', '')
            user_id = data.get('user_id', session.get('user_id', 0))
        else:
            video_url = request.form.get('video_url', '')
            title = request.form.get('title', '')
            user_id = request.form.get('user_id', session.get('user_id', 0))
        
        if not video_url:
            if request.is_json:
                return jsonify({'success': False, 'error': 'Не указана ссылка на видео'})
            else:
                flash('Пожалуйста, укажите ссылку на видео.')
                return redirect(url_for('webapp_create_room'))
        
        # Преобразуем к int, если user_id - строка
        if isinstance(user_id, str) and user_id.isdigit():
            user_id = int(user_id)
        
        # Создаем комнату
        room = Room(user_id, video_url, title)
        rooms[room.id] = room
        user_current_room[user_id] = room.id
        
        # Сохраняем состояние
        save_state()
        
        # Проверяем, нужно ли предупреждение о YouTube
        need_vpn = is_youtube_link(video_url)
        
        if request.is_json:
            return jsonify({
                'success': True, 
                'room_id': room.id, 
                'need_vpn': need_vpn
            })
        else:
            return redirect(url_for('webapp_room', room_id=room.id))
    
    return render_template('webapp_create_room.html')

# Просмотр комнаты через WebApp
@app.route('/webapp/room/<room_id>')
def webapp_room(room_id):
    if room_id not in rooms:
        if request.is_json:
            return jsonify({'success': False, 'error': 'Комната не найдена'})
        else:
            flash('Комната не найдена.')
            return redirect(url_for('webapp_index'))
    
    room = rooms[room_id]
    
    # Получаем ID пользователя из сессии или параметров
    user_id = request.args.get('user_id', session.get('user_id', 0))
    if isinstance(user_id, str) and user_id.isdigit():
        user_id = int(user_id)
    
    # Проверяем, не заблокирован ли пользователь
    is_banned = user_id in room.banned_users
    
    # Если пользователь не заблокирован, добавляем его в список зрителей
    if not is_banned and user_id not in room.viewers:
        room.viewers.add(user_id)
        save_state()
    
    # Проверяем, является ли пользователь создателем комнаты
    is_creator = user_id == room.creator_id
    
    # Проверяем, нужно ли предупреждение о YouTube
    need_vpn = is_youtube_link(room.video_url)
    
    # Формируем ссылку для приглашения
    share_link = f"https://t.me/{os.getenv('BOT_USERNAME', 'your_bot_username')}?start=join_{room_id}"
    
    return render_template(
        'webapp_room.html',
        room=room,
        user_id=user_id,
        is_creator=is_creator,
        is_banned=is_banned,
        share_link=share_link,
        need_vpn=need_vpn
    )

# API для отправки сообщений через WebApp
@app.route('/webapp/send_message', methods=['POST'])
def webapp_send_message():
    data = request.get_json()
    room_id = data.get('room_id')
    message_text = data.get('message')
    user_id = data.get('user_id', session.get('user_id', 0))
    
    if isinstance(user_id, str) and user_id.isdigit():
        user_id = int(user_id)
    
    if not room_id or not message_text or room_id not in rooms:
        return jsonify({'success': False, 'error': 'Неверные параметры'})
    
    room = rooms[room_id]
    
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

# API для обновления видео через WebApp
@app.route('/webapp/update_video', methods=['POST'])
def webapp_update_video():
    data = request.get_json()
    room_id = data.get('room_id')
    video_url = data.get('video_url')
    user_id = data.get('user_id', session.get('user_id', 0))
    
    if isinstance(user_id, str) and user_id.isdigit():
        user_id = int(user_id)
    
    if not room_id or not video_url or room_id not in rooms:
        return jsonify({'success': False, 'error': 'Неверные параметры'})
    
    room = rooms[room_id]
    
    # Проверяем, является ли пользователь создателем комнаты
    if user_id != room.creator_id:
        return jsonify({'success': False, 'error': 'Только создатель комнаты может менять видео'})
    
    # Проверяем, нужно ли предупреждение о YouTube
    need_vpn = is_youtube_link(video_url)
    
    # Обновляем видео
    room.video_url = video_url
    save_state()
    
    return jsonify({'success': True, 'need_vpn': need_vpn})

# API для получения информации о комнате
@app.route('/webapp/room_info/<room_id>')
def webapp_room_info(room_id):
    if room_id not in rooms:
        return jsonify({'success': False, 'error': 'Комната не найдена'})
    
    room = rooms[room_id]
    
    # Получаем ID пользователя из сессии или параметров
    user_id = request.args.get('user_id', session.get('user_id', 0))
    if isinstance(user_id, str) and user_id.isdigit():
        user_id = int(user_id)
    
    # Проверяем, не заблокирован ли пользователь
    is_banned = user_id in room.banned_users
    
    # Проверяем, является ли пользователь создателем комнаты
    is_creator = user_id == room.creator_id
    
    # Проверяем, нужно ли предупреждение о YouTube
    need_vpn = is_youtube_link(room.video_url)
    
    return jsonify({
        'success': True,
        'room': {
            'id': room.id,
            'title': room.title,
            'video_url': room.video_url,
            'creator_id': room.creator_id,
            'viewers_count': len(room.viewers),
            'messages_count': len(room.messages),
            'need_vpn': need_vpn
        },
        'user': {
            'id': user_id,
            'is_creator': is_creator,
            'is_banned': is_banned
        }
    })

# API для присоединения к комнате
@app.route('/webapp/join_room/<room_id>')
def webapp_join_room(room_id):
    if room_id not in rooms:
        return jsonify({'success': False, 'error': 'Комната не найдена'})
    
    room = rooms[room_id]
    
    # Получаем ID пользователя из сессии или параметров
    user_id = request.args.get('user_id', session.get('user_id', 0))
    if isinstance(user_id, str) and user_id.isdigit():
        user_id = int(user_id)
    
    # Проверяем, не заблокирован ли пользователь
    if user_id in room.banned_users:
        return jsonify({'success': False, 'error': 'Вы заблокированы в этой комнате'})
    
    # Добавляем пользователя в комнату
    room.viewers.add(user_id)
    user_current_room[user_id] = room_id
    
    # Сохраняем состояние
    save_state()
    
    # Проверяем, нужно ли предупреждение о YouTube
    need_vpn = is_youtube_link(room.video_url)
    
    # Если запрос через API, возвращаем JSON
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or '/api/' in request.path:
        return jsonify({
            'success': True, 
            'room_id': room_id,
            'need_vpn': need_vpn
        })
    
    # В противном случае перенаправляем на страницу комнаты
    return redirect(url_for('webapp_room', room_id=room_id))

# Функция синхронизации видео (для будущих улучшений)
@app.route('/webapp/sync_video', methods=['POST'])
def webapp_sync_video():
    data = request.get_json()
    room_id = data.get('room_id')
    current_time = data.get('current_time', 0)
    is_playing = data.get('is_playing', True)
    user_id = data.get('user_id', session.get('user_id', 0))
    
    if isinstance(user_id, str) and user_id.isdigit():
        user_id = int(user_id)
    
    if not room_id or room_id not in rooms:
        return jsonify({'success': False, 'error': 'Комната не найдена'})
    
    room = rooms[room_id]
    
    # Добавляем информацию о синхронизации в комнату
    if not hasattr(room, 'sync_info'):
        room.sync_info = {}
    
    room.sync_info['last_update'] = datetime.now().isoformat()
    room.sync_info['current_time'] = current_time
    room.sync_info['is_playing'] = is_playing
    room.sync_info['updated_by'] = user_id
    
    save_state()
    
    return jsonify({'success': True})

# Получение статуса синхронизации видео
@app.route('/webapp/sync_status/<room_id>')
def webapp_sync_status(room_id):
    if room_id not in rooms:
        return jsonify({'success': False, 'error': 'Комната не найдена'})
    
    room = rooms[room_id]
    
    if not hasattr(room, 'sync_info'):
        return jsonify({
            'success': True,
            'sync_info': {
                'current_time': 0,
                'is_playing': True,
                'last_update': datetime.now().isoformat(),
                'updated_by': room.creator_id
            }
        })
    
    return jsonify({
        'success': True,
        'sync_info': room.sync_info
    })

# Запуск приложения
if __name__ == '__main__':
    # Загружаем существующие комнаты из файла состояния
    load_state()
    app.run(debug=True, host='0.0.0.0', port=5001) 