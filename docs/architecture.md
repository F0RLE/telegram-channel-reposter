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
│  │  • Подписки events  │    │  │  commands/  │  │     domain/     │   │ │
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

### Core Plugins (lib.rs)

-   **shell**: Открытие ссылок, запуск процессов.
-   **notification**: Системные уведомления.
-   **global-shortcut**: Глобальные хоткеи (Ctrl+Space).
-   **dialog**: Нативные диалоги (открытие файлов).
-   **single-instance**: Запрет запуска второй копии.

---

---

## Архитектурные принципы

> Эти правила предотвращают архитектурный дрейф со временем.

| Правило                                 | Пояснение                                                                  |
| --------------------------------------- | -------------------------------------------------------------------------- |
| **Вся бизнес-логика — только в Rust**   | Frontend: только UX-валидация (required, length). Backend: бизнес-правила. |
| **IPC команды — тонкий слой**           | `commands/` только валидирует и вызывает `domain/`                         |
| **domain/ не знают о Tauri**            | Доменная логика изолирована (за исключением `AppHandle` для events)        |
| **Нет глобального состояния**           | `domain/` не используют глобальное состояние без явной инициализации       |
| **UI не знает о внутреннем устройстве** | Frontend получает готовые данные, не детали реализации                     |
| **Event-driven где возможно**           | System monitor использует события, а не polling                            |

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
├── bin/                   # Вспомогательные бинарники (export-types)
├── commands/              # IPC слой — валидация → вызов domain/
│   ├── health.rs
│   ├── system.rs
│   ├── modules.rs
│   ├── settings.rs
│   ├── license.rs
│   └── ...
│
├── domain/                # ВСЯ БИЗНЕС-ЛОГИКА (Domain-Driven Design)
│   ├── chat/              # Пример домена
│   │   ├── mod.rs
│   │   ├── models.rs      # DTO и типы данных
│   │   └── service.rs     # Логика
│   ├── monitoring/
│   ├── settings/
│   ├── modules/
│   ├── license/
│   └── ...
│
├── utils/                 # Общие утилиты
│   ├── paths.rs
│   ├── process.rs
│   └── windows.rs
│
├── errors.rs              # AppError и IpcError (Централизованная обработка ошибок)
├── lib.rs                 # Точка входа библиотеки (Tauri Builder)
└── main.rs                # Точка входа бинарника
```

## Структура Frontend (WebView)

> [!IMPORTANT] > **Frontend — только отображение!** Никакой бизнес-логики, валидации, или вычислений.
> Все данные приходят из Rust через `invoke()` или события.

```
src/
├── core/                  # Ядро приложения
│   ├── api/               # Tauri bridge & mocks
│   ├── app/               # Lifecycle & init
│   ├── events/            # Global event bus
│   ├── i18n/              # Локализация
│   ├── state/             # Global Store (Signals)
│   └── utils/             # Helpers
│
├── features/              # UI-модули (подписка на события + рендеринг)
│   ├── chat/              # Логика и UI чата
│   ├── monitoring/        # Виджеты мониторинга
│   ├── settings/          # Экраны настроек
│   ├── downloads/         # Менеджер загрузок
│   └── ...
│
├── pages/                 # Страницы (Routing)
├── styles/                # CSS (дизайн-система)
├── types/                 # Global Types (DTO)
├── assets/                # Static files
└── index.html             # Entry point
```

### Слои Frontend:

1.  **Core**: Базовая инфраструктура (API, Events, State, i18n). Не зависит от UI.
2.  **Features**: Самодостаточные модули функциональности.
3.  **Pages**: Компоновка фич в страницы.
4.  **UI/Styles**: Визуальный слой.

---

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

-   `domain/` возвращают `Result<T, AppError>`
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

    // 2. Вызов доменной логики
    domain::example::process(&id)
}

// domain/example.rs
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
| **domain/**   | Unit-тесты (`#[cfg(test)]`)           |
| **commands/** | Не тестируются напрямую (тонкий слой) |
| **models/**   | Unit-тесты для валидации              |
| **Frontend**  | Ручное тестирование в dev режиме      |

```rust
// domain/example.rs
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

| Команда                | Группа            | Описание                      |
| ---------------------- | ----------------- | ----------------------------- |
| **System**             |                   |                               |
| `get_health`           | `health`          | Проверка здоровья бэкенда     |
| `get_system_stats`     | `system`          | CPU, RAM, Disk, Network       |
| `get_gpu_info`         | `system`          | Детальная инфо о GPU          |
| `get_system_language`  | `settings`        | Язык системы (Auto-detect)    |
| **Modules**            |                   |                               |
| `get_modules`          | `modules`         | Список модулей                |
| `control_module`       | `modules`         | Lifecycle: Start/stop/install |
| **Settings**           |                   |                               |
| `get_settings`         | `settings`        | Настройки приложения          |
| `save_settings`        | `settings`        | Сохранение настроек           |
| `get_theme_colors`     | `theme`           | Цветовая палитра              |
| **Window**             |                   |                               |
| `minimize_window`      | `window`          | Свернуть окно                 |
| `maximize_window`      | `window`          | Развернуть/восстановить       |
| `close_window`         | `window`          | Скрыть в трей / закрыть       |
| `get_window_settings`  | `window_settings` | Размер, позиция, зум          |
| `save_window_size`     | `window_settings` | Сохранение размера            |
| `save_window_position` | `window_settings` | Сохранение позиции            |
| `save_maximized_state` | `window_settings` | Сохранение состояния          |
| `save_zoom_level`      | `window_settings` | Сохранение масштаба           |
| **Features**           |                   |                               |
| `get_license_status`   | `license`         | Статус лицензии               |
| `activate_license`     | `license`         | Активация ключа               |
| `deactivate_license`   | `license`         | Сброс привязки                |
| `check_feature`        | `license`         | Проверка прав доступа         |
| `start_download`       | `downloader`      | Скачивание файлов             |
| `cancel_download`      | `downloader`      | Отмена загрузки               |
| **Logs**               |                   |                               |
| `get_logs`             | `logs`            | Получение буфера логов        |
| `add_log`              | `logs`            | Запись лога с фронта          |
| `clear_logs`           | `logs`            | Очистка логов                 |
| **Chat**               |                   |                               |
| `get_chat_history`     | `chat`            | История сообщений             |
| `save_chat_message`    | `chat`            | Сохранение сообщения          |
| `clear_chat_history`   | `chat`            | Очистка истории               |
| `send_message`         | `chat`            | Отправка сообщения (AI)       |
| `get_translations`     | `translations`    | i18n строки                   |

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
domain::monitoring::start_monitoring(app.handle().clone(), 1000);

// Остановка мониторинга (при закрытии приложения)
domain::monitoring::stop_monitoring();
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

---

## Evolution & Roadmap (Vision)

Архитектура проекта эволюционирует в сторону **Hexagonal Architecture (Ports and Adapters)**.

### 1. Изоляция домена (Ports)

Текущее внедрение `AppHandle` в домен — прагматичный компромисс.
**Цель:** Полная отвязка `domain/` от `tauri`.

```rust
// Вместо прямого использования Tauri events:
trait EventPublisher {
    fn publish(&self, event: DomainEvent);
}

// Реализация в infrastructure layer:
struct TauriEventPublisher { app: AppHandle }
```

### 2. Inference Layer

Текущая схема `IPC -> HTTP -> Python` является временным решением для быстрого прототипирования.
**Цель:** Переход на **In-Process Inference** (Rust bindings для `llama.cpp` / `rwkv`).

### 3. IPC Versioning

По мере роста API будет введено явное версионирование:

-   DTO суффиксы: `ChatMessageV1`, `ChatMessageV2`
-   Команда: `invoke("chat.send_message_v2")`

### 4. Enterprise Quality

-   **Diagnostics**: `get_health` превратится в полноценный `Self-Diagnostic Report`.
-   **Observability**: Структурированные логи и метрики производительности.
