<div align="center">

# Flux Platform

[![Rust](https://img.shields.io/badge/Rust-1.70+-orange.svg?style=flat-square&logo=rust)](https://www.rust-lang.org/)
[![Tauri](https://img.shields.io/badge/Tauri-v2-blue.svg?style=flat-square&logo=tauri)](https://tauri.app/)
[![Vite](https://img.shields.io/badge/Vite-v6-purple.svg?style=flat-square&logo=vite)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg?style=flat-square&logo=windows)](https://www.microsoft.com/windows)

<br/>

[![English](https://img.shields.io/badge/-English-grey?style=for-the-badge&logo=usb&logoColor=white&labelColor=002060)](#english) &nbsp;
[![Русский](https://img.shields.io/badge/-Русский-grey?style=for-the-badge&logo=usb&logoColor=white&labelColor=blue)](#russian) &nbsp;
[![中文](https://img.shields.io/badge/-中文-grey?style=for-the-badge&logo=usb&logoColor=white&labelColor=red)](#chinese)

</div>

---

<a name="english"></a>

## <img src="https://flagcdn.com/24x18/gb.png" valign="middle"> English

**Flux Platform** is a modular service management platform designed for high performance, predictability, and extensibility. Built upon the **Rust** ecosystem and **Tauri v2**, it bridges the gap between native system execution and modern interfaces.

The platform was designed with enterprise requirements in mind: strict process isolation, access control, and stable resource usage. Unlike Electron-based alternatives, Flux Platform leverages the native WebView2, resulting in a significantly smaller binary size and reduced memory footprint.

### Core Architecture

-   **Rust Backend**: Business logic is implemented in pure Rust, ensuring memory safety and thread safety without Garbage Collection overhead.
-   **Tauri v2 IPC**: Utilizes an optimized asynchronous Inter-Process Communication bridge for low-latency state synchronization.
-   **Zero-Overhead Abstractions**: Critical services (LicenseVerifier, SystemMonitor) execute on isolated threads to prevent UI blocking.
-   **Modular Design**: The core architecture was designed from the ground up to support a modular service lifecycle and strict component isolation.

### Monitoring System

The platform implements a proprietary telemetry engine for real-time analysis:

-   **CPU**: Per-core load tracking and process-level heuristics.
-   **Memory**: Detailed breakdown of physical (RAM) and video (VRAM) memory allocation.
-   **GPU**: Real-time utilization metrics via direct NVML integration for NVIDIA hardware.
-   **I/O**: Throughput analysis for disk and network interfaces.

### Performance & Frontend

-   **Vite Architecture**: Instant Hot Module Replacement (HMR) and optimized asset bundling.
-   **Vanilla TypeScript**: The core dashboard avoids heavy frameworks (React/Vue) to minimize initialization time and runtime overhead.
-   **Custom Design System**: Bespoke CSS architecture ensures consistent rendering and efficient updates.

### Security

-   **Path Traversal Protection**: Filesystem operations are strictly sandboxed and validated against allowlists.
-   **Input Sanitization**: Strict typing and sanitization for all IPC payloads.
-   **Secure Storage**: Sensitive configuration data is encrypted using the operating system's native key storage mechanisms.

### Stack

-   **Backend**: Rust (Tokio, Serde, Tauri, Sysinfo, NVML-Wrapper)
-   **Frontend**: TypeScript, Vite, CSS
-   **Build**: Cargo, NPM, PowerShell Automation
-   **Installer**: WiX Toolset (MSI), NSIS (EXE)

### Quick Start (Development)

**Prerequisites:**

-   Windows 10/11 (x64 Build 19041+)
-   [Rust](https://rustup.rs/) (Stable 1.70+)
-   [Node.js](https://nodejs.org/) (LTS v18+)
-   [Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

```powershell
# 1. Clone repository
git clone https://github.com/F0RLE/flux-platform.git
cd flux-platform

# 2. Initialize environment
cd scripts
./dev.ps1
```

The `./dev.ps1` script automates dependency checks, compilation, and debug launch.

---

<a name="russian"></a>

## <img src="https://flagcdn.com/24x18/ru.png" valign="middle"> Русский

**Flux Platform** — модульная десктопная платформа для управления сервисами, ориентированная на высокую производительность, предсказуемость и расширяемость. Платформа построена на экосистеме **Rust** и фреймворке **Tauri v2**, сочетая нативный системный код с современным веб-интерфейсом.

Платформа проектировалась с учётом требований корпоративной эксплуатации: изоляция процессов, контроль доступа и стабильное поведение под нагрузкой. Использование нативного WebView2 позволяет достичь значительно меньшего размера приложения и потребления памяти по сравнению с аналогами на Electron.

### Архитектура ядра

-   **Бэкенд на Rust**: Бизнес-логика реализована на Rust, что гарантирует безопасность памяти и отсутствие пауз на сборку мусора (GC).
-   **Tauri v2 IPC**: Используется оптимизированный асинхронный мост для обмена данными между UI и ядром с минимальными задержками.
-   **Изоляция потоков**: Критические сервисы (мониторинг, проверка лицензий) работают в независимых потоках, не блокируя основной цикл приложения.
-   **Модульный дизайн**: Архитектура ядра изначально проектировалась с поддержкой модульного жизненного цикла сервисов и строгой изоляции компонентов.

### Система мониторинга

Собственный движок телеметрии обеспечивает анализ в реальном времени:

-   **CPU**: Отслеживание нагрузки по ядрам и анализ процессов.
-   **Память**: Детальная статистика по RAM и VRAM (доступно/использовано/кэш).
-   **GPU**: Прямая интеграция с NVML для получения метрик видеокарт NVIDIA.
-   **I/O**: Мониторинг пропускной способности дисков и сетевых адаптеров.

### Производительность и Фронтенд

-   **Архитектура Vite**: Мгновенный HMR и оптимизированная сборка ассетов.
-   **Vanilla TypeScript**: Отказ от тяжелых фреймворков в ядре дашборда минимизирует время инициализации.
-   **Дизайн-система**: Уникальная CSS-архитектура для стабильного рендеринга и плавных анимаций.

### Безопасность

-   **Защита FS**: Операции с файловой системой проходят через "песочницу" и валидацию списков доступа.
-   **Санитизация ввода**: Строгая типизация всех данных, передаваемых через IPC.
-   **Безопасное хранение**: Шифрование чувствительных данных с использованием системных хранилищ ключей (Windows DPAPI/Credential Locker).

### Стек технологий

-   **Backend**: Rust (Tokio, Serde, Tauri, Sysinfo, NVML-Wrapper)
-   **Frontend**: TypeScript, Vite, CSS
-   **Build**: Cargo, NPM, PowerShell Automation
-   **Installer**: WiX Toolset (MSI), NSIS (EXE)

### Запуск (Development)

**Требования:**

-   Windows 10/11 (x64 версия 19041+)
-   [Rust](https://rustup.rs/) (Stable 1.70+)
-   [Node.js](https://nodejs.org/) (LTS v18+)
-   [Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

```powershell
# 1. Клонирование
git clone https://github.com/F0RLE/flux-platform.git
cd flux-platform

# 2. Инициализация
cd scripts
./dev.ps1
```

Скрипт `./dev.ps1` выполняет проверку окружения, установку зависимостей и сборку проекта.

---

<a name="chinese"></a>

## <img src="https://flagcdn.com/24x18/cn.png" valign="middle"> 中文

**Flux Platform** 是一个专注于高性能、可预测性和可扩展性的模块化服务管理平台。该平台基于 **Rust** 生态系统和 **Tauri v2** 构建，弥合了原生系统执行与现代界面之间的鸿沟。

该平台的设计充分考虑了企业级运营需求：严格的进程隔离、访问控制和稳定的资源使用。与基于 Electron 的替代方案不同，Flux Platform 利用原生 WebView2，从而显著减小了二进制文件大小并降低了内存占用。

### 核心架构

-   **Rust 后端**: 业务逻辑完全使用 Rust 实现，确保内存安全和线程安全，无垃圾回收 (GC) 开销。
-   **Tauri v2 IPC**:通过优化的异步进程间通信桥梁，实现低延迟的状态同步。
-   **零开销抽象**: 关键服务（如许可证验证、系统监控）在隔离线程上运行，防止阻塞用户界面。
-   **模块化设计**: 核心架构从底层设计开始就支持模块化服务生命周期和严格的组件隔离。

### 监控系统

平台实现了专有的实时遥测分析引擎：

-   **CPU**: 核心级负载跟踪和进程级启发式分析。
-   **内存**: 物理内存 (RAM) 和显存 (VRAM) 分配的详细分类。
-   **GPU**: 通过直接集成 NVML 获取 NVIDIA 硬件的实时利用率指标。
-   **I/O**: 磁盘和网络接口的吞吐量分析。

### 性能与前端

-   **Vite 架构**: 即时热模块替换 (HMR) 和优化的资源打包。
-   **Vanilla TypeScript**: 核心仪表板避免使用沉重的框架（React/Vue），以最大限度地缩短初始化时间。
-   **自定义设计系统**: 定制的 CSS 架构确保一致的渲染效果和高效的更新。

### 安全性

-   **路径遍历保护**: 文件系统操作经过严格沙箱化，并针对白名单进行验证。
-   **输入清洗**: 对所有 IPC 负载进行严格类型检查和数据清洗。
-   **安全存储**: 使用操作系统原生密钥存储机制加密敏感配置数据。

### 技术栈

-   **后端**: Rust (Tokio, Serde, Tauri, Sysinfo, NVML-Wrapper)
-   **前端**: TypeScript, Vite, CSS
-   **构建**: Cargo, NPM, PowerShell Automation
-   **安装程序**: WiX Toolset (MSI), NSIS (EXE)

### 快速开始 (Development)

**先决条件:**

-   Windows 10/11 (x64 版本 19041+)
-   [Rust](https://rustup.rs/) (Stable 1.70+)
-   [Node.js](https://nodejs.org/) (LTS v18+)
-   [Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

```powershell
# 1. 克隆仓库
git clone https://github.com/F0RLE/flux-platform.git
cd flux-platform

# 2. 初始化环境
cd scripts
./dev.ps1
```

`./dev.ps1` 脚本自动执行依赖检查、编译和调试启动。

---

<div align="center">
  <p>
    <b>Proprietary Software</b><br>
    Copyright © 2025 F0RLE. All Rights Reserved.
  </p>
</div>
