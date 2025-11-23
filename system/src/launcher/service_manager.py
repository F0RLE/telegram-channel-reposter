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

    def stop_service(self, name: str):
        proc = self.procs.get(name)
        if proc:
            service_name = self._get_service_name(name)
            self.log(t("ui.launcher.log.service_stopping", default="⏹️ Stopping service: {service}...", service=service_name), name.upper())
            self.stop_events[name].set()
            try:
                self.kill_tree(proc.pid)
            except:
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
                except:
                    pass
        except:
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
                                except:
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
                                except:
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
                except:
                    pass
                
                cmd = [venv_py, "launch.py", "--api", "--nowebui", "--port", "7860", "--skip-python-version-check"]
                if cuda_supported:
                    cmd.extend(["--xformers", "--cuda-stream"])
                cwd = SD_DIR

            # Launch process
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            p = subprocess.Popen(
                cmd, cwd=cwd, env=env,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                encoding='utf-8', errors='replace',
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            self.procs[name] = p
            self.update_status(name, "running", "green")
            
            def reader():
                try:
                    for line in iter(p.stdout.readline, ''):
                        if line and not self.stop_events[name].is_set():
                            self.log_queue.put((line.strip(), name.upper()))
                except:
                    pass
                finally:
                    try:
                        p.stdout.close()
                    except:
                        pass
                    if self.procs.get(name) == p:  # If this is still the active process
                        self.procs[name] = None
                        self.update_status(name, "stopped", "gray")

            threading.Thread(target=reader, daemon=True).start()

        except Exception as e:
            self.log(t("ui.launcher.log.service_start_error", default="❌ Error: {error}", error=str(e)), name.upper())
            self.update_status(name, "error", "red")

