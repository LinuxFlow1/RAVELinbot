# RAVELinbot

Telegram бот для совместного просмотра видео с друзьями. Позволяет создавать комнаты для просмотра, синхронизировать воспроизведение и общаться в чате.

## Возможности

- 🎥 Создание комнат для совместного просмотра
- 👥 Приглашение друзей по ссылке
- 💬 Встроенный чат
- ⏯️ Синхронизация воспроизведения видео
- 📱 Адаптивный интерфейс
- 🔒 Система модерации комнат

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/LinuxFlow1/RAVELinbot.git
cd RAVELinbot
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте конфигурацию:
- Создайте бота через [@BotFather](https://t.me/BotFather)
- Получите токен бота
- Настройте веб-приложение в BotFather

## Использование

### Локальный запуск

```bash
python simple_bot.py
```

### Развертывание на PythonAnywhere

1. Создайте аккаунт на [PythonAnywhere](https://www.pythonanywhere.com)
2. В консоли выполните:
```bash
git clone https://github.com/LinuxFlow1/RAVELinbot.git
cd RAVELinbot
pip3 install --user -r requirements.txt
```

3. Создайте веб-приложение:
- Выберите Python 3.9
- Укажите путь: `/home/username/RAVELinbot/pythonanywhere_flask_app.py`
- Настройте WSGI файл

## Команды бота

- `/start` - Начать работу с ботом
- `/create` - Создать новую комнату
- `/join [room_id]` - Присоединиться к комнате
- `/help` - Показать справку

## Технологии

- Python 3.9
- Flask
- pyTelegramBotAPI
- WebSocket
- HTML5 Video API

## Структура проекта

```
RAVELinbot/
├── simple_bot.py          # Основной файл бота
├── pythonanywhere_flask_app.py  # Точка входа для PythonAnywhere
├── requirements.txt       # Зависимости проекта
├── static/               # Статические файлы
│   └── webapp/          # Файлы веб-приложения
├── templates/            # HTML шаблоны
│   └── webapp/          # Шаблоны веб-приложения
└── README.md            # Документация
```

## Разработка

Бот находится в активной разработке. Планируемые улучшения:
- [ ] Поддержка различных видео-платформ
- [ ] Система плейлистов
- [ ] Улучшенная синхронизация
- [ ] Голосовой чат

## Лицензия

MIT License

## Автор

LinuxFlow - [GitHub](https://github.com/LinuxFlow1)

## Поддержка

Если у вас возникли проблемы или есть предложения по улучшению:
1. Создайте Issue в репозитории
2. Напишите мне в Telegram
3. Отправьте Pull Request 
