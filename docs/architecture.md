# Flux Platform — Архитектура

> [!IMPORTANT]
> Этот документ является архитектурной спецификацией.
> Изменения в нём требуют осознанного решения и ревью.

## Обзор

Flux Platform — десктопное приложение на **Tauri v2** + **Rust** + **Vite**.

```
┌─────────────────────────────────────────────────────────────┐
│                        Tauri Shell                          │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐    ┌─────────────────────────────┐ │
│  │    WebView (UI)     │◄──►│      Rust Backend           │ │
│  │                     │ IPC│                             │ │
│  │  - HTML/CSS/TypeScript│    │  - src/services/ (логика)   │ │
│  │  - Подписки events  │    │  - src/commands/ (IPC слой) │ │
│  │  - Нет вычислений   │    │  - Вся бизнес-логика        │ │
│  └─────────────────────┘    └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
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

## Структура Backend

```
src-tauri/src/
├── commands/              # IPC слой (тонкий!)
│   ├── mod.rs
│   ├── system.rs          # get_system_stats, get_gpu_info
│   ├── modules.rs         # get_modules, control_module
│   ├── settings.rs        # get_settings, save_settings
│   ├── license.rs         # get_license_status, activate_license
│   ├── window_settings.rs # get_window_settings, save_window_size, save_zoom_level
│   └── ...
│
├── services/              # Бизнес-логика
│   ├── mod.rs
│   ├── system_monitor.rs  # Мониторинг + события
│   ├── modules.rs         # Реестр модулей
│   ├── module_controller.rs # Управление модулями
│   ├── module_lifecycle.rs  # Trait для плагинов
│   ├── window_settings.rs # Сохранение размера/позиции окна
│   ├── license/           # Лицензирование
│   │   ├── types.rs
│   │   ├── verifier.rs
│   │   └── storage.rs
│   └── ...
│
├── models/                # DTO (Data Transfer Objects)
└── utils/                 # Хелперы
    ├── paths.rs           # Пути к файлам конфигурации
    ├── process.rs         # Управление процессами
    └── windows.rs         # Windows API (язык системы)
```

## Structure Frontend

```
src/
├── assets/                # Статические ресурсы (изображения, шрифты)
├── features/              # Функциональные модули
│   ├── chat/              # Логика чата
│   ├── monitoring/        # Виджеты мониторинга
│   └── ...
├── shared/                # Общий код
│   ├── components/        # UI компоненты (Sidebar, Particles)
│   ├── lib/               # Утилиты (events, sound)
│   └── types/             # TypeScript интерфейсы
├── styles/                # Глобальные и модульные стили
└── i18n.ts                # Конфигурация локализации
```

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
