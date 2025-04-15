// Глобальные переменные
let player = null;
let videoType = null;
let playerReady = false;
let messageInterval = null;

// Получение данных из data-атрибутов безопасным способом
function getPageData() {
    const body = document.body;
    return {
        roomId: body.dataset.roomId || '',
        roomTitle: body.dataset.roomTitle || 'Комната',
        isCreator: body.dataset.isCreator === 'true',
        isBanned: body.dataset.isBanned === 'true',
        userId: body.dataset.userId || '',
        botUsername: body.dataset.botUsername || '',
    };
}

// Инициализация Telegram WebApp
function initTelegramApp() {
    if (window.Telegram && window.Telegram.WebApp) {
        try {
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.MainButton.hide();
            
            // Настройка цветов темы
            const colorScheme = window.Telegram.WebApp.colorScheme || 'light';
            document.body.setAttribute('data-theme', colorScheme);
            
            console.log('Telegram WebApp инициализирован');
            return true;
        } catch (e) {
            console.error('Ошибка при инициализации Telegram WebApp:', e);
        }
    } else {
        console.warn('Telegram WebApp не обнаружен, работаем в автономном режиме');
    }
    return false;
}

// Инициализация видеоплеера
function initVideoPlayer() {
    const videoContainer = document.getElementById('video-container');
    
    if (!videoContainer) {
        console.error('Контейнер для видео не найден');
        return;
    }
    
    const videoUrl = videoContainer.dataset.videoUrl || '';
    
    if (!videoUrl) {
        console.warn('URL видео отсутствует');
        videoContainer.innerHTML = '<div class="video-error">Видео не найдено</div>';
        return;
    }
    
    console.log('Инициализация видеоплеера с URL:', videoUrl);
    
    // Определение типа видео
    if (videoUrl.includes('youtube.com') || videoUrl.includes('youtu.be')) {
        videoType = 'youtube';
        initYouTubePlayer(videoUrl, videoContainer);
    } else if (videoUrl.includes('vimeo.com')) {
        videoType = 'vimeo';
        initVimeoPlayer(videoUrl, videoContainer);
    } else {
        videoType = 'unknown';
        videoContainer.innerHTML = '<div class="video-error">Неподдерживаемый формат видео</div>';
    }
}

// Инициализация YouTube плеера
function initYouTubePlayer(url, container) {
    // Получаем ID видео из URL
    let videoId = '';
    
    if (url.includes('v=')) {
        videoId = url.split('v=')[1].split('&')[0];
    } else if (url.includes('youtu.be/')) {
        videoId = url.split('youtu.be/')[1].split('?')[0];
    }
    
    if (!videoId) {
        container.innerHTML = '<div class="video-error">Неверная ссылка на YouTube видео</div>';
        return;
    }
    
    // Создаем iframe для YouTube плеера
    const iframe = document.createElement('iframe');
    iframe.src = `https://www.youtube.com/embed/${videoId}?enablejsapi=1&origin=${window.location.origin}`;
    iframe.id = 'youtube-player';
    iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture';
    iframe.allowFullscreen = true;
    
    container.innerHTML = '';
    container.appendChild(iframe);
    
    // Инициализация YouTube API
    window.onYouTubeIframeAPIReady = function() {
        player = new YT.Player('youtube-player', {
            events: {
                'onReady': onPlayerReady,
                'onStateChange': onPlayerStateChange
            }
        });
    };
    
    // Загрузка YouTube API
    if (!window.YT) {
        const tag = document.createElement('script');
        tag.src = 'https://www.youtube.com/iframe_api';
        const firstScriptTag = document.getElementsByTagName('script')[0];
        firstScriptTag.parentNode.insertBefore(tag, firstScriptTag);
    } else if (window.YT.Player) {
        window.onYouTubeIframeAPIReady();
    }
}

// Обработчики событий YouTube плеера
function onPlayerReady(event) {
    console.log('Плеер YouTube готов');
    playerReady = true;
    
    // Настройка кнопки синхронизации
    setupVideoSync();
}

function onPlayerStateChange(event) {
    // Можно добавить логику для отслеживания состояния видео
    console.log('Состояние плеера изменилось:', event.data);
}

// Настройка синхронизации видео
function setupVideoSync() {
    const syncButton = document.getElementById('sync-btn');
    
    if (!syncButton) {
        console.error('Кнопка синхронизации не найдена');
        return;
    }
    
    syncButton.addEventListener('click', function() {
        if (!player || !playerReady) {
            showToast('Плеер еще не готов', true);
            return;
        }
        
        try {
            // Получаем текущее время видео
            let currentTime = 0;
            
            if (videoType === 'youtube' && player) {
                try {
                    currentTime = player.getCurrentTime();
                } catch (e) {
                    console.error('Ошибка получения времени YouTube:', e);
                }
            }
            
            const pageData = getPageData();
            
            // Отправляем запрос на синхронизацию
            fetch('/webapp/sync_video', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    room_id: pageData.roomId,
                    current_time: currentTime,
                    user_id: pageData.userId
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showToast('Видео синхронизировано');
                } else {
                    showToast(data.error || 'Ошибка синхронизации', true);
                }
            })
            .catch(e => {
                console.error('Ошибка запроса синхронизации:', e);
                showToast('Ошибка при синхронизации', true);
            });
        } catch (e) {
            console.error('Ошибка при синхронизации видео:', e);
            showToast('Ошибка при синхронизации', true);
        }
    });
}

// Получение текущего времени видео
function getCurrentVideoTime() {
    if (!player || !playerReady) return 0;
    
    try {
        if (videoType === 'youtube') {
            return player.getCurrentTime() || 0;
        }
    } catch (e) {
        console.error('Ошибка получения времени видео:', e);
    }
    
    return 0;
}

// Установка времени видео
function setVideoTime(seconds) {
    if (!player || !playerReady) return false;
    
    try {
        if (videoType === 'youtube') {
            player.seekTo(seconds, true);
            return true;
        }
    } catch (e) {
        console.error('Ошибка установки времени видео:', e);
    }
    
    return false;
}

// Инициализация чата
function initChat() {
    const chatMessages = document.getElementById('chat-messages');
    
    if (!chatMessages) {
        console.error('Контейнер для сообщений не найден');
        return;
    }
    
    // Прокрутка чата вниз при загрузке
    scrollChatToBottom();
    
    // Запуск периодической проверки новых сообщений
    if (messageInterval) {
        clearInterval(messageInterval);
    }
    
    messageInterval = setInterval(fetchNewMessages, 5000);
    
    console.log('Чат инициализирован');
}

// Отправка сообщения в чат
function sendChatMessage(message) {
    if (!message || message.trim() === '') {
        return;
    }
    
    const pageData = getPageData();
    
    if (!pageData.roomId) {
        console.error('ID комнаты не найден');
        showToast('Ошибка: ID комнаты не найден', true);
        return;
    }
    
    fetch('/webapp/send_message', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            room_id: pageData.roomId,
            message: message,
            user_id: pageData.userId
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Сообщение успешно отправлено, добавляем его в чат
            addMessageToChat({
                text: message,
                username: 'Вы',
                timestamp: Date.now() / 1000,
                is_current_user: true
            });
        } else {
            showToast(data.error || 'Не удалось отправить сообщение', true);
        }
    })
    .catch(error => {
        console.error('Ошибка отправки сообщения:', error);
        showToast('Произошла ошибка при отправке сообщения', true);
    });
}

// Добавление сообщения в чат
function addMessageToChat(messageData) {
    if (!messageData) return;
    
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    
    // Удаляем уведомление о пустом чате, если оно есть
    const emptyChat = chatMessages.querySelector('.empty-chat-message');
    if (emptyChat) {
        emptyChat.remove();
    }
    
    const messageElement = document.createElement('div');
    messageElement.className = 'message';
    if (messageData.is_current_user) {
        messageElement.classList.add('outgoing');
    }
    
    const timestamp = messageData.timestamp || Math.floor(Date.now() / 1000);
    messageElement.setAttribute('data-timestamp', timestamp);
    
    const text = messageData.text || '';
    const username = messageData.username || 'Пользователь';
    const formattedTime = formatTime(timestamp);
    
    messageElement.innerHTML = `
        <div class="message-bubble">${escapeHtml(text)}</div>
        <div class="message-info">
            ${escapeHtml(username)} • ${formattedTime}
        </div>
    `;
    
    chatMessages.appendChild(messageElement);
    
    // Прокрутка чата вниз
    scrollChatToBottom();
}

// Прокрутка чата вниз
function scrollChatToBottom() {
    const chatMessages = document.getElementById('chat-messages');
    if (chatMessages) {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }
}

// Получение новых сообщений
function fetchNewMessages() {
    const pageData = getPageData();
    
    if (!pageData.roomId) {
        console.error('ID комнаты не найден');
        return;
    }
    
    const chatMessages = document.getElementById('chat-messages');
    if (!chatMessages) return;
    
    // Получаем timestamp последнего сообщения
    const messages = chatMessages.querySelectorAll('.message');
    let lastTimestamp = 0;
    
    if (messages.length > 0) {
        const lastMessage = messages[messages.length - 1];
        lastTimestamp = lastMessage.getAttribute('data-timestamp') || 0;
    }
    
    fetch(`/webapp/get_messages?room_id=${pageData.roomId}&after=${lastTimestamp}${pageData.userId ? '&user_id=' + pageData.userId : ''}`)
        .then(response => response.json())
        .then(data => {
            if (data.success && data.messages && data.messages.length > 0) {
                data.messages.forEach(message => {
                    // Проверяем, нет ли уже такого сообщения
                    const existingMessage = document.querySelector(`.message[data-timestamp="${message.timestamp}"]`);
                    if (!existingMessage) {
                        addMessageToChat({
                            text: message.text,
                            username: message.username,
                            timestamp: message.timestamp,
                            is_current_user: message.user_id === pageData.userId
                        });
                    }
                });
            }
        })
        .catch(error => {
            console.error('Ошибка получения новых сообщений:', error);
        });
}

// Получение значения cookie
function getCookie(name) {
    try {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return '';
    } catch (e) {
        console.error('Ошибка при получении cookie:', e);
        return '';
    }
}

// Форматирование времени
function formatTime(timestamp) {
    try {
        if (!timestamp) return '';
        
        const date = new Date(timestamp * 1000);
        const hours = date.getHours().toString().padStart(2, '0');
        const minutes = date.getMinutes().toString().padStart(2, '0');
        return `${hours}:${minutes}`;
    } catch (e) {
        console.error('Ошибка при форматировании времени:', e);
        return '';
    }
}

// Показ уведомления
function showToast(message, isError = false) {
    if (!message) return;
    
    // Проверяем, существует ли уже контейнер для toast-уведомлений
    let toastContainer = document.getElementById('toast-container');
    
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    
    const toast = document.createElement('div');
    toast.className = 'toast' + (isError ? ' toast-error' : '');
    toast.textContent = message;
    
    toastContainer.appendChild(toast);
    
    // Удаляем уведомление через 3 секунды
    setTimeout(() => {
        toast.classList.add('toast-hide');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }, 3000);
}

// Безопасное экранирование HTML
function escapeHtml(text) {
    if (!text) return '';
    
    try {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    } catch (e) {
        console.error('Ошибка при экранировании HTML:', e);
        return text.replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', function() {
    try {
        // Инициализация Telegram WebApp
        initTelegramApp();
        
        // Инициализация видеоплеера
        initVideoPlayer();
        
        // Инициализация чата
        initChat();
        
        console.log('Страница комнаты полностью инициализирована');
    } catch (e) {
        console.error('Ошибка при инициализации страницы:', e);
    }
}); 