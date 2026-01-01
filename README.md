<div align="center">

# 🚀 Flux Platform

[![Rust](https://img.shields.io/badge/Rust-1.70+-orange.svg)](https://www.rust-lang.org/)
[![Tauri](https://img.shields.io/badge/Tauri-v2-blue.svg)](https://tauri.app/)
[![Vite](https://img.shields.io/badge/Vite-v6-purple.svg)](https://vitejs.dev/)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://www.microsoft.com/windows)

**[English](#english)** | **[Русский](#russian)** | **[中文](#chinese)**

</div>

---

<a name="english"></a>
## 🇬🇧 English

**Flux Platform** is a powerful, modular service management platform and launcher built with **Rust**, **Tauri v2**, and **Vite**.

### ✨ Features

| Feature | Description |
|---------|-------------|
| 🚀 **Modern UI** | Sleek dashboard built with Vanilla JS + Vite (Tailwind-free) |
| ⚡ **High Performance** | Rust backend for near-native performance and low footprint |
| 📊 **Monitoring** | Real-time tracking of CPU, GPU, RAM, VRAM, Disk, and Network |
| 🧩 **Modular** | Extensible architecture for managing external services |
| 🔒 **Secure** | Path traversal protection, input validation, and secure IPC |
| 🌐 **Localization** | Built-in support for multiple languages (EN, RU, ZH) |

### 🛠️ Quick Start

**Requirements:**
- Windows 10/11 (x64)
- [Rust](https://rustup.rs/) (1.70+)
- [Node.js](https://nodejs.org/) (18+)
- [VS C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

```powershell
# 1. Clone the repository
git clone https://github.com/F0RLE/flux-platform.git
cd flux-platform

# 2. Run the development script
cd scripts
./dev.ps1
```

The application will start in development mode with Hot Module Replacement (HMR).

### 🏗️ Project Structure

```
flux-platform/
├── src-tauri/           # 🦀 Rust Backend (Tauri v2)
│   ├── src/
│   │   ├── commands/    # IPC Commands (Thin layer)
│   │   ├── services/    # Business Logic
│   │   └── models/      # Data Structures
│   └── tauri.conf.json  # Application Config
├── src/                 # ⚡ Frontend (Vite)
│   ├── js/              # Core logic & UI components
│   └── css/             # Modular styles
└── scripts/             # 🛠️ Build & Dev Scripts (PowerShell)
```

### 📚 Documentation

- [**Architecture Overview**](docs/architecture.md) — Internal design and principles.
- [**Development Guide**](docs/development.md) — How to contribute and add features.

---

<a name="russian"></a>
## 🇷🇺 Русский

**Flux Platform** — это мощная платформа для управления сервисами и запуска приложений, созданная на **Rust**, **Tauri v2** и **Vite**.

### ✨ Возможности

| Функция | Описание |
|---------|----------|
| 🚀 **Современный UI** | Быстрый интерфейс на Vanilla JS + Vite (без тяжелых фреймворков) |
| ⚡ **Производительность** | Бэкенд на Rust обеспечивает минимальное потребление ресурсов |
| 📊 **Мониторинг** | Отслеживание CPU, GPU, RAM, VRAM, дисков и сети в реальном времени |
| 🧩 **Модульность** | Расширяемая архитектура для подключения внешних сервисов |
| 🔒 **Безопасность** | Защита от path traversal, валидация ввода, безопасный IPC |
| 🌐 **Локализация** | Поддержка русского, английского и китайского языков |

### 🛠️ Быстрый старт

**Требования:**
- Windows 10/11 (x64)
- [Rust](https://rustup.rs/) (1.70+)
- [Node.js](https://nodejs.org/) (18+)
- [VS C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

```powershell
# 1. Клонирование репозитория
git clone https://github.com/F0RLE/flux-platform.git
cd flux-platform

# 2. Запуск скрипта разработки
cd scripts
./dev.ps1
```

Приложение запустится в режиме разработки с поддержкой Hot Module Replacement (HMR).

### 🏗️ Структура проекта

```
flux-platform/
├── src-tauri/           # 🦀 Бэкенд на Rust (Tauri v2)
│   ├── src/
│   │   ├── commands/    # IPC команды (Тонкий слой)
│   │   ├── services/    # Бизнес-логика
│   │   └── models/      # Структуры данных
│   └── tauri.conf.json  # Конфигурация приложения
├── src/                 # ⚡ Фронтенд (Vite)
│   ├── js/              # Логика и компоненты UI
│   └── css/             # Модульные стили
└── scripts/             # 🛠️ Скрипты сборки и запуска (PowerShell)
```

### 📚 Документация

- [**Архитектура**](docs/architecture.md) — Принципы проектирования и внутреннее устройство.
- [**Руководство разработчика**](docs/development.md) — Как добавлять новые функции и сервисы.

---

<a name="chinese"></a>
## 🇨🇳 中文

**Flux Platform** 是一个基于 **Rust**、**Tauri v2** 和 **Vite** 构建的强大模块化服务管理平台和启动器。

### ✨ 主要功能

| 功能 | 描述 |
|------|------|
| 🚀 **现代界面** | 使用 Vanilla JS + Vite 构建的流畅仪表板（无 Tailwind） |
| ⚡ **高性能** | 基于 Rust 的后端，提供近乎原生的性能和低资源占用 |
| 📊 **实时监控** | 实时追踪 CPU、GPU、RAM、VRAM、磁盘和网络状态 |
| 🧩 **模块化** | 可扩展的架构，用于管理外部服务 |
| 🔒 **安全** | 路径遍历保护、输入验证和安全的 IPC 通信 |
| 🌐 **本地化** | 内置多语言支持（英语、俄语、中文） |

### 🛠️ 快速开始

**系统要求:**
- Windows 10/11 (x64)
- [Rust](https://rustup.rs/) (1.70+)
- [Node.js](https://nodejs.org/) (18+)
- [VS C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

```powershell
# 1. 克隆仓库
git clone https://github.com/F0RLE/flux-platform.git
cd flux-platform

# 2. 运行开发脚本
cd scripts
./dev.ps1
```

应用程序将以开发模式启动，支持热模块替换 (HMR)。

### 🏗️ 项目结构

```
flux-platform/
├── src-tauri/           # 🦀 Rust 后端 (Tauri v2)
│   ├── src/
│   │   ├── commands/    # IPC 命令 (薄层)
│   │   ├── services/    # 业务逻辑
│   │   └── models/      # 数据结构
│   └── tauri.conf.json  # 应用程序配置
├── src/                 # ⚡ 前端 (Vite)
│   ├── js/              # 核心逻辑与 UI 组件
│   └── css/             # 模块化样式
└── scripts/             # 🛠️ 构建与开发脚本 (PowerShell)
```

### 📚 文档

- [**架构概览**](docs/architecture.md) — 内部设计与原则。
- [**开发指南**](docs/development.md) — 如何贡献代码与添加功能。

---

<div align="center">
  <p>
    <b>Proprietary Software</b><br>
    Copyright © 2025 F0RLE. All Rights Reserved.
  </p>
</div>
