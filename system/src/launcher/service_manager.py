import os
import subprocess
import sys
import threading
import time
import psutil
import queue
import urllib.request
from typing import Callable, Dict, Optional, Any

# Try relative import first, fallback to absolute
try:
    from .i18n import t
except (ImportError, ValueError):
    try:
        from i18n import t
    except ImportError:
        def t(key, default=None, **kwargs):
            return default or key

# Import config with fallback
try:
    from .config import (
        BASE_DIR, PYTHON_EXE, GIT_CMD, OLLAMA_EXE, OLLAMA_DIR, OLLAMA_MODELS_DIR,
        OLLAMA_DATA_DIR, SD_DIR, MODELS_SD_DIR, MODELS_LLM_DIR, FILE_ENV, DIR_CONFIGS, DIR_TEMP
    )
except (ImportError, ValueError):
    from config import (
        BASE_DIR, PYTHON_EXE, GIT_CMD, OLLAMA_EXE, OLLAMA_DIR, OLLAMA_MODELS_DIR,
        OLLAMA_DATA_DIR, SD_DIR, MODELS_SD_DIR, MODELS_LLM_DIR, FILE_ENV, DIR_CONFIGS, DIR_TEMP
    )

# Import other modules with fallback
try:
    from .installer import Installer
    from .model_manager import ModelManager
except (ImportError, ValueError):
    from installer import Installer
    from model_manager import ModelManager

class ServiceManager:
    def __init__(self, log_callback: Callable[[str, str], None], 
                 status_callback: Callable[[str, str, str], None],
                 installer: Installer,
                 log_queue: queue.Queue):
        self.log = log_callback
        self.update_status = status_callback
        self.installer = installer
        self.log_queue = log_queue
        self.procs = {"bot": None, "llm": None, "sd": None}
        self.stop_events = {k: threading.Event() for k in self.procs}
        self.selected_llm_model = None
        self.model_manager = ModelManager(log_callback=log_callback)

    def _get_service_name(self, key: str) -> str:
        """Get localized service name"""
        names = {
            "bot": t("ui.launcher.service.telegram_bot", default="Telegram Bot"),
            "llm": t("ui.launcher.service.llm_server", default="LLM Server"),
            "sd": t("ui.launcher.service.stable_diffusion", default="Stable Diffusion")
        }
        return names.get(key, key.upper())

    def kill_tree(self, pid):
        """Kill process and all its children recursively"""
        try:
            parent = psutil.Process(pid)
            # Terminate all children first
            for child in parent.children(recursive=True):
                try:
                    child.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            # Wait a bit for graceful termination
            try:
                parent.terminate()
                parent.wait(timeout=3)
            except (psutil.TimeoutExpired, psutil.NoSuchProcess):
                # Force kill if still running
                try:
                    parent.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    def _kill_process_on_port(self, port: int):
        """Убивает процесс, занимающий указанный порт"""
        try:
            import socket
            # Проверяем, занят ли порт
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:  # Порт занят
                self.log(t("ui.launcher.log.port_in_use", default="⚠️ Порт {port} занят, освобождаю...", port=port), "SYSTEM")
                
                # Находим процесс, занимающий порт (правильный способ для Windows)
                # Используем netstat для более надежного поиска на Windows
                try:
                    # Пробуем через netstat (работает без прав администратора)
                    netstat_result = subprocess.run(
                        ["netstat", "-ano"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if netstat_result.returncode == 0:
                        for line in netstat_result.stdout.split('\n'):
                            if f':{port}' in line and 'LISTENING' in line:
                                parts = line.split()
                                if len(parts) >= 5:
                                    try:
                                        pid = int(parts[-1])
                                        self.log(t("ui.launcher.log.killing_process_on_port", default="🔄 Убиваю процесс {pid} на порту {port}...", pid=pid, port=port), "SYSTEM")
                                        self.kill_tree(pid)
                                        time.sleep(2)  # Даем время на освобождение порта
                                        return
                                    except (ValueError, psutil.NoSuchProcess):
                                        continue
                except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                    pass
                
                # Fallback: пробуем через psutil (может не работать для всех процессов без прав админа)
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        # Используем proc.connections() с обработкой ошибок доступа
                        connections = proc.connections(kind='inet')
                        if connections:
                            for conn in connections:
                                if conn.status == psutil.CONN_LISTEN and conn.laddr.port == port:
                                    pid = proc.pid
                                    self.log(t("ui.launcher.log.killing_process_on_port", default="🔄 Убиваю процесс {pid} на порту {port}...", pid=pid, port=port), "SYSTEM")
                                    self.kill_tree(pid)
                                    time.sleep(2)  # Даем время на освобождение порта
                                    return
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, AttributeError, OSError):
                        continue
        except Exception as e:
            self.log(t("ui.launcher.log.port_check_error", default="⚠️ Ошибка проверки порта {port}: {error}", port=port, error=str(e)), "SYSTEM")

    def stop_service(self, name: str):
        proc = self.procs.get(name)
        if proc:
            service_name = self._get_service_name(name)
            self.log(t("ui.launcher.log.service_stopping", default="⏹️ Stopping service: {service}...", service=service_name), name.upper())
            self.stop_events[name].set()
            
            # Для бота используем более мягкое завершение
            if name == "bot":
                try:
                    # Сначала отправляем SIGTERM для graceful shutdown
                    parent = psutil.Process(proc.pid)
                    parent.terminate()
                    # Ждем до 10 секунд для graceful shutdown (удаление сообщений может занять время)
                    try:
                        parent.wait(timeout=10)
                        self.log(t("ui.launcher.log.service_stopped_gracefully", default="✅ Service {service} stopped gracefully", service=service_name), name.upper())
                    except psutil.TimeoutExpired:
                        # Если не завершился, убиваем принудительно
                        self.log(t("ui.launcher.log.service_force_stop", default="⚠️ Force stopping service {service}...", service=service_name), name.upper())
                        self.kill_tree(proc.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            else:
                # Для других сервисов используем обычное завершение
                try:
                    self.kill_tree(proc.pid)
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            self.procs[name] = None
            self.update_status(name, "stopped", "gray")
            self.log(t("ui.launcher.log.service_stopped", default="⏹️ Service {service} stopped", service=service_name), name.upper())

    def _kill_bot_processes(self):
        try:
            current_pid = os.getpid()
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        cmdline = proc.info.get('cmdline', [])
                        if cmdline and any('main.py' in str(arg) for arg in cmdline):
                            pid = proc.info['pid']
                            if pid != current_pid:
                                p = psutil.Process(pid)
                                p.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError, TypeError):
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    def start_service(self, name: str, llm_model_info=None):
        self.stop_events[name].clear()
        self.update_status(name, "starting", "orange")
        
        env = os.environ.copy()
        if os.path.exists(os.path.dirname(GIT_CMD)):
            env["PATH"] = os.path.dirname(GIT_CMD) + os.pathsep + env.get("PATH", "")

        cmd = []
        cwd = BASE_DIR

        try:
            if name == "bot":
                if not os.path.exists(PYTHON_EXE):
                    self.log(t("ui.launcher.log.python_not_found", default="❌ [BOT] Python not found"), "BOT")
                    raise FileNotFoundError("Python not found")
                
                script = os.path.join(BASE_DIR, "main.py")
                if not os.path.exists(script):
                    self.log(t("ui.launcher.log.main_not_found", default="❌ [BOT] main.py not found"), "BOT")
                    raise FileNotFoundError("main.py not found")
                
                # Check bot token
                from dotenv import get_key
                bot_token = get_key(FILE_ENV, "BOT_TOKEN")
                if not bot_token or not bot_token.strip():
                    self.log(t("ui.launcher.log.bot_token_not_set", default="❌ [BOT] Bot token not set"), "BOT")
                    raise ValueError("Bot token not set")
                
                self._kill_bot_processes()
                
                env["BOT_CONFIG_DIR"] = DIR_CONFIGS
                env["PYTHONPATH"] = BASE_DIR
                cmd = [PYTHON_EXE, "-u", script]

            elif name == "llm":
                if not os.path.exists(OLLAMA_EXE):
                    if not self.installer.download_ollama():
                        raise Exception("Ollama installation failed")

                if not llm_model_info:
                     raise Exception("Model not selected")

                model_name = llm_model_info['name']
                model_type = llm_model_info['type']
                model_path = llm_model_info.get('path')

                # Проверяем и загружаем модель Ollama, если она не загружена
                if model_type == 'ollama':
                    # Проверяем наличие модели в Ollama
                    if not self.model_manager.check_ollama_model(model_name):
                        self.log(f"📦 [LLM] Модель {model_name} не найдена, загружаю...", "LLM")
                        
                        # Останавливаем все процессы Ollama перед началом
                        self.installer.kill_all_ollama_processes()
                        time.sleep(2)
                        
                        # Запускаем временный Ollama server для загрузки
                        temp_env = env.copy()
                        temp_env["OLLAMA_HOST"] = "127.0.0.1:11434"
                        temp_env["OLLAMA_ORIGINS"] = "*"
                        temp_env["OLLAMA_MODELS"] = MODELS_LLM_DIR
                        temp_env["OLLAMA_DATA"] = OLLAMA_DATA_DIR
                        
                        temp_ollama = None
                        try:
                            # Стартуем временный сервер
                            self.log(f"🔧 [LLM] Запуск временного Ollama сервера...", "LLM")
                            temp_ollama = subprocess.Popen(
                                [OLLAMA_EXE, "serve"],
                                cwd=OLLAMA_DIR,
                                env=temp_env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=subprocess.STARTUPINFO()
                            )
                            
                            # Ждем запуска сервера
                            server_started = False
                            for i in range(30):
                                time.sleep(1)
                                try:
                                    req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
                                    with urllib.request.urlopen(req, timeout=2) as response:
                                        if response.status == 200:
                                            server_started = True
                                            self.log(f"✅ [LLM] Временный сервер запущен", "LLM")
                                            break
                                except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError):
                                    if i == 29:
                                        raise Exception("Ollama server failed to start")
                            
                            if not server_started:
                                raise Exception("Failed to start temporary Ollama server")
                            
                            # Загружаем модель через ollama pull
                            self.log(f"⬇️ [LLM] Загрузка модели {model_name}...", "LLM")
                            
                            startupinfo = subprocess.STARTUPINFO()
                            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                            startupinfo.wShowWindow = subprocess.SW_HIDE
                            
                            # Используем Popen для отслеживания прогресса
                            pull_process = subprocess.Popen(
                                [OLLAMA_EXE, "pull", model_name],
                                cwd=OLLAMA_DIR,
                                env=temp_env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                text=True,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=startupinfo
                            )
                            
                            # Читаем вывод в реальном времени
                            for line in iter(pull_process.stdout.readline, ''):
                                if line:
                                    # Логируем прогресс
                                    line_stripped = line.strip()
                                    if line_stripped:
                                        self.log(f"📥 [LLM] {line_stripped}", "LLM")
                            
                            pull_process.wait(timeout=600)
                            
                            if pull_process.returncode == 0:
                                self.log(f"✅ [LLM] Модель {model_name} успешно загружена", "LLM")
                            else:
                                raise Exception(f"Pull command failed with code {pull_process.returncode}")
                                
                        except subprocess.TimeoutExpired:
                            self.log(f"❌ [LLM] Таймаут при загрузке модели {model_name}", "LLM")
                            if pull_process:
                                pull_process.kill()
                            raise Exception("Model download timeout")
                        except Exception as e:
                            self.log(f"❌ [LLM] Ошибка при загрузке модели: {e}", "LLM")
                            raise
                        finally:
                            # Останавливаем временный сервер
                            if temp_ollama:
                                try:
                                    temp_ollama.terminate()
                                    temp_ollama.wait(timeout=5)
                                except (subprocess.TimeoutExpired, ProcessLookupError):
                                    if temp_ollama.poll() is None:
                                        temp_ollama.kill()
                            time.sleep(2)
                            self.installer.kill_all_ollama_processes()

                # Import GGUF model if needed
                if model_type == 'gguf' and model_path:
                    if not self.model_manager.check_ollama_model(model_name):
                        self.log(t("ui.launcher.log.model_not_found", default="📦 [LLM] Model not found, importing..."), "LLM")
                        self.installer.kill_all_ollama_processes()
                        time.sleep(2)
                        
                        # Start temporary Ollama server for import
                        temp_env = env.copy()
                        temp_env["OLLAMA_HOST"] = "127.0.0.1:11434"
                        temp_env["OLLAMA_ORIGINS"] = "*"
                        temp_env["OLLAMA_MODELS"] = MODELS_LLM_DIR  # Use unified models directory
                        temp_env["OLLAMA_DATA"] = OLLAMA_DATA_DIR
                        
                        temp_ollama = None
                        try:
                            temp_ollama = subprocess.Popen(
                                [OLLAMA_EXE, "serve"],
                                cwd=OLLAMA_DIR,
                                env=temp_env,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                                startupinfo=subprocess.STARTUPINFO()
                            )
                            
                            # Wait for server to start
                            for i in range(30):
                                time.sleep(1)
                                try:
                                    req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
                                    with urllib.request.urlopen(req, timeout=2) as response:
                                        if response.status == 200:
                                            break
                                except (urllib.error.URLError, urllib.error.HTTPError, OSError, TimeoutError):
                                    if i == 29:
                                        raise Exception("Ollama server failed to start")
                            
                            # Import model
                            if not self.model_manager.import_gguf_to_ollama(model_path, model_name, temp_env):
                                raise Exception("Model import failed")
                        finally:
                            # Stop temporary server
                            if temp_ollama:
                                try:
                                    temp_ollama.terminate()
                                    temp_ollama.wait(timeout=5)
                                except (subprocess.TimeoutExpired, ProcessLookupError):
                                    if temp_ollama.poll() is None:
                                        temp_ollama.kill()
                            time.sleep(2)
                            self.installer.kill_all_ollama_processes()

                self.installer.kill_all_ollama_processes()

                env["OLLAMA_HOST"] = "127.0.0.1:11434"
                env["OLLAMA_ORIGINS"] = "*"
                env["OLLAMA_MODELS"] = MODELS_LLM_DIR  # Use unified models directory
                env["OLLAMA_DATA"] = OLLAMA_DATA_DIR
                
                cmd = [OLLAMA_EXE, "serve"]
                cwd = OLLAMA_DIR

            elif name == "sd":
                launch_script = os.path.join(SD_DIR, "launch.py")
                if not os.path.exists(SD_DIR) or not os.path.exists(launch_script):
                    if not self.installer.install_sd():
                        raise Exception("SD installation failed")
                
                venv = os.path.join(SD_DIR, "venv")
                if not os.path.exists(venv):
                     if not self.installer.create_sd_venv():
                        raise Exception("SD venv creation failed")
                
                venv_py = os.path.join(venv, "Scripts", "python.exe")
                if not os.path.exists(venv_py):
                    raise FileNotFoundError("SD venv Python not found")
                
                # Проверяем и освобождаем порт 7860
                self._kill_process_on_port(7860)
                
                # Check for CUDA support
                cuda_supported = False
                try:
                    check_result = subprocess.run(
                        ["nvidia-smi"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    if check_result.returncode == 0:
                        cuda_supported = True
                except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
                    pass
                
                cmd = [venv_py, "launch.py", "--api", "--nowebui", "--port", "7860", "--skip-python-version-check"]
                if cuda_supported:
                    cmd.extend(["--xformers", "--cuda-stream"])
                cwd = SD_DIR

            # Launch process
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            service_name = self._get_service_name(name)
            self.log(t("ui.launcher.log.service_launching", default=f"🚀 [{name.upper()}] Launching {service_name}...", service=service_name), name.upper())
            
            p = subprocess.Popen(
                cmd, cwd=cwd, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,  # Separate stderr
                encoding='utf-8', errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            self.procs[name] = p
            self.update_status(name, "running", "green")
            self.log(t("ui.launcher.log.service_pid", default=f"✅ [{name.upper()}] Process started (PID: {p.pid})", service=service_name, pid=p.pid), name.upper())
            
            def reader():
                try:
                    for line in iter(p.stdout.readline, ''):
                        if line and not self.stop_events[name].is_set():
                            self.log_queue.put((line.strip(), name.upper()))
                except (OSError, ValueError, AttributeError):
                    pass
                finally:
                    try:
                        p.stdout.close()
                    except (OSError, AttributeError):
                        pass
                    if self.procs.get(name) == p:  # If this is still the active process
                        self.procs[name] = None
                        self.update_status(name, "stopped", "gray")
            
            def error_reader():
                try:
                    for line in iter(p.stderr.readline, ''):
                        if line and not self.stop_events[name].is_set():
                            # Log errors with warning prefix
                            self.log_queue.put((f"⚠️ {line.strip()}", name.upper()))
                except (OSError, ValueError, AttributeError):
                    pass
                finally:
                    try:
                        p.stderr.close()
                    except (OSError, AttributeError):
                        pass
            
            threading.Thread(target=reader, daemon=True).start()
            threading.Thread(target=error_reader, daemon=True).start()

        except Exception as e:
            service_name = self._get_service_name(name)
            self.log(t("ui.launcher.log.service_start_error", default=f"❌ [{name.upper()}] Error starting service: {{error}}", service=service_name, error=str(e)), name.upper())
            self.update_status(name, "error", "red")

