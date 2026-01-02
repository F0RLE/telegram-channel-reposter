# Flux Platform — Архитектура

> [!IMPORTANT]
> Этот документ является архитектурной спецификацией.
> Изменения в нём требуют осознанного решения и ревью.

## Обзор

Flux Platform — десктопное приложение на **Tauri v2** + **Rust** + **Vite**.

**Ключевой принцип:** Вся бизнес-логика выполняется в **Rust**, WebView служит только для отображения UI.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          Tauri Shell (Rust)                             │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐    ┌─────────────────────────────────────────┐ │
│  │    WebView (UI)     │◄──►│            Rust Backend                 │ │
│  │                     │ IPC│                                         │ │
│  │  • HTML/CSS/TS      │    │  ┌─────────────┐  ┌─────────────────┐   │ │
│  │  • Подписки events  │    │  │  commands/  │  │    services/    │   │ │
│  │  • Рендеринг DOM    │    │  │ (IPC слой)  │──│ (бизнес-логика) │   │ │
│  │  • НЕТ вычислений   │    │  └─────────────┘  └────────┬────────┘   │ │
│  │  • НЕТ валидаций    │    │                           │             │ │
│  └─────────────────────┘    │  ┌────────────────────────▼──────────┐  │ │
│                             │  │  • SQLite (чат)                   │  │ │
│                             │  │  • Файлы (.env, JSON)             │  │ │
│                             │  │  • NVML (GPU)                     │  │ │
│                             │  │  • Python AI API (reqwest)        │  │ │
│                             │  └───────────────────────────────────┘  │ │
│                             └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Архитектурные принципы

> Эти правила предотвращают архитектурный дрейф со временем.

| Правило                                 | Пояснение                                                                 |
| --------------------------------------- | ------------------------------------------------------------------------- |
| **Вся бизнес-логика — только в Rust**   | Frontend не содержит вычислений или валидаций                             |
| **IPC команды — тонкий слой**           | `commands/` только валидирует и вызывает `services/`                      |
| **services/ не знают о Tauri**          | Сервисы не импортируют `tauri::*` (за исключением `AppHandle` для events) |
| **Нет глобального состояния**           | `services/` не используют глобальное состояние без явной инициализации    |
| **UI не знает о внутреннем устройстве** | Frontend получает готовые данные, не детали реализации                    |
| **Event-driven где возможно**           | System monitor использует события, а не polling                           |

---

## Безопасность

> Frontend считается **недоверенной средой**.

| Аспект                 | Реализация                                                 |
| ---------------------- | ---------------------------------------------------------- |
| **Лицензирование**     | Проверка только в Rust, UI получает только `LicenseStatus` |
| **Критичные операции** | Выполняются в backend (установка модулей, настройки)       |
| **Валидация**          | Все входные данные валидируются в `commands/`              |
| **Секреты**            | Никогда не передаются в frontend                           |

> [!WARNING]
> Лицензия не считается защитой от взлома.
> Цель — усложнение, контроль доступа и коммерческая логика.

---

## Структура Backend (Rust)

```
src-tauri/src/
├── lib.rs                 # Точка входа, регистрация команд и сервисов
├── commands/              # IPC слой (тонкий!) — валидация → вызов services/
│   ├── system.rs          # get_system_stats, get_gpu_info
│   ├── modules.rs         # get_modules, control_module
│   ├── settings.rs        # get_settings, save_settings
│   ├── license.rs         # get_license_status, activate_license
│   ├── window_settings.rs # save_window_size, save_zoom_level
│   ├── downloader.rs      # start_download, cancel_download
│   └── ...
│
├── services/              # ВCСЯ БИЗНЕС-ЛОГИКА
│   ├── system_monitor.rs  # [252 строк] Мониторинг CPU/RAM/GPU/Disk/Network + events
│   ├── chat.rs            # [220 строк] SQLite история + API клиент для Python AI
│   ├── downloader.rs      # [161 строк] Async загрузка с прогрессом
│   ├── settings.rs        # [80 строк] Чтение/запись .env конфига
│   ├── module_controller.rs # Запуск/остановка модулей
│   ├── module_lifecycle.rs  # Trait для плагинов
│   ├── window_settings.rs # Сохранение размера/позиции окна
│   ├── theme.rs           # Динамические темы
│   ├── translations.rs    # i18n из JSON файлов
│   ├── logs.rs            # Централизованное логирование
│   └── license/           # Лицензирование
│       ├── types.rs
│       ├── verifier.rs
│       └── storage.rs
│
├── models/                # DTO (Data Transfer Objects)
│   ├── settings.rs        # AppSettings (theme, language, api_base_url...)
│   ├── system.rs          # SystemStats, CpuStats, RamStats, GpuStats...
│   ├── modules.rs         # Module, ModuleStatus
│   └── license.rs         # LicenseInfo, LicenseStatus
│
└── utils/                 # Хелперы
    ├── paths.rs           # APPDATA_ROOT, CONFIG_DIR, FILE_ENV...
    ├── process.rs         # Управление процессами (Job Objects)
    └── windows.rs         # Windows API (detect_system_language)
```

## Структура Frontend (WebView)

> [!IMPORTANT] > **Frontend — только отображение!** Никакой бизнес-логики, валидации, или вычислений.
> Все данные приходят из Rust через `invoke()` или события.

```
src/
├── features/              # UI-модули (подписка на события + рендеринг)
│   ├── chat/              # UI чата (отправка → invoke, отображение ← events)
│   │   ├── chat.ts        # DOM-манипуляции, вызов invoke('send_message')
│   │   └── voice-input.ts # Голосовой ввод
│   ├── monitoring/        # Виджеты мониторинга (только updateUI)
│   │   └── monitoring.ts  # Подписка на 'system_stats', обновление DOM
│   ├── settings/          # UI настроек
│   ├── downloads/         # Progress bar загрузок
│   └── ...
│
├── shared/
│   ├── api/
│   │   └── tauri.ts       # Мост к Tauri (invoke, listen, mock для браузера)
│   ├── lib/
│   │   ├── events/        # Подписки на Tauri events
│   │   └── utils/         # DOM-утилиты, форматирование
│   └── types/             # TypeScript интерфейсы (зеркало models/)
│
├── styles/                # CSS (дизайн-система)
└── i18n.ts                # Загрузка переводов из Rust
```

### Что делает Frontend:

| Разрешено                           | Запрещено                            |
| ----------------------------------- | ------------------------------------ |
| ✅ Подписка на события Tauri        | ❌ Вычисления (форматы — исключение) |
| ✅ Обновление DOM                   | ❌ Валидация данных                  |
| ✅ Вызов `invoke()` команд          | ❌ Прямые HTTP-запросы               |
| ✅ Локальное форматирование (bytes) | ❌ Хранение состояния (кроме UI)     |

---

## Data Transfer Objects (DTO)

> Все данные между UI и backend передаются только через `models/`

| Правило                            | Пояснение                                    |
| ---------------------------------- | -------------------------------------------- |
| UI не получает внутренних структур | Сервисы возвращают DTO, не internal types    |
| Изменения в DTO = breaking change  | Версионируем при изменении API               |
| Ошибки через `IpcError`            | Структурированный формат `{ code, message }` |

---

## Error Model

```rust
pub enum AppError {
    Validation(String),      // Ошибка валидации входных данных
    NotFound(String),        // Ресурс не найден
    PermissionDenied(String), // Нет доступа / лицензия
    Config(String),          // Ошибка конфигурации
    External(String),        // Внешний сервис недоступен
    Internal(String),        // Внутренняя ошибка
}
```

**Правила:**

-   `services/` возвращают `Result<T, AppError>`
-   `commands/` мапят `AppError` → `IpcError` для UI
-   UI получает `{ code: "VALIDATION", message: "..." }`

---

## Шаблон команды (best practice)

### ❌ Плохо — логика в команде:

```rust
#[tauri::command]
pub fn do_something(id: String) -> Result<Data, String> {
    // 50+ строк бизнес-логики прямо здесь
    let data = /* сложные вычисления */;
    Ok(data)
}
```

### ✅ Хорошо — команда вызывает сервис:

```rust
// commands/example.rs
#[tauri::command]
pub fn do_something(id: String) -> Result<Data, String> {
    // 1. Валидация
    if id.is_empty() {
        return Err("id is required".to_string());
    }

    // 2. Вызов сервиса
    services::example::process(&id)
}

// services/example.rs
pub fn process(id: &str) -> Result<Data, String> {
    // Вся логика здесь
    // ...
}
```

---

## Модули (Lifecycle)

Каждый модуль поддерживает lifecycle:

| Фаза           | Описание                                |
| -------------- | --------------------------------------- |
| `init`         | Первичная инициализация при регистрации |
| `start`        | Запуск модуля                           |
| `stop`         | Graceful остановка                      |
| `dispose`      | Очистка при удалении                    |
| `health_check` | Проверка состояния                      |

### Манифест модуля (module.json):

```json
{
    "apiVersion": "1",
    "id": "flux-chat",
    "name": "Flux Chat",
    "version": "1.0.0",
    "entry": "main.exe",
    "dependencies": ["python-3.11"],
    "lifecycle": {
        "init": "scripts/init.ps1",
        "start": "start.bat",
        "stop": "stop.bat"
    }
}
```

> [!NOTE] > `apiVersion` используется для проверки совместимости.
> При изменении API модулей увеличивайте версию.

---

## Тестирование

| Слой          | Подход                                |
| ------------- | ------------------------------------- |
| **services/** | Unit-тесты (`#[cfg(test)]`)           |
| **commands/** | Не тестируются напрямую (тонкий слой) |
| **models/**   | Unit-тесты для валидации              |
| **Frontend**  | Ручное тестирование в dev режиме      |

```rust
// services/example.rs
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_process_valid_id() {
        let result = process("valid-id");
        assert!(result.is_ok());
    }
}
```

---

## IPC Команды

| Команда              | Сервис              | Описание                |
| -------------------- | ------------------- | ----------------------- |
| `get_system_stats`   | `system_monitor`    | CPU, RAM, Disk, Network |
| `get_gpu_info`       | `system`            | Детальная инфо о GPU    |
| `get_modules`        | `modules`           | Список модулей          |
| `control_module`     | `module_controller` | Start/stop/install      |
| `get_license_status` | `license`           | Статус лицензии         |
| `check_feature`      | `license`           | Проверка прав доступа   |
| `get_settings`       | `settings`          | Настройки пользователя  |
| `save_settings`      | `settings`          | Сохранение настроек     |
| `get_logs`           | `logs`              | Получение логов         |
| `start_download`     | `downloader`        | Скачивание файлов       |
| `minimize_window`    | `window`            | Управление окном        |
| `get_chat_history`   | `chat`              | История сообщений       |
| `save_chat_message`  | `chat`              | Сохранение сообщения    |
| `clear_chat_history` | `chat`              | Очистка истории         |
| `send_message`       | `chat`              | Отправка сообщения (AI) |

---

## События (Events)

Вместо polling UI подписывается на события:

| Событие             | Источник         | Данные                         |
| ------------------- | ---------------- | ------------------------------ |
| `system_stats`      | `system_monitor` | `SystemStats` (каждую секунду) |
| `download_progress` | `downloader`     | `{ id, progress, status }`     |

### Управление мониторингом

```rust
// Запуск мониторинга (вызывается в setup)
services::system_monitor::start_monitoring(app.handle().clone(), 1000);

// Остановка мониторинга (при закрытии приложения)
services::system_monitor::stop_monitoring();
```

### Правила именования

| Правило                     | Пример                              |
| --------------------------- | ----------------------------------- |
| События в `snake_case`      | `system_stats`, `download_progress` |
| Payload только из `models/` | Не internal structs                 |
| Event = публичный API       | Изменение = breaking change         |

```javascript
// Frontend подписка
import { listen } from "@tauri-apps/api/event";

const unlisten = await listen("system_stats", (event) => {
    updateUI(event.payload);
});
```

---

## Windows Specific Features

Flux Platform включает ряд оптимизаций для Windows:

1.  **System Tray**:

    -   Реализован через `TrayIconBuilder` c иконкой приложения.
    -   Контекстное меню: "Показать" (Show) и "Выход" (Quit).
    -   Двойной клик открывает главное окно.
    -   При выходе происходит корректная остановка мониторинга (`system_monitor::stop_monitoring`).

2.  **Language Detection**:

    -   Использует Win32 API (`GetUserDefaultUILanguage`) через crate `windows-sys`.
    -   Автоматически определяет язык системы при первом запуске (fallback на `en`).

3.  **Window Persistence**:
    -   Сохраняет состояние окна (размер, позиция, maximized) и уровень зума.
    -   Конфиг: `AppData/Roaming/.../window-settings.json`.
    -   Логика восстановления работает на старте приложения до показа окна.

---

## API Configuration

Конфигурация внешних API централизована в настройках:

| Параметр        | Файл                     | Описание                        |
| --------------- | ------------------------ | ------------------------------- |
| `API_BASE_URL`  | `Configs/.env`           | Базовый URL AI бэкенда (Python) |
| `llm_temp`, ... | `generation_config.json` | Параметры генерации (LLM, SD)   |

### Пример .env файла:

```ini
LANGUAGE=ru
THEME=dark
USE_GPU=true
DEBUG_MODE=false
API_BASE_URL=http://127.0.0.1:5000
```

> [!TIP]
> Изменение `API_BASE_URL` позволяет переключаться между локальным и удалённым AI сервером.

---

## Chat System

Чат использует **единый источник истории** — SQLite (`chat.db`).

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Frontend      │─────►│   Tauri IPC     │─────►│  Python AI API  │
│   (chat.ts)     │      │   (chat.rs)     │      │   (Flask/FastAPI)│
└────────┬────────┘      └────────┬────────┘      └─────────────────┘
         │                        │
         │                        ▼
         │               ┌─────────────────┐
         └──────────────►│   SQLite DB     │
            get_history  │   (chat.db)     │
                         └─────────────────┘
```

**Команды:**

-   `send_message` — сохраняет user + assistant сообщения автоматически
-   `get_chat_history` — возвращает N последних сообщений
-   `clear_chat_history` — очищает всю историю
