# Flux Platform API Reference

Полный справочник IPC команд и событий.

---

## IPC Команды (Tauri Commands)

### Настройки

| Команда                | Параметры               | Возврат            | Описание                     |
| ---------------------- | ----------------------- | ------------------ | ---------------------------- |
| **Health**             |                         |                    |                              |
| `get_health`           | —                       | `HealthStatus`     | Проверка состояния бэкенда   |
| **Settings**           |                         |                    |                              |
| `get_settings`         | —                       | `AppSettings`      | Загрузить настройки          |
| `save_settings`        | `settings: AppSettings` | `()`               | Сохранить настройки          |
| `get_system_language`  | —                       | `String`           | Определение языка системы    |
| **Logs**               |                         |                    |                              |
| `get_logs`             | —                       | `Vec<LogEntry>`    | Получить логи                |
| `clear_logs`           | —                       | `()`               | Очистить логи                |
| `add_log`              | `level, message`        | `()`               | Добавить лог из фронтенда    |
| **System**             |                         |                    |                              |
| `get_system_stats`     | —                       | `SystemStats`      | CPU/RAM/Network utilization  |
| `get_gpu_info`         | —                       | `GpuInfo`          | Детальная инфо о GPU         |
| **Modules**            |                         |                    |                              |
| `get_modules`          | —                       | `Vec<Module>`      | Список доступных модулей     |
| `control_module`       | `id, action`            | `Result`           | Start/Stop/Install модуля    |
| **Window**             |                         |                    |                              |
| `minimize_window`      | —                       | `()`               | Свернуть окно                |
| `maximize_window`      | —                       | `()`               | Развернуть/восстановить      |
| `close_window`         | —                       | `()`               | Закрыть приложение/в трей    |
| **Window Settings**    |                         |                    |                              |
| `get_window_settings`  | —                       | `WindowSettings`   | Загрузить состояние окна     |
| `save_window_size`     | `width, height`         | `()`               | Сохранить размер             |
| `save_window_position` | `x, y`                  | `()`               | Сохранить позицию            |
| `save_maximized_state` | `maximized: bool`       | `()`               | Сохранить статус разворота   |
| `save_zoom_level`      | `level: f64`            | `()`               | Сохранить масштаб интерфейса |
| **Theme & i18n**       |                         |                    |                              |
| `get_theme_colors`     | —                       | `ThemeColors`      | Цвета из системной темы      |
| `get_translations`     | `lang`                  | `Value`            | Загрузить переводы           |
| **Downloader**         |                         |                    |                              |
| `start_download`       | `url, path`             | `download_id`      | Начать загрузку              |
| `cancel_download`      | `id`                    | `()`               | Отменить загрузку            |
| **License**            |                         |                    |                              |
| `get_license_status`   | —                       | `LicenseStatus`    | Текущая лицензия             |
| `activate_license`     | `key`                   | `Result`           | Активация ключа              |
| `deactivate_license`   | —                       | `Result`           | Деактивация                  |
| `check_feature`        | `feature`               | `bool`             | Проверка доступа к функции   |
| **Chat**               |                         |                    |                              |
| `save_chat_message`    | `message`               | `id`               | Сохранить в БД               |
| `get_chat_history`     | `limit, offset`         | `Vec<ChatMessage>` | Получить историю             |
| `clear_chat_history`   | —                       | `()`               | Удалить всю переписку        |
| `send_message`         | `message`               | `Stream`           | Отправить AI агенту          |

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

## Типы данных (Type Definitions)

### System & Monitoring

```typescript
interface SystemStats {
    cpu: CpuStats;
    ram: RamStats;
    gpu: GpuStats | null;
    vram: VramStats | null;
    disk: DiskStats;
    network: NetworkStats;
    pid: number;
}

interface CpuStats {
    percent: number;
    cores: number;
    name: string;
}

interface RamStats {
    percent: number;
    used_gb: number;
    total_gb: number;
    available_gb: number;
}

interface GpuStats {
    usage: number;
    memory_used: number;
    memory_total: number;
    temp: number;
    name: string;
}

interface VramStats {
    percent: number;
    used_gb: number;
    total_gb: number;
}

interface DiskStats {
    read_rate: number; // MB/s
    write_rate: number; // MB/s
    utilization: number; // %
    total_gb: number;
    used_gb: number;
}

interface NetworkStats {
    download_rate: number; // KB/s
    upload_rate: number; // KB/s
    total_received: number; // Bytes
    total_sent: number; // Bytes
    utilization: number; // %
}
```

### Settings & Window

```typescript
interface AppSettings {
    theme: string; // Default: "dark"
    language: string; // Default: "ru"
    use_gpu: boolean; // Default: true
    debug_mode: boolean; // Default: false
    api_base_url: string; // Default: "http://127.0.0.1:5000"
}

interface WindowSettings {
    width: number; // Default: 1600
    height: number; // Default: 1000
    x: number | null;
    y: number | null;
    maximized: boolean;
    zoom_level: number; // Default: 1.0
}
```

### Chat & AI

```typescript
interface ChatMessage {
    id: number | null;
    role: "user" | "assistant";
    content: string;
    timestamp: number; // Unix timestamp
}

interface ChatApiResponse {
    ok: boolean;
    reply: ChatApiReply | null;
    error: string | null;
}

interface ChatApiReply {
    text: string | null;
    type: string | null;
    images: string[] | null; // Base64 strings
}
```

### Modules

```typescript
interface ModuleItem {
    id: string;
    name: string | null;
    version: string | null;
    description: string | null;
    type: string | null;
    kind: string | null;
    status: string | null;
    installed: boolean | null;
    icon: string | null;
    removable: boolean | null;
    recommended: boolean | null;
    repo: string | null;
    custom: boolean | null;
}

interface ControlResponse {
    success: boolean;
    message: string;
    status: string | null;
}
```

### License

```typescript
type LicenseStatus = "Free" | "Pro" | "Enterprise" | "Expired" | "Invalid";

interface LicenseStatusResponse {
    status: LicenseStatus;
    email: string | null;
}
```

---

## Использование во Frontend

```typescript
import { invoke } from "@core/api/tauri";

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

Результат: `src/types/generated.ts`
