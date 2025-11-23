<details>
<summary><b>🇷🇺 Русский (Нажмите, чтобы развернуть)</b></summary>

# 📢 Telegram Channel Reposter

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Windows](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![GitHub](https://img.shields.io/badge/GitHub-F0RLE-black.svg)](https://github.com/F0RLE)

> Автоматизированная система для мониторинга Telegram каналов, переработки контента и публикации в ваш канал с возможностью ручного редактирования

**Версия:** 1.1.0 | **Последнее обновление:** 2025-11-23

---

## 🎯 Что это?

**Telegram Channel Reposter** — это комплексное решение для автоматизации работы с контентом из Telegram каналов:

- 📺 **Мониторинг каналов** - Просмотр и отслеживание постов из различных Telegram каналов прямо в боте
- ✏️ **Переработка контента** - Автоматическая перегенерация текста с помощью LLM для улучшения и адаптации
- 🎨 **Генерация изображений** - Создание уникальных изображений на основе текста через Stable Diffusion
- 📤 **Автопубликация** - Отправка обработанного контента в ваш целевой канал
- ✋ **Ручное редактирование** - Возможность изменить контент перед публикацией

## ✨ Основные возможности

- 🚀 **Графический лаунчер** - Удобный интерфейс для управления всеми компонентами
- 🤖 **Telegram бот** - Интерактивный бот для просмотра и работы с контентом
- 📝 **Обработка текста** - Интеграция с Ollama для переработки и улучшения текста
- 🎨 **Генерация изображений** - Stable Diffusion с ADetailer для создания качественного визуального контента
- 📊 **Мониторинг** - Отслеживание состояния всех сервисов и системных ресурсов
- 🔄 **Автоматизация** - Автоустановка зависимостей и обновлений
- 🛡️ **Безопасность** - Rate limiting, валидация данных, SSL шифрование
- 📋 **Логирование** - Детальные логи с фильтрацией по сервисам

## 📋 Требования

- Windows 10/11
- Python 3.10 или 3.11 (устанавливается автоматически)
- Интернет-соединение (для загрузки зависимостей)

## 🛠️ Быстрый старт

### Установка

1. **Запустите `Install.bat`**
   - Скрипт автоматически установит Python, Git и все необходимые зависимости
   - Установка может занять несколько минут

2. **Запустите `Launch.bat`**
   - Откроется лаунчер с графическим интерфейсом

### Первоначальная настройка

1. **Telegram Bot Token**
   - Получите токен от [@BotFather](https://t.me/BotFather)
   - Введите токен в настройках лаунчера (вкладка "Основные")

2. **Target Channel ID**
   - ID канала, куда будут публиковаться посты
   - Можно получить через бота [@userinfobot](https://t.me/userinfobot)

3. **LLM Model**
   - Поместите GGUF модели в папку `Engine/LLM_Models/`
   - Модели будут автоматически импортированы в Ollama при первом запуске

## ⚙️ Настройки

### Настройки текста

- **LLM Model**: Выберите модель для обработки текста
- **Temperature**: Температура генерации (0.0-1.0)
- **Context Window**: Размер контекстного окна

### Настройки изображений

- **Steps**: Количество шагов генерации
- **CFG Scale**: Масштаб CFG
- **Width/Height**: Размеры изображения

## 📁 Структура проекта

```
telegram-channel-reposter/
├── .github/
│   ├── workflows/         # CI/CD конфигурация
│   └── ISSUE_TEMPLATE/    # Шаблоны для Issues
├── system/src/
│   ├── launcher/          # Файлы лаунчера
│   │   ├── launcher.pyw   # Главный файл
│   │   ├── channels.py    # Управление каналами
│   │   ├── ui_components.py
│   │   └── core/          # Ядро лаунчера
│   ├── config/            # Конфигурация
│   ├── core/              # Ядро бота (validators, error_handler, monitoring)
│   ├── handlers/          # Обработчики команд
│   ├── keyboards/         # Клавиатуры
│   ├── modules/           # Модули (LLM, парсер, генерация)
│   ├── main.py            # Точка входа бота
│   └── requirements.txt   # Зависимости Python
├── tests/                 # Unit-тесты
├── Launch.bat             # Запуск лаунчера
├── Install.bat            # Установка зависимостей
├── README.md              # Документация
├── LICENSE                # Лицензия MIT
└── .gitignore            # Игнорируемые файлы
```

## 📂 Структура данных

Все данные хранятся в `%APPDATA%\TelegramBotData\`:

```
TelegramBotData/
├── data/
│   ├── Engine/
│   │   ├── LLM_Models/    # Модели LLM
│   │   ├── ollama/        # Ollama сервер
│   │   └── stable-diffusion-webui-reforge/
│   ├── configs/           # Конфигурационные файлы
│   ├── logs/              # Логи
│   ├── temp/              # Временные файлы
│   └── backups/           # Резервные копии
└── env/                   # Python и Git
```

## 🔧 Использование

### Запуск сервисов

1. **Telegram Bot**
   - Нажмите кнопку ▶ рядом с "Telegram Bot"
   - Убедитесь, что токен настроен
   - Бот позволит просматривать посты из каналов и управлять контентом

2. **LLM Server (Ollama)**
   - Выберите модель в настройках
   - Нажмите ▶ для запуска
   - При первом запуске Ollama будет автоматически установлен
   - Используется для переработки и улучшения текста

3. **Stable Diffusion**
   - Убедитесь, что Stable Diffusion установлен
   - Нажмите ▶ для запуска
   - Используется для генерации изображений на основе текста

### Работа с контентом

1. **Настройка каналов**
   - Перейдите на вкладку "Каналы" в лаунчере
   - Создайте тему (например, "Новости", "Технологии")
   - Добавьте каналы в тему (формат: `@username` или `https://t.me/username`)

2. **Просмотр и выбор постов**
   - В боте выберите тему и канал
   - Просмотрите доступные посты
   - Выберите пост для обработки

3. **Обработка контента**
   - Текст автоматически перерабатывается через LLM
   - При необходимости можно сгенерировать изображение
   - Вы можете вручную отредактировать контент перед публикацией

4. **Публикация**
   - После обработки контент отправляется в ваш целевой канал
   - Все опубликованные посты сохраняются для избежания дублирования

### Просмотр логов

- Вкладка "Консоль" показывает логи всех сервисов
- Используйте вкладки для фильтрации по сервисам
- Горячие клавиши: `Ctrl+1-4` для переключения вкладок

## 🐛 Решение проблем

### Ollama не запускается

1. Проверьте, установлен ли Ollama
2. Если нет - лаунчер попытается установить его автоматически
3. Или установите вручную с [ollama.com](https://ollama.com/download)

### Бот не запускается

1. Проверьте токен бота в настройках
2. Убедитесь, что токен правильный и активный
3. Проверьте логи в консоли лаунчера

### Модели не загружаются

1. Убедитесь, что GGUF файлы находятся в `Engine/LLM_Models/`
2. Проверьте, что файлы имеют расширение `.gguf`
3. Модели будут автоматически импортированы в Ollama

## 📝 Логирование

Логи сохраняются в:
- Консоль лаунчера (в реальном времени)
- Файлы в `%APPDATA%\TelegramBotData\data\logs\`
- Файлы сбоев: `crash_YYYYMMDD_HHMMSS.log`

## 🔄 Резервное копирование

Лаунчер автоматически создает резервные копии:
- При сохранении настроек
- При изменении конфигурации
- Хранятся в `data/backups/`
- Сохраняются последние 10 копий

## 📦 Установка из исходников

```bash
# Клонировать репозиторий
git clone https://github.com/F0RLE/telegram-channel-reposter.git
cd telegram-channel-reposter

# Установить зависимости
cd system/src
pip install -r requirements.txt

# Запустить лаунчер
python launcher/launcher.pyw
```

## 🧪 Тестирование

Проект включает unit-тесты для основных модулей:

```bash
# Установка зависимостей для тестирования
pip install pytest pytest-asyncio pytest-cov

# Запуск тестов
pytest tests/ -v

# С покрытием кода
pytest tests/ --cov=system/src --cov-report=html
```

## 🏗️ Технические особенности

- ✅ **Модульная архитектура** - Чистый и поддерживаемый код
- ✅ **Обработка ошибок** - Retry механизм с exponential backoff
- ✅ **Rate limiting** - Защита от перегрузки API
- ✅ **Мониторинг** - Сбор метрик и статистики
- ✅ **Тестирование** - Unit-тесты для основных модулей
- ✅ **Документация** - Type hints и docstrings
- ✅ **CI/CD** - Автоматические тесты и релизы

## 📄 Лицензия

Этот проект распространяется под лицензией MIT. См. файл [LICENSE](LICENSE) для подробностей.

## 🤝 Вклад в проект

Мы приветствуем вклад в проект! Пожалуйста, ознакомьтесь с [CONTRIBUTING.md](CONTRIBUTING.md) для получения информации о стандартах кода и процессе разработки.

## 🔄 Обновления

Для обновления:
1. Скачайте новую версию
2. Замените файлы (кроме папки `data/`)
3. Запустите `Launch.bat`

## 📞 Поддержка

Если у вас возникли вопросы или проблемы:
1. Проверьте [Issues](https://github.com/F0RLE/telegram-channel-reposter/issues)
2. Создайте новый Issue с описанием проблемы
3. Приложите логи из папки `logs/`

## ⭐ Звезды

Если проект вам понравился, поставьте ⭐ звезду на GitHub!

---

**Разработано с ❤️ для автоматизации работы с контентом из Telegram каналов**

</details>

---

# 📢 Telegram Channel Reposter

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Windows](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![GitHub](https://img.shields.io/badge/GitHub-F0RLE-black.svg)](https://github.com/F0RLE)

> Automated system for monitoring Telegram channels, content processing, and publishing to your channel with manual editing capabilities

**Version:** 1.1.0 | **Last Updated:** 2025-11-23

---

## 🎯 What is this?

**Telegram Channel Reposter** is a comprehensive solution for automating work with content from Telegram channels:

- 📺 **Channel Monitoring** - View and track posts from various Telegram channels directly in the bot
- ✏️ **Content Processing** - Automatic text regeneration using LLM for improvement and adaptation
- 🎨 **Image Generation** - Create unique images based on text through Stable Diffusion
- 📤 **Auto-publishing** - Send processed content to your target channel
- ✋ **Manual Editing** - Ability to edit content before publishing

## ✨ Key Features

- 🚀 **Graphical Launcher** - Convenient interface for managing all components
- 🤖 **Telegram Bot** - Interactive bot for viewing and working with content
- 📝 **Text Processing** - Integration with Ollama for text processing and improvement
- 🎨 **Image Generation** - Stable Diffusion with ADetailer for creating quality visual content
- 📊 **Monitoring** - Track status of all services and system resources
- 🔄 **Automation** - Automatic dependency installation and updates
- 🛡️ **Security** - Rate limiting, data validation, SSL encryption
- 📋 **Logging** - Detailed logs with filtering by services

## 📋 Requirements

- Windows 10/11
- Python 3.10 or 3.11 (installed automatically)
- Internet connection (for downloading dependencies)

## 🛠️ Quick Start

### Installation

1. **Run `Install.bat`**
   - The script will automatically install Python, Git, and all necessary dependencies
   - Installation may take several minutes

2. **Run `Launch.bat`**
   - The launcher with graphical interface will open

### Initial Setup

1. **Telegram Bot Token**
   - Get a token from [@BotFather](https://t.me/BotFather)
   - Enter the token in launcher settings (Main tab)

2. **Target Channel ID**
   - ID of the channel where posts will be published
   - Can be obtained via bot [@userinfobot](https://t.me/userinfobot)

3. **LLM Model**
   - Place GGUF models in the `Engine/LLM_Models/` folder
   - Models will be automatically imported into Ollama on first launch

## ⚙️ Settings

### Text Settings

- **LLM Model**: Select a model for text processing
- **Temperature**: Generation temperature (0.0-1.0)
- **Context Window**: Context window size

### Image Settings

- **Steps**: Number of generation steps
- **CFG Scale**: CFG scale
- **Width/Height**: Image dimensions

## 📁 Project Structure

```
telegram-channel-reposter/
├── .github/
│   ├── workflows/         # CI/CD configuration
│   └── ISSUE_TEMPLATE/    # Issue templates
├── system/src/
│   ├── launcher/          # Launcher files
│   │   ├── launcher.pyw   # Main file
│   │   ├── channels.py    # Channel management
│   │   ├── ui_components.py
│   │   └── core/          # Launcher core
│   ├── config/            # Configuration
│   ├── core/              # Bot core (validators, error_handler, monitoring)
│   ├── handlers/          # Command handlers
│   ├── keyboards/         # Keyboards
│   ├── modules/           # Modules (LLM, parser, generation)
│   ├── main.py            # Bot entry point
│   └── requirements.txt   # Python dependencies
├── tests/                 # Unit tests
├── Launch.bat             # Launch launcher
├── Install.bat            # Install dependencies
├── README.md              # Documentation
├── LICENSE                # MIT License
└── .gitignore            # Ignored files
```

## 📂 Data Structure

All data is stored in `%APPDATA%\TelegramBotData\`:

```
TelegramBotData/
├── data/
│   ├── Engine/
│   │   ├── LLM_Models/    # LLM models
│   │   ├── ollama/        # Ollama server
│   │   └── stable-diffusion-webui-reforge/
│   ├── configs/           # Configuration files
│   ├── logs/              # Logs
│   ├── temp/              # Temporary files
│   └── backups/           # Backups
└── env/                   # Python and Git
```

## 🔧 Usage

### Starting Services

1. **Telegram Bot**
   - Click the ▶ button next to "Telegram Bot"
   - Make sure the token is configured
   - The bot will allow viewing posts from channels and managing content

2. **LLM Server (Ollama)**
   - Select a model in settings
   - Click ▶ to start
   - On first launch, Ollama will be automatically installed
   - Used for text processing and improvement

3. **Stable Diffusion**
   - Make sure Stable Diffusion is installed
   - Click ▶ to start
   - Used for generating images based on text

### Working with Content

1. **Channel Setup**
   - Go to the "Channels" tab in the launcher
   - Create a topic (e.g., "News", "Technology")
   - Add channels to the topic (format: `@username` or `https://t.me/username`)

2. **Viewing and Selecting Posts**
   - In the bot, select a topic and channel
   - View available posts
   - Select a post for processing

3. **Content Processing**
   - Text is automatically processed through LLM
   - If necessary, you can generate an image
   - You can manually edit content before publishing

4. **Publishing**
   - After processing, content is sent to your target channel
   - All published posts are saved to avoid duplication

### Viewing Logs

- The "Console" tab shows logs from all services
- Use tabs to filter by services
- Hotkeys: `Ctrl+1-4` to switch tabs

## 🐛 Troubleshooting

### Ollama won't start

1. Check if Ollama is installed
2. If not - the launcher will attempt to install it automatically
3. Or install manually from [ollama.com](https://ollama.com/download)

### Bot won't start

1. Check the bot token in settings
2. Make sure the token is correct and active
3. Check logs in the launcher console

### Models won't load

1. Make sure GGUF files are in `Engine/LLM_Models/`
2. Check that files have `.gguf` extension
3. Models will be automatically imported into Ollama

## 📝 Logging

Logs are saved to:
- Launcher console (in real-time)
- Files in `%APPDATA%\TelegramBotData\data\logs\`
- Crash files: `crash_YYYYMMDD_HHMMSS.log`

## 🔄 Backup

The launcher automatically creates backups:
- When saving settings
- When changing configuration
- Stored in `data/backups/`
- Last 10 copies are kept

## 📦 Installation from Source

```bash
# Clone repository
git clone https://github.com/F0RLE/telegram-channel-reposter.git
cd telegram-channel-reposter

# Install dependencies
cd system/src
pip install -r requirements.txt

# Run launcher
python launcher/launcher.pyw
```

## 🧪 Testing

The project includes unit tests for main modules:

```bash
# Install testing dependencies
pip install pytest pytest-asyncio pytest-cov

# Run tests
pytest tests/ -v

# With code coverage
pytest tests/ --cov=system/src --cov-report=html
```

## 🏗️ Technical Features

- ✅ **Modular Architecture** - Clean and maintainable code
- ✅ **Error Handling** - Retry mechanism with exponential backoff
- ✅ **Rate Limiting** - Protection against API overload
- ✅ **Monitoring** - Metrics and statistics collection
- ✅ **Testing** - Unit tests for main modules
- ✅ **Documentation** - Type hints and docstrings
- ✅ **CI/CD** - Automatic tests and releases

## 📄 License

This project is distributed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

We welcome contributions to the project! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for information on code standards and development process.

## 🔄 Updates

To update:
1. Download the new version
2. Replace files (except the `data/` folder)
3. Run `Launch.bat`

## 📞 Support

If you have questions or issues:
1. Check [Issues](https://github.com/F0RLE/telegram-channel-reposter/issues)
2. Create a new Issue with problem description
3. Attach logs from the `logs/` folder

## ⭐ Stars

If you liked the project, give it a ⭐ star on GitHub!

---

**Developed with ❤️ for automating work with content from Telegram channels**
