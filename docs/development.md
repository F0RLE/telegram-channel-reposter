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
├── src-tauri/             # Rust + Tauri
│   ├── src/
│   │   ├── commands/      # IPC слой (тонкий!)
│   │   ├── services/      # Бизнес-логика
│   │   ├── models/        # DTO (Data Transfer Objects)
│   │   └── utils/         # Хелперы
│   └── tauri.conf.json
│
├── src/                   # Vite + TypeScript
│   ├── assets/            # Статические ресурсы
│   ├── features/          # Функциональные модули (chat, monitoring, etc.)
│   ├── pages/             # Компоненты страниц
│   ├── shared/            # Общие компоненты и утилиты
│   ├── styles/            # CSS стили
│   ├── i18n.ts            # Локализация
│   ├── index.html         # Точка входа
│   └── vite.config.ts
│
└── scripts/               # Build скрипты
```

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
const result = await window.__TAURI__.invoke("my_command", {
    param: "test",
});
```

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
