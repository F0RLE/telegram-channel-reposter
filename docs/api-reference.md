# Flux Platform API Reference

Полный справочник IPC команд и событий.

---

## IPC Команды (Tauri Commands)

### Настройки

| Команда           | Параметры               | Возврат       | Описание                         |
| ----------------- | ----------------------- | ------------- | -------------------------------- |
| `get_settings`    | —                       | `AppSettings` | Загрузить настройки из .env      |
| `save_settings`   | `settings: AppSettings` | `()`          | Сохранить настройки в .env       |
| `get_gen_config`  | —                       | `Value`       | Загрузить generation_config.json |
| `save_gen_config` | `config: Value`         | `()`          | Сохранить generation_config.json |

### Чат

| Команда              | Параметры                          | Возврат            | Описание                         |
| -------------------- | ---------------------------------- | ------------------ | -------------------------------- |
| `send_message`       | `text, mode, attachments, history` | `ChatApiResponse`  | Отправить сообщение через AI API |
| `get_chat_history`   | `limit: i32`                       | `Vec<ChatMessage>` | Получить историю из SQLite       |
| `save_chat_message`  | `role, content`                    | `i64` (id)         | Сохранить сообщение              |
| `clear_chat_history` | —                                  | `()`               | Очистить историю                 |

### Мониторинг

| Команда            | Параметры          | Возврат       | Описание                          |
| ------------------ | ------------------ | ------------- | --------------------------------- |
| `get_system_stats` | —                  | `SystemStats` | Получить CPU/RAM/GPU/Disk/Network |
| `start_monitoring` | `interval_ms: u64` | `()`          | Запустить поток мониторинга       |
| `stop_monitoring`  | —                  | `()`          | Остановить мониторинг             |

### Модули

| Команда             | Параметры           | Возврат        | Описание                  |
| ------------------- | ------------------- | -------------- | ------------------------- |
| `control_module`    | `module_id, action` | `Result`       | start/stop/install модуля |
| `get_module_status` | `module_id`         | `ModuleStatus` | Статус модуля             |

### Загрузки

| Команда           | Параметры       | Возврат       | Описание          |
| ----------------- | --------------- | ------------- | ----------------- |
| `start_download`  | `url, filename` | `download_id` | Начать загрузку   |
| `cancel_download` | `download_id`   | `()`          | Отменить загрузку |

### Лицензирование

| Команда              | Параметры         | Возврат         | Описание            |
| -------------------- | ----------------- | --------------- | ------------------- |
| `get_license_status` | —                 | `LicenseStatus` | Free/Pro/Enterprise |
| `activate_license`   | `key: String`     | `Result`        | Активировать ключ   |
| `check_feature`      | `feature: String` | `bool`          | Доступ к фиче       |

---

## Tauri События (Events)

### Мониторинг

```typescript
// Подписка на system_stats
import { listen } from "@tauri-apps/api/event";

const unlisten = await listen<SystemStats>("system_stats", (event) => {
    console.log("CPU:", event.payload.cpu.percent);
});
```

| Событие                 | Payload            | Частота     | Описание                     |
| ----------------------- | ------------------ | ----------- | ---------------------------- |
| `system_stats`          | `SystemStats`      | 1/сек       | CPU, RAM, GPU, Disk, Network |
| `download_progress`     | `DownloadProgress` | динамически | Прогресс загрузки            |
| `module_status_changed` | `ModuleStatus`     | по событию  | Изменение статуса модуля     |

---

## Типы данных

### SystemStats

```typescript
interface SystemStats {
    cpu: { percent: number; cores: number; name: string };
    ram: {
        percent: number;
        used_gb: number;
        total_gb: number;
        available_gb: number;
    };
    gpu: {
        usage: number;
        memory_used: number;
        memory_total: number;
        temp: number;
        name: string;
    } | null;
    vram: { percent: number; used_gb: number; total_gb: number } | null;
    disk: {
        read_rate: number;
        write_rate: number;
        utilization: number;
        total_gb: number;
        used_gb: number;
    };
    network: {
        download_rate: number;
        upload_rate: number;
        total_received: number;
        total_sent: number;
    };
    pid: number;
}
```

### AppSettings

```typescript
interface AppSettings {
    theme: string; // "dark" | "light"
    language: string; // "ru" | "en" | "zh"
    use_gpu: boolean;
    debug_mode: boolean;
    api_base_url: string; // "http://127.0.0.1:5000"
}
```

### ChatMessage

```typescript
interface ChatMessage {
    id: number | null;
    role: string; // "user" | "assistant"
    content: string;
    timestamp: number;
}
```

---

## Использование во Frontend

```typescript
import { invoke } from "@shared/api/tauri";

// Получить настройки
const settings = await invoke<AppSettings>("get_settings");

// Отправить сообщение
const response = await invoke<ChatApiResponse>("send_message", {
    text: "Привет!",
    mode: "chat",
    attachments: [],
    history: [],
});

// Подписка на мониторинг
import { listen } from "@tauri-apps/api/event";
await listen("system_stats", (e) => updateUI(e.payload));
```

---

## Генерация типов

TypeScript типы генерируются из Rust моделей:

```powershell
cd src-tauri
cargo run --bin export-types
```

Результат: `src/shared/types/generated.ts`
