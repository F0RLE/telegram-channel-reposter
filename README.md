<details>
<summary><b>🇨🇳 中文 (点击展开)</b></summary>

# 📢 Telegram 频道转发器

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Windows](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![GitHub](https://img.shields.io/badge/GitHub-F0RLE-black.svg)](https://github.com/F0RLE)

> 自动监控 Telegram 频道、处理内容并发布到您的频道，支持手动编辑

**版本:** 1.1.0 | **最后更新:** 2025-11-23

---

## 🎯 这是什么？

**Telegram Channel Reposter** 是一个全面的自动化解决方案，用于处理 Telegram 频道内容：

- 📺 **频道监控** - 直接在机器人中查看和跟踪各种 Telegram 频道的帖子
- ✏️ **内容处理** - 使用 LLM 自动重新生成文本以改进和适应
- 🎨 **图像生成** - 通过 Stable Diffusion 基于文本创建独特图像
- 📤 **自动发布** - 将处理后的内容发送到目标频道
- ✋ **手动编辑** - 发布前可以编辑内容

## ✨ 主要功能

- 🚀 **图形启动器** - 方便管理所有组件的界面
- 🤖 **Telegram 机器人** - 用于查看和处理内容的交互式机器人
- 📝 **文本处理** - 与 Ollama 集成以处理和改进文本
- 🎨 **图像生成** - Stable Diffusion 配合 ADetailer 创建高质量视觉内容
- 📊 **监控** - 跟踪所有服务和系统资源的状态
- 🔄 **自动化** - 自动安装依赖项和更新
- 🛡️ **安全** - 速率限制、数据验证、SSL 加密
- 📋 **日志** - 按服务过滤的详细日志

## 📋 要求

- Windows 10/11
- Python 3.10 或 3.11（自动安装）
- 互联网连接（用于下载依赖项）

## 🛠️ 快速开始

### 安装

1. **运行 `Install.bat`**
   - 脚本将自动安装 Python、Git 和所有必需的依赖项
   - 安装可能需要几分钟

2. **运行 `Launch.bat`**
   - 将打开带有图形界面的启动器

### 初始设置

1. **Telegram Bot Token**
   - 从 [@BotFather](https://t.me/BotFather) 获取令牌
   - 在启动器设置中输入令牌（主要选项卡）

2. **Target Channel ID**
   - 将发布帖子的频道 ID
   - 可以通过机器人 [@userinfobot](https://t.me/userinfobot) 获取

3. **LLM Model**
   - 将 GGUF 模型放在 `Engine/LLM_Models/` 文件夹中
   - 首次启动时将自动导入到 Ollama

## 📄 许可证

本项目根据 MIT 许可证分发。详见 [LICENSE](LICENSE) 文件。

---

**用 ❤️ 开发，用于自动化 Telegram 频道内容工作**

</details>

---

<details>
<summary><b>🇪🇸 Español (Haz clic para expandir)</b></summary>

# 📢 Telegram Channel Reposter

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Windows](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![GitHub](https://img.shields.io/badge/GitHub-F0RLE-black.svg)](https://github.com/F0RLE)

> Sistema automatizado para monitorear canales de Telegram, procesar contenido y publicar en tu canal con capacidades de edición manual

**Versión:** 1.1.0 | **Última actualización:** 2025-11-23

---

## 🎯 ¿Qué es esto?

**Telegram Channel Reposter** es una solución integral para automatizar el trabajo con contenido de canales de Telegram:

- 📺 **Monitoreo de Canales** - Ver y rastrear publicaciones de varios canales de Telegram directamente en el bot
- ✏️ **Procesamiento de Contenido** - Regeneración automática de texto usando LLM para mejorar y adaptar
- 🎨 **Generación de Imágenes** - Crear imágenes únicas basadas en texto a través de Stable Diffusion
- 📤 **Auto-publicación** - Enviar contenido procesado a tu canal objetivo
- ✋ **Edición Manual** - Capacidad de editar contenido antes de publicar

## ✨ Características Principales

- 🚀 **Lanzador Gráfico** - Interfaz conveniente para gestionar todos los componentes
- 🤖 **Bot de Telegram** - Bot interactivo para ver y trabajar con contenido
- 📝 **Procesamiento de Texto** - Integración con Ollama para procesar y mejorar texto
- 🎨 **Generación de Imágenes** - Stable Diffusion con ADetailer para crear contenido visual de calidad
- 📊 **Monitoreo** - Seguimiento del estado de todos los servicios y recursos del sistema
- 🔄 **Automatización** - Instalación automática de dependencias y actualizaciones
- 🛡️ **Seguridad** - Limitación de tasa, validación de datos, cifrado SSL
- 📋 **Registro** - Registros detallados con filtrado por servicios

## 📋 Requisitos

- Windows 10/11
- Python 3.10 o 3.11 (se instala automáticamente)
- Conexión a Internet (para descargar dependencias)

## 🛠️ Inicio Rápido

### Instalación

1. **Ejecutar `Install.bat`**
   - El script instalará automáticamente Python, Git y todas las dependencias necesarias
   - La instalación puede tardar varios minutos

2. **Ejecutar `Launch.bat`**
   - Se abrirá el lanzador con interfaz gráfica

### Configuración Inicial

1. **Token del Bot de Telegram**
   - Obtener un token de [@BotFather](https://t.me/BotFather)
   - Ingresar el token en la configuración del lanzador (pestaña Principal)

2. **ID del Canal Objetivo**
   - ID del canal donde se publicarán las publicaciones
   - Se puede obtener a través del bot [@userinfobot](https://t.me/userinfobot)

3. **Modelo LLM**
   - Colocar modelos GGUF en la carpeta `Engine/LLM_Models/`
   - Los modelos se importarán automáticamente a Ollama en el primer inicio

## 📄 Licencia

Este proyecto se distribuye bajo la Licencia MIT. Ver el archivo [LICENSE](LICENSE) para más detalles.

---

**Desarrollado con ❤️ para automatizar el trabajo con contenido de canales de Telegram**

</details>

---

<details>
<summary><b>🇮🇳 हिंदी (विस्तार करने के लिए क्लिक करें)</b></summary>

# 📢 Telegram Channel Reposter

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Windows](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![GitHub](https://img.shields.io/badge/GitHub-F0RLE-black.svg)](https://github.com/F0RLE)

> Telegram चैनलों की निगरानी, सामग्री प्रसंस्करण, और मैनुअल संपादन क्षमताओं के साथ आपके चैनल पर प्रकाशन के लिए स्वचालित प्रणाली

**संस्करण:** 1.1.0 | **अंतिम अपडेट:** 2025-11-23

---

## 🎯 यह क्या है?

**Telegram Channel Reposter** Telegram चैनलों की सामग्री के साथ काम को स्वचालित करने के लिए एक व्यापक समाधान है:

- 📺 **चैनल निगरानी** - सीधे बॉट में विभिन्न Telegram चैनलों से पोस्ट देखें और ट्रैक करें
- ✏️ **सामग्री प्रसंस्करण** - सुधार और अनुकूलन के लिए LLM का उपयोग करके स्वचालित टेक्स्ट पुनर्जनन
- 🎨 **छवि निर्माण** - Stable Diffusion के माध्यम से टेक्स्ट के आधार पर अद्वितीय छवियाँ बनाएं
- 📤 **स्वतः प्रकाशन** - प्रोसेस की गई सामग्री को अपने लक्ष्य चैनल पर भेजें
- ✋ **मैनुअल संपादन** - प्रकाशन से पहले सामग्री संपादित करने की क्षमता

## ✨ मुख्य विशेषताएं

- 🚀 **ग्राफिकल लॉन्चर** - सभी घटकों को प्रबंधित करने के लिए सुविधाजनक इंटरफ़ेस
- 🤖 **Telegram बॉट** - सामग्री देखने और काम करने के लिए इंटरैक्टिव बॉट
- 📝 **टेक्स्ट प्रसंस्करण** - टेक्स्ट प्रसंस्करण और सुधार के लिए Ollama के साथ एकीकरण
- 🎨 **छवि निर्माण** - गुणवत्ता दृश्य सामग्री बनाने के लिए ADetailer के साथ Stable Diffusion
- 📊 **निगरानी** - सभी सेवाओं और सिस्टम संसाधनों की स्थिति ट्रैक करें
- 🔄 **स्वचालन** - स्वचालित निर्भरता स्थापना और अपडेट
- 🛡️ **सुरक्षा** - दर सीमा, डेटा सत्यापन, SSL एन्क्रिप्शन
- 📋 **लॉगिंग** - सेवाओं द्वारा फ़िल्टरिंग के साथ विस्तृत लॉग

## 📋 आवश्यकताएँ

- Windows 10/11
- Python 3.10 या 3.11 (स्वचालित रूप से स्थापित)
- इंटरनेट कनेक्शन (निर्भरताओं को डाउनलोड करने के लिए)

## 🛠️ त्वरित प्रारंभ

### स्थापना

1. **`Install.bat` चलाएं**
   - स्क्रिप्ट स्वचालित रूप से Python, Git और सभी आवश्यक निर्भरताओं को स्थापित करेगी
   - स्थापना में कुछ मिनट लग सकते हैं

2. **`Launch.bat` चलाएं**
   - ग्राफिकल इंटरफ़ेस के साथ लॉन्चर खुलेगा

### प्रारंभिक सेटअप

1. **Telegram बॉट टोकन**
   - [@BotFather](https://t.me/BotFather) से टोकन प्राप्त करें
   - लॉन्चर सेटिंग्स में टोकन दर्ज करें (मुख्य टैब)

2. **लक्ष्य चैनल ID**
   - उस चैनल की ID जहाँ पोस्ट प्रकाशित होंगे
   - बॉट [@userinfobot](https://t.me/userinfobot) के माध्यम से प्राप्त किया जा सकता है

3. **LLM मॉडल**
   - GGUF मॉडल को `Engine/LLM_Models/` फ़ोल्डर में रखें
   - पहले लॉन्च पर मॉडल स्वचालित रूप से Ollama में आयात हो जाएंगे

## 📄 लाइसेंस

यह परियोजना MIT लाइसेंस के तहत वितरित की जाती है। विवरण के लिए [LICENSE](LICENSE) फ़ाइल देखें।

---

**Telegram चैनल सामग्री के साथ काम को स्वचालित करने के लिए ❤️ के साथ विकसित**

</details>

---

<details>
<summary><b>🇸🇦 العربية (انقر للتوسيع)</b></summary>

# 📢 Telegram Channel Reposter

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Windows](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)
[![GitHub](https://img.shields.io/badge/GitHub-F0RLE-black.svg)](https://github.com/F0RLE)

> نظام آلي لمراقبة قنوات Telegram ومعالجة المحتوى والنشر على قناتك مع إمكانيات التحرير اليدوي

**الإصدار:** 1.1.0 | **آخر تحديث:** 2025-11-23

---

## 🎯 ما هذا؟

**Telegram Channel Reposter** هو حل شامل لأتمتة العمل مع محتوى قنوات Telegram:

- 📺 **مراقبة القنوات** - عرض وتتبع المنشورات من قنوات Telegram المختلفة مباشرة في البوت
- ✏️ **معالجة المحتوى** - إعادة توليد النص تلقائيًا باستخدام LLM للتحسين والتكيف
- 🎨 **توليد الصور** - إنشاء صور فريدة بناءً على النص من خلال Stable Diffusion
- 📤 **النشر التلقائي** - إرسال المحتوى المعالج إلى قناتك المستهدفة
- ✋ **التحرير اليدوي** - القدرة على تحرير المحتوى قبل النشر

## ✨ الميزات الرئيسية

- 🚀 **المشغل الرسومي** - واجهة مريحة لإدارة جميع المكونات
- 🤖 **بوت Telegram** - بوت تفاعلي لعرض والعمل مع المحتوى
- 📝 **معالجة النص** - التكامل مع Ollama لمعالجة وتحسين النص
- 🎨 **توليد الصور** - Stable Diffusion مع ADetailer لإنشاء محتوى مرئي عالي الجودة
- 📊 **المراقبة** - تتبع حالة جميع الخدمات وموارد النظام
- 🔄 **الأتمتة** - تثبيت التبعيات والتحديثات تلقائيًا
- 🛡️ **الأمان** - تحديد المعدل والتحقق من البيانات وتشفير SSL
- 📋 **التسجيل** - سجلات مفصلة مع التصفية حسب الخدمات

## 📋 المتطلبات

- Windows 10/11
- Python 3.10 أو 3.11 (يتم التثبيت تلقائيًا)
- اتصال بالإنترنت (لتنزيل التبعيات)

## 🛠️ البدء السريع

### التثبيت

1. **قم بتشغيل `Install.bat`**
   - سيقوم السكريبت بتثبيت Python و Git وجميع التبعيات اللازمة تلقائيًا
   - قد يستغرق التثبيت عدة دقائق

2. **قم بتشغيل `Launch.bat`**
   - سيفتح المشغل مع واجهة رسومية

### الإعداد الأولي

1. **رمز بوت Telegram**
   - احصل على رمز من [@BotFather](https://t.me/BotFather)
   - أدخل الرمز في إعدادات المشغل (علامة التبويب الرئيسية)

2. **معرف القناة المستهدفة**
   - معرف القناة التي سيتم نشر المنشورات فيها
   - يمكن الحصول عليه عبر البوت [@userinfobot](https://t.me/userinfobot)

3. **نموذج LLM**
   - ضع نماذج GGUF في مجلد `Engine/LLM_Models/`
   - سيتم استيراد النماذج تلقائيًا إلى Ollama عند التشغيل الأول

## 📄 الترخيص

يتم توزيع هذا المشروع بموجب ترخيص MIT. راجع ملف [LICENSE](LICENSE) للحصول على التفاصيل.

---

**تم التطوير بـ ❤️ لأتمتة العمل مع محتوى قنوات Telegram**

</details>

---

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
