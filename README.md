<div align="center">

# 🚀 Flux Platform

[![Rust](https://img.shields.io/badge/Rust-1.70+-orange.svg?style=flat-square&logo=rust)](https://www.rust-lang.org/)
[![Tauri](https://img.shields.io/badge/Tauri-v2-blue.svg?style=flat-square&logo=tauri)](https://tauri.app/)
[![Vite](https://img.shields.io/badge/Vite-v6-purple.svg?style=flat-square&logo=vite)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg?style=flat-square&logo=windows)](https://www.microsoft.com/windows)

<br/>

[![English](https://img.shields.io/badge/-English-grey?style=for-the-badge&logo=usb&logoColor=white&labelColor=002060)]( #english ) &nbsp;
[![Русский](https://img.shields.io/badge/-Русский-grey?style=for-the-badge&logo=usb&logoColor=white&labelColor=blue)]( #russian ) &nbsp;
[![中文](https://img.shields.io/badge/-中文-grey?style=for-the-badge&logo=usb&logoColor=white&labelColor=red)]( #chinese )

</div>

---

<a name="english"></a>
## <img src="https://flagcdn.com/24x18/gb.png" valign="middle"> English

**Flux Platform** is an enterprise-grade, modular service management platform designed for high-performance applications. Built upon the robust **Rust** ecosystem and the **Tauri v2** framework, it bridges the gap between native system performance and modern web interfaces.

Unlike Electron-based alternatives, Flux Platform leverages the system's native WebView (WebView2 on Windows), resulting in a binary size that is significantly smaller and RAM usage that is drastically lower.

### ✨ Detailed Features

#### �️ Core Architecture
*   **Rust Backend**: The core business logic is written in pure Rust, ensuring memory safety and thread safety without the overhead of a garbage collector.
*   **Tauri v2 IPC**: Uses an optimized asynchronous Inter-Process Communication (IPC) bridge to communicate between the UI and the Backend.
*   **Zero-Overhead Abstractions**: Critical services like the `LicenseVerifier` and `SystemMonitor` run on separate threads, ensuring the UI never freezes.

#### 📊 Advanced Monitoring System
The platform includes a proprietary system monitoring engine that provides real-time telemetry:
*   **CPU**: Individual core usage tracking and process-level analysis.
*   **RAM/VRAM**: Detailed breakdown of used, cached, and available memory.
*   **GPU**: Real-time utilization stats for NVIDIA (via NVML) and generic adapters.
*   **Disk I/O**: Read/Write speeds and partition usage.
*   **Network**: Real-time Upload/Download throughput monitoring.

#### ⚡ Performance & Frontend
*   **Vite-Powered**: Instant HMR (Hot Module Replacement) and optimized production builds.
*   **Vanilla JS Optimization**: We purposefully avoided heavy frontend frameworks (React/Vue/Angular) for the core dashboard to maximize startup speed and minimize overhead.
*   **Custom Design System**: A bespoke CSS framework ensures consistent theming and smooth 60fps animations.

#### 🔒 Enterprise Security
*   **Path Traversal Protection**: All file system operations are sandboxed and validated against strict allowlists.
*   **Input Sanitization**: All user inputs and IPC payloads are strictly typed and sanitized before processing.
*   **Secure Storage**: Sensitive configuration data is encrypted at rest using OS-level key chains.

### 🛠️ Technical Stack

- **Backend**: Rust (Tokio, Serde, Tauri, Sysinfo, NVML-Wrapper)
- **Frontend**: TypeScript, Vite, SASS/CSS Modules, Chart.js
- **Build System**: Cargo, NPM, PowerShell Automation
- **Installer**: WiX Toolset (MSI), NSIS (EXE)

### � Quick Start Guide

**Prerequisites:**
- Windows 10/11 (x64 Build 19041+)
- [Rust](https://rustup.rs/) (Stable 1.70+)
- [Node.js](https://nodejs.org/) (LTS v18+)
- [Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

```powershell
# 1. Clone the repository including submodules
git clone https://github.com/F0RLE/flux-platform.git
cd flux-platform

# 2. Initialize the development environment
cd scripts
./dev.ps1
```

The `./dev.ps1` script automates the entire process: it checks for dependencies, installs NPM packages, compiles the Rust backend, and launches the application in debug mode.

---

<a name="russian"></a>
## <img src="https://flagcdn.com/24x18/ru.png" valign="middle"> Русский

**Flux Platform** — это модульная платформа корпоративного уровня для управления сервисами, разработанная с упором на максимальную производительность. Построенная на экосистеме **Rust** и фреймворке **Tauri v2**, она объединяет мощь нативного кода с гибкостью современных веб-интерфейсов.

В отличие от решений на базе Electron, Flux Platform использует нативный системный WebView (WebView2 в Windows), что обеспечивает экстремально малый размер приложения и минимальное потребление оперативной памяти (в 10-20 раз меньше аналогов).

### ✨ Подробный разбор возможностей

#### 🛡️ Архитектура Ядра
*   **Бэкенд на Rust**: Вся бизнес-логика написана на чистом Rust, что гарантирует безопасность памяти и отсутствие пауз на сборку мусора (GC).
*   **Tauri v2 IPC**: Используется оптимизированный асинхронный мост (IPC) для мгновенного обмена данными между UI и системным ядром.
*   **Многопоточность**: Критические сервисы, такие как проверка лицензий и мониторинг, работают в изолированных потоках, гарантируя, что интерфейс всегда остается отзывчивым.

#### 📊 Продвинутая Система Мониторинга
Платформа включает собственный движок телеметрии:
*   **CPU**: Отслеживание нагрузки по каждому ядру и анализ процессов.
*   **RAM/VRAM**: Детальная статистика использования, кэша и доступной памяти.
*   **GPU**: Мониторинг нагрузки в реальном времени для NVIDIA (через NVML) и других адаптеров.
*   **Диски**: Скорость чтения/записи и заполненность разделов.
*   **Сеть**: Текущая скорость отдачи/загрузки.

#### ⚡ Производительность и Фронтенд
*   **Vite**: Мгновенный HMR (Hot Module Replacement) и оптимизированные сборки.
*   **Оптимизация**: Мы намеренно отказались от тяжелых фреймворков (React/Vue) в ядре дашборда, чтобы приложения запускалось мгновенно.
*   **Дизайн-система**: Уникальный CSS-фреймворк обеспечивает визуальную целостность и плавные анимации 60fps.

#### 🔒 Корпоративная Безопасность
*   **Защита от Path Traversal**: Все операции с файловой системой проходят через "песочницу" и строгую валидацию путей.
*   **Санитизация ввода**: Все данные от пользователя и через IPC строго типизируются и очищаются.
*   **Безопасное хранение**: Чувствительные данные шифруются с использованием системных механизмов защиты ключей.

### 🛠️ Технический Стек

- **Backend**: Rust (Tokio, Serde, Tauri, Sysinfo, NVML-Wrapper)
- **Frontend**: TypeScript, Vite, SASS/CSS Modules, Chart.js
- **Сборка**: Cargo, NPM, PowerShell Automation
- **Инсталлер**: WiX Toolset (MSI), NSIS (EXE)

### 🚀 Инструкция по запуску

**Требования:**
- Windows 10/11 (x64 версия 19041+)
- [Rust](https://rustup.rs/) (Stable 1.70+)
- [Node.js](https://nodejs.org/) (LTS v18+)
- [Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

```powershell
# 1. Клонирование репозитория
git clone https://github.com/F0RLE/flux-platform.git
cd flux-platform

# 2. Инициализация среды разработки
cd scripts
./dev.ps1
```

Скрипт `./dev.ps1` полностью автоматизирует процесс: проверяет зависимости, устанавливает пакеты NPM, компилирует Rust бэкенд и запускает приложение в режиме отладки.

---

<a name="chinese"></a>
## <img src="https://flagcdn.com/24x18/cn.png" valign="middle"> 中文

**Flux Platform** 是一个企业级的模块化服务管理平台，专为高性能应用设计。基于 **Rust** 生态系统和 **Tauri v2** 框架构建，它完美结合了原生系统的性能与现代 Web 界面的灵活性。

与基于 Electron 的替代方案不同，Flux Platform 利用系统的原生 WebView（Windows 上的 WebView2），因此二进制文件体积极小，且 RAM 占用率大幅降低。

### ✨ 功能详解

#### 🛡️ 核心架构
*   **Rust 后端**: 核心业务逻辑完全使用 Rust 编写，确保内存安全和线程安全，没有垃圾回收（GC）的开销。
*   **Tauri v2 IPC**: 使用优化的异步进程间通信（IPC）桥梁，在 UI 和后端之间进行高效通信。
*   **零开销抽象**: 诸如 `LicenseVerifier` 和 `SystemMonitor` 等关键服务在独立线程上运行，确保 UI 永不卡顿。

#### 📊 高级监控系统
平台包含专有的系统监控引擎，提供实时遥测：
*   **CPU**: 跟踪单个核心的使用率及进程级分析。
*   **RAM/VRAM**: 详细细分已用、缓存和可用内存。
*   **GPU**: NVIDIA (通过 NVML) 和通用适配器的实时利用率统计。
*   **磁盘 I/O**: 读/写速度和分区使用情况。
*   **网络**: 实时上传/下载吞吐量监控。

#### ⚡ 性能与前端
*   **Vite 驱动**: 即时 HMR（热模块替换）和优化的生产构建。
*   **原生 JS 优化**: 核心仪表板刻意避免使用沉重的前端框架（如 React/Vue/Angular），以最大限度地提高启动速度并减少开销。
*   **自定义设计系统**: 定制的 CSS 框架确保一致的主题风格和流畅的 60fps 动画。

#### 🔒 企业级安全
*   **路径遍历保护**: 所有文件系统操作都在沙箱中进行，并根据严格的白名单进行验证。
*   **输入清洗**: 所有用户输入和 IPC 负载在处理前都经过严格的类型检查和清洗。
*   **安全存储**: 敏感配置数据使用操作系统级密钥链进行静态加密。

### 🛠️ 技术栈

- **后端**: Rust (Tokio, Serde, Tauri, Sysinfo, NVML-Wrapper)
- **前端**: TypeScript, Vite, SASS/CSS Modules, Chart.js
- **构建系统**: Cargo, NPM, PowerShell Automation
- **安装程序**: WiX Toolset (MSI), NSIS (EXE)

### � 快速开始指南

**先决条件:**
- Windows 10/11 (x64 版本 19041+)
- [Rust](https://rustup.rs/) (Stable 1.70+)
- [Node.js](https://nodejs.org/) (LTS v18+)
- [Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

```powershell
# 1. 克隆仓库
git clone https://github.com/F0RLE/flux-platform.git
cd flux-platform

# 2. 初始化开发环境
cd scripts
./dev.ps1
```

`./dev.ps1` 脚本自动化了整个过程：它会检查依赖项、安装 NPM 包、编译 Rust 后端，并在调试模式下启动应用程序。

---

<div align="center">
  <p>
    <b>Proprietary Software</b><br>
    Copyright © 2025 F0RLE. All Rights Reserved.
  </p>
</div>
