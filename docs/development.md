# Flux Platform — Руководство разработчика

## Требования

| Компонент | Версия               |
| --------- | -------------------- |
| Rust      | 1.70+                |
| Node.js   | 18+                  |
| Windows   | 10/11 (64-bit)       |
| MSYS2     | Для сборки (MinGW64) |

---

## Быстрый старт

```powershell
# 1. Клонирование
git clone https://github.com/F0RLE/flux-platform.git
cd flux-platform

# 2. Установка зависимостей и запуск
cd scripts
./dev.ps1
```

Dev сервер Vite: `http://localhost:1420`

---

## Скрипты

| Скрипт                | Описание                         |
| --------------------- | -------------------------------- |
| `./scripts/dev.ps1`   | Dev режим с Vite hot-reload      |
| `./scripts/build.ps1` | Production сборка + installer    |
| `./scripts/clean.ps1` | Очистка target/, dist/, release/ |

---

## Структура проекта

```
├── src-tauri/             # Rust Backend (ВСЯ БИЗНЕС-ЛОГИКА)
│   ├── src/
│   │   ├── lib.rs        # Точка входа, регистрация команд
│   │   ├── commands/     # IPC слой (тонкий!) — валидация → services/
│   │   ├── services/     # Вся логика:
│   │   │   ├── system_monitor.rs  # Мониторинг + Tauri events
│   │   │   ├── chat.rs            # SQLite история + Python AI API
│   │   │   ├── downloader.rs      # Async загрузка с прогрессом
│   │   │   ├── settings.rs        # Чтение/запись .env
│   │   │   ├── module_controller.rs
│   │   │   ├── license/           # Лицензирование
│   │   │   └── ...
│   │   ├── models/       # DTO (AppSettings, SystemStats...)
│   │   └── utils/        # paths.rs, process.rs, windows.rs
│   └── tauri.conf.json
│
├── src/                   # WebView (ТОЛЬКО UI!)
│   ├── features/          # UI-модули (подписка на events + рендеринг)
│   │   ├── chat/         # chat.ts (вызов invoke, обновление DOM)
│   │   ├── monitoring/   # monitoring.ts (подписка на system_stats)
│   │   └── ...
│   ├── shared/
│   │   ├── api/tauri.ts  # Мост к Tauri (invoke, listen)
│   │   ├── lib/events/   # Подписки на Tauri events
│   │   └── types/        # TypeScript интерфейсы
│   ├── styles/            # CSS
│   └── i18n.ts
│
└── scripts/               # Build скрипты
```

> **Важно:** Frontend не содержит бизнес-логики. Все вычисления, валидация, HTTP-запросы — в Rust.

---

## Добавление новой команды

### 1. Создать сервис (services/)

```rust
// services/example.rs
pub fn do_work(param: &str) -> Result<String, String> {
    // Вся бизнес-логика здесь
    if param.is_empty() {
        return Err("param cannot be empty".to_string());
    }
    Ok(format!("Processed: {}", param))
}
```

### 2. Создать команду (commands/)

```rust
// commands/example.rs
use crate::services::example;

#[tauri::command]
pub fn my_command(param: String) -> Result<String, String> {
    // Только валидация + вызов сервиса
    example::do_work(&param)
}
```

### 3. Зарегистрировать в lib.rs

```rust
.invoke_handler(tauri::generate_handler![
    // ...
    example::my_command,
])
```

### 4. Добавить модуль

```rust
// commands/mod.rs
pub mod example;

// services/mod.rs
pub mod example;
```

### 5. Вызвать из TypeScript

```typescript
import { invoke } from "@shared/api/tauri";

const result = await invoke<string>("my_command", { param: "test" });
```

---

## Основные команды (IPC)

| Команда              | Сервис              | Описание                        |
| -------------------- | ------------------- | ------------------------------- |
| `get_system_stats`   | `system_monitor`    | CPU/RAM/GPU/Disk/Network        |
| `get_settings`       | `settings`          | Настройки (тема, язык, API URL) |
| `save_settings`      | `settings`          | Сохранение в .env               |
| `get_chat_history`   | `chat`              | История из SQLite               |
| `send_message`       | `chat`              | Отправка сообщения через AI API |
| `clear_chat_history` | `chat`              | Очистка истории                 |
| `start_download`     | `downloader`        | Загрузка файла                  |
| `get_license_status` | `license`           | Статус лицензии                 |
| `control_module`     | `module_controller` | start/stop/install              |

---

## Подписка на события

Вместо polling используй события:

```typescript
// src/shared/lib/events/system.ts
import { listen } from "@tauri-apps/api/event";
import type { SystemStats } from "../types"; // Пример

export async function subscribeToSystemStats(
    callback: (stats: SystemStats) => void
) {
    return await listen<SystemStats>("system_stats", (event) => {
        callback(event.payload);
    });
}

// Использование (например, в features/monitoring/monitoring.ts)
import { subscribeToSystemStats } from "@shared/lib/events/system";

const unsub = await subscribeToSystemStats((stats) => {
    console.log("CPU:", stats.cpu.percent);
});

// При выходе (cleanup)
unsub();
```

---

## Локализация

Файлы: см. `src/i18n.ts` и `src-tauri/src/services/translations.rs` (если есть).
В текущей версии локализация управляется через `src/i18n.ts` (Frontend) или системные настройки.

| Файл      | Язык    |
| --------- | ------- |
| `en.json` | English |
| `ru.json` | Русский |
| `zh.json` | 中文    |

### Добавление перевода

1. Добавить ключ во все JSON
2. В HTML: `data-i18n="key.path"`
3. В TypeScript: `i18n.t('key.path')`

---

## Лицензирование

```typescript
// Проверка статуса
const status = await invoke("get_license_status");
// { status: "Free" | "Pro" | "Enterprise", email: null }

// Проверка фичи
const canUse = await invoke("check_feature", { feature: "advanced_chat" });
```

Ключи форматы:

-   `PRO-XXXX-XXXX` → Pro tier
-   `ENT-XXXX-XXXX` → Enterprise tier

---

## Отладка

### Rust логи

```rust
log::info!("Debug message");
log::warn!("Warning");
log::error!("Error!");
```

### DevTools

`F12` в dev режиме для WebView DevTools.

### dlltool ошибка

Если видите `dlltool.exe not found`:

```powershell
$env:PATH = "C:\msys64\mingw64\bin;$env:PATH"
cargo build
```

Или используйте `./scripts/dev.ps1` — там PATH уже настроен.

---

## Сборка

```powershell
./scripts/build.ps1
```

Результат:

-   `release/FluxPlatform.exe`
-   `release/dist/*.msi`
-   `release/dist/*.exe` (NSIS installer)

---

## Автогенерация типов (Rust → TypeScript)

Проект использует **specta** для генерации TypeScript интерфейсов из Rust моделей.

### Добавление нового типа

1. Добавить `specta::Type` derive к struct:

```rust
use specta::Type;

#[derive(Debug, Serialize, Type)]
pub struct MyNewType {
    pub field: String,
}
```

2. Обновить `src/bin/export_types.rs`:

```rust
use flux_platform_lib::models::MyNewType;
// ...добавить в tuple типов
```

3. Запустить генерацию:

```powershell
cd src-tauri
cargo run --bin export-types
```

Результат: `src/shared/types/generated.ts`

### Типы с поддержкой specta

| Модуль        | Типы                                                    |
| ------------- | ------------------------------------------------------- |
| `system.rs`   | `SystemStats`, `CpuStats`, `RamStats`, `GpuStats`, etc. |
| `settings.rs` | `AppSettings`                                           |
| `chat.rs`     | `ChatMessage`, `ChatApiResponse`, `ChatApiReply`        |
