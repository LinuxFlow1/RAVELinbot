// Звуки
const sounds = {
    click: new Audio('static/sounds/click.mp3'),
    message: new Audio('static/sounds/message.mp3'),
    join: new Audio('static/sounds/join.mp3'),
    leave: new Audio('static/sounds/leave.mp3'),
    success: new Audio('static/sounds/success.mp3'),
    error: new Audio('static/sounds/error.mp3')
};

// Настройка громкости звуков
Object.values(sounds).forEach(sound => {
    sound.volume = 0.5;
});

// Функция для воспроизведения звука
function playSound(soundName) {
    if (sounds[soundName]) {
        sounds[soundName].currentTime = 0;
        sounds[soundName].play().catch(e => console.log("Ошибка воспроизведения звука:", e));
    }
}

// Обработчики нажатий на кнопки
document.addEventListener('DOMContentLoaded', () => {
    // Добавляем анимацию нажатия на все кнопки
    const buttons = document.querySelectorAll('.btn');
    buttons.forEach(button => {
        button.addEventListener('mousedown', () => {
            button.style.transform = 'scale(0.95)';
            playSound('click');
        });

        button.addEventListener('mouseup', () => {
            button.style.transform = 'scale(1)';
        });

        button.addEventListener('mouseleave', () => {
            button.style.transform = 'scale(1)';
        });

        // Добавляем анимацию при долгом нажатии (для мобильных устройств)
        let pressTimer;
        
        button.addEventListener('touchstart', (e) => {
            e.preventDefault();
            playSound('click');
            button.style.transform = 'scale(0.95)';
            
            pressTimer = setTimeout(() => {
                // Добавляем эффект пульсации при долгом нажатии
                button.classList.add('pulse');
            }, 500);
        });

        button.addEventListener('touchend', () => {
            clearTimeout(pressTimer);
            button.style.transform = 'scale(1)';
            button.classList.remove('pulse');
        });
    });

    // Обработка отправки сообщений в чате
    const chatForm = document.getElementById('chat-form');
    if (chatForm) {
        chatForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const messageInput = document.getElementById('message-input');
            const message = messageInput.value.trim();
            
            if (message) {
                // Здесь будет логика отправки сообщения на сервер
                addMessage(message, true);
                messageInput.value = '';
                playSound('message');
            }
        });
    }

    // Анимации для комнат в списке
    const roomItems = document.querySelectorAll('.room-item');
    roomItems.forEach(room => {
        room.addEventListener('click', () => {
            playSound('click');
            // Добавляем класс для анимации перед переходом
            room.classList.add('fade-in');
            
            // Здесь будет логика перехода в комнату
            setTimeout(() => {
                room.classList.remove('fade-in');
            }, 500);
        });
    });
});

// Функция для добавления сообщения в чат
function addMessage(text, isOutgoing = false) {
    const chatMessages = document.querySelector('.chat-messages');
    if (!chatMessages) return;
    
    const messageElement = document.createElement('div');
    messageElement.className = `message ${isOutgoing ? 'outgoing' : ''}`;
    
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.innerText = text;
    
    const info = document.createElement('div');
    info.className = 'message-info';
    
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    
    info.innerText = isOutgoing ? `Вы, ${time}` : `Пользователь, ${time}`;
    
    messageElement.appendChild(bubble);
    messageElement.appendChild(info);
    
    // Добавляем с анимацией
    messageElement.style.opacity = '0';
    messageElement.style.transform = 'translateY(20px)';
    
    chatMessages.appendChild(messageElement);
    
    // Прокручиваем чат вниз
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    // Запускаем анимацию появления
    setTimeout(() => {
        messageElement.style.transition = 'all 0.3s ease';
        messageElement.style.opacity = '1';
        messageElement.style.transform = 'translateY(0)';
    }, 10);
}

// Функция для уведомления о присоединении пользователя
function notifyUserJoined(username) {
    playSound('join');
    
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.innerText = `${username} присоединился к комнате`;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// Функция для уведомления о выходе пользователя
function notifyUserLeft(username) {
    playSound('leave');
    
    const notification = document.createElement('div');
    notification.className = 'notification';
    notification.innerText = `${username} покинул комнату`;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.classList.add('show');
    }, 10);
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}

// Функция для анимации перламутрового эффекта
function initPearlescent() {
    const pearlescentElements = document.querySelectorAll('.pearlescent');
    
    pearlescentElements.forEach(element => {
        element.addEventListener('mouseover', () => {
            element.style.backgroundSize = '150% 150%';
            element.style.animationDuration = '3s';
        });
        
        element.addEventListener('mouseout', () => {
            element.style.backgroundSize = '200% 200%';
            element.style.animationDuration = '6s';
        });
    });
}

// Инициализация перламутрового эффекта при загрузке страницы
document.addEventListener('DOMContentLoaded', initPearlescent); 