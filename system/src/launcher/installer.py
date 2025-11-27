import os
import subprocess
import sys
import time
import shutil
import urllib.request
import urllib.error
import json
import threading
from typing import Callable, Optional

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
        BASE_DIR, DIR_TEMP, OLLAMA_EXE, OLLAMA_DIR, SD_DIR, GIT_CMD, 
        SD_REPO, MODELS_SD_DIR, ADETAILER_REPO, PYTHON_EXE
    )
except (ImportError, ValueError):
    from config import (
        BASE_DIR, DIR_TEMP, OLLAMA_EXE, OLLAMA_DIR, SD_DIR, GIT_CMD, 
        SD_REPO, MODELS_SD_DIR, ADETAILER_REPO, PYTHON_EXE
    )

class Installer:
    def __init__(self, log_callback: Callable[[str, str], None]):
        self.log = log_callback

    def _download_file_with_progress(self, url, dest_path, service_name, total_size_override=None):
        """Downloads a file with progress logging"""
        try:
            req = urllib.request.Request(url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            
            with urllib.request.urlopen(req, timeout=300) as response:
                total_size = int(response.headers.get('Content-Length', 0))
                if total_size_override:
                    total_size = total_size_override
                    
                total_mb = total_size / 1024 / 1024
                
                downloaded = 0
                last_percent = -1
                
                with open(dest_path, 'wb') as out_file:
                    while True:
                        chunk = response.read(8192)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        downloaded += len(chunk)
                        
                        if total_size > 0:
                            percent = (downloaded * 100) // total_size
                            if percent != last_percent and (percent % 10 == 0 or downloaded == len(chunk)):
                                downloaded_mb = downloaded / 1024 / 1024
                                self.log(t("ui.launcher.log.download_progress", 
                                         default="📥 [{service}] Downloaded: {downloaded} / {total} MB ({percent}%)", 
                                         service=service_name,
                                         downloaded=f"{downloaded_mb:.1f}", 
                                         total=f"{total_mb:.1f}", 
                                         percent=percent), service_name)
                                last_percent = percent
            return True
        except Exception as e:
            self.log(t("ui.launcher.log.download_error", 
                     default="❌ [{service}] Download error: {error}", 
                     service=service_name,
                     error=str(e)), service_name)
            return False

    def kill_all_ollama_processes(self):
        """Kills all running Ollama processes"""
        killed_count = 0
        try:
            # Try to kill via taskkill
            subprocess.run(["taskkill", "/F", "/IM", "ollama.exe"], 
                         capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            subprocess.run(["taskkill", "/F", "/IM", "ollama_app.exe"], 
                         capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            return 1 # Return at least 1 if no exception
        except Exception:
            return 0

    def download_ollama(self):
        """Automatically downloads and installs Ollama for Windows"""
        try:
            self.log(t("ui.launcher.log.llm_searching_ollama", default="📥 [LLM] Searching for Ollama..."), "LLM")
            
            # Check standard paths
            possible_paths = [
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Ollama", "ollama.exe"),
                os.path.join(os.environ.get("ProgramFiles", ""), "Ollama", "ollama.exe"),
                os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Ollama", "ollama.exe"),
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    try:
                        shutil.copy2(path, OLLAMA_EXE)
                        self.log(t("ui.launcher.log.llm_ollama_copied", default="✅ [LLM] Ollama copied from {path}", path=path), "LLM")
                        return True
                    except Exception as e:
                        self.log(t("ui.launcher.log.llm_ollama_copy_failed", default="⚠️ [LLM] Copy failed: {error}", error=str(e)), "LLM")
            
            self.log(t("ui.launcher.log.llm_ollama_not_found", default="📦 [LLM] Ollama not found, starting download..."), "LLM")
            
            try:
                direct_url = "https://ollama.com/download/OllamaSetup.exe"
                download_url = direct_url
                file_size = 0
                
                try:
                    req = urllib.request.Request(direct_url)
                    req.add_header('User-Agent', 'Mozilla/5.0')
                    with urllib.request.urlopen(req, timeout=5) as response:
                        file_size = int(response.headers.get('Content-Length', 0))
                except:
                    # Fallback to GitHub
                    self.log(t("ui.launcher.log.llm_trying_github", default="🔍 [LLM] Direct URL unavailable, trying GitHub Releases..."), "LLM")
                    releases_url = "https://api.github.com/repos/ollama/ollama/releases/latest"
                    
                    with urllib.request.urlopen(releases_url, timeout=10) as response:
                        release_data = json.loads(response.read().decode())
                    
                    patterns = ["windows", "win", "setup", "installer"]
                    download_url = None
                    
                    for asset in release_data.get("assets", []):
                        name_lower = asset["name"].lower()
                        if asset["name"].endswith(".exe") and any(p in name_lower for p in patterns):
                            download_url = asset["browser_download_url"]
                            file_size = asset.get("size", 0)
                            break
                    
                    if not download_url:
                        self.log(t("ui.launcher.log.llm_windows_installer_not_found", default="❌ [LLM] Windows installer not found in release"), "LLM")
                        return False
                
                # Download
                temp_installer = os.path.join(DIR_TEMP, "OllamaSetup.exe")
                os.makedirs(DIR_TEMP, exist_ok=True)
                
                if not self._download_file_with_progress(download_url, temp_installer, "LLM", total_size_override=file_size):
                    return False
                
                self.log(t("ui.launcher.log.llm_installer_downloaded", default="✅ [LLM] Installer downloaded"), "LLM")
                
                # Install
                self.log(t("ui.launcher.log.llm_installing_ollama", default="⚙️ [LLM] Installing Ollama (silent mode)..."), "LLM")
                
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                proc = subprocess.Popen(
                    [temp_installer, "/S"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    startupinfo=startupinfo,
                    shell=False
                )
                
                try:
                    proc.wait(timeout=300)
                    if proc.returncode == 0:
                        self.log(t("ui.launcher.log.llm_installer_success", default="✅ [LLM] Installation successful"), "LLM")
                    else:
                        self.log(t("ui.launcher.log.llm_installer_exit_code", default="⚠️ [LLM] Installer exit code: {code}", code=proc.returncode), "LLM")
                except subprocess.TimeoutExpired:
                    proc.kill()
                    self.log(t("ui.launcher.log.llm_install_timeout", default="⚠️ [LLM] Installation timed out"), "LLM")
                    return False
                
                time.sleep(5)
                self.kill_all_ollama_processes()
                
                # Copy to local dir
                for _ in range(5):
                    for path in possible_paths:
                        if os.path.exists(path):
                            try:
                                os.makedirs(OLLAMA_DIR, exist_ok=True)
                                shutil.copy2(path, OLLAMA_EXE)
                                self.log(t("ui.launcher.log.llm_installed_copied", default="✅ [LLM] Ollama installed and copied"), "LLM")
                                try:
                                    os.remove(temp_installer)
                                except:
                                    pass
                                return True
                            except:
                                pass
                    time.sleep(2)
                
                return False

            except Exception as e:
                self.log(t("ui.launcher.log.llm_download_error", default="❌ [LLM] Download error: {error}", error=str(e)), "LLM")
                return False
                
        except Exception as e:
            self.log(t("ui.launcher.log.llm_critical_download_error", default="❌ [LLM] Critical error: {error}", error=str(e)), "LLM")
            return False

    def install_sd(self):
        """Installs Stable Diffusion WebUI Forge"""
        try:
            self.log(t("ui.launcher.log.sd_cloning_repo", default="📥 [SD] Cloning Stable Diffusion Forge repository..."), "SD")
            
            # Backup models
            saved_models = None
            if os.path.exists(MODELS_SD_DIR):
                try:
                    temp_backup = os.path.join(DIR_TEMP, "sd_models_backup_temp")
                    if os.path.exists(temp_backup):
                        shutil.rmtree(temp_backup, ignore_errors=True)
                    os.makedirs(DIR_TEMP, exist_ok=True)
                    shutil.copytree(MODELS_SD_DIR, temp_backup)
                    saved_models = temp_backup
                except Exception as e:
                    self.log(t("ui.launcher.log.sd_models_save_failed", default="⚠️ [SD] Failed to backup models: {error}", error=str(e)), "SD")

            # Clone repo
            launch_script = os.path.join(SD_DIR, "launch.py")
            if not os.path.exists(SD_DIR):
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                
                result = subprocess.run(
                    [GIT_CMD, "clone", SD_REPO, SD_DIR],
                    capture_output=True, text=True, timeout=600,
                    creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo
                )
                
                if result.returncode != 0:
                    self.log(t("ui.launcher.log.sd_clone_error", default="❌ [SD] Clone error: {error}", error=result.stderr), "SD")
                    return False
                    
                if not os.path.exists(launch_script):
                    return False
            
            # Restore models
            if saved_models and os.path.exists(saved_models):
                try:
                    os.makedirs(MODELS_SD_DIR, exist_ok=True)
                    for item in os.listdir(saved_models):
                        src = os.path.join(saved_models, item)
                        dst = os.path.join(MODELS_SD_DIR, item)
                        if os.path.isdir(src):
                            if os.path.exists(dst): shutil.rmtree(dst, ignore_errors=True)
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)
                    shutil.rmtree(saved_models, ignore_errors=True)
                except:
                    pass

            # Clone ADetailer
            adetailer_dir = os.path.join(SD_DIR, "extensions", "adetailer")
            if not os.path.exists(adetailer_dir):
                os.makedirs(os.path.dirname(adetailer_dir), exist_ok=True)
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                subprocess.run(
                    [GIT_CMD, "clone", ADETAILER_REPO, adetailer_dir],
                    capture_output=True, text=True, timeout=300,
                    creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo
                )

            return True
        except Exception as e:
            self.log(t("ui.launcher.log.sd_install_error", default="❌ [SD] Install error: {error}", error=str(e)), "SD")
            return False

    def create_sd_venv(self):
        """Creates virtual environment for SD"""
        try:
            self.log(t("ui.launcher.log.sd_creating_venv", default="📦 [SD] Creating virtual environment..."), "SD")
            venv = os.path.join(SD_DIR, "venv")
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            # Create venv
            result = subprocess.run(
                [PYTHON_EXE, "-m", "venv", venv],
                cwd=SD_DIR, capture_output=True, text=True, timeout=60,
                creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo
            )
            
            if result.returncode != 0:
                self.log(t("ui.launcher.log.sd_venv_error", default="❌ [SD] Venv creation error: {error}", error=result.stderr), "SD")
                return False
                
            venv_py = os.path.join(venv, "Scripts", "python.exe")
            
            # Upgrade pip
            subprocess.run([venv_py, "-m", "pip", "install", "--upgrade", "pip"], 
                         capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
            
            # Check CUDA
            cuda_available = False
            try:
                check = subprocess.run(["nvidia-smi"], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo)
                if check.returncode == 0:
                    cuda_available = True
            except:
                pass

            # Install PyTorch
            if cuda_available:
                subprocess.run(
                    [venv_py, "-m", "pip", "install", "torch==2.1.2", "torchvision", "torchaudio", 
                     "--index-url", "https://download.pytorch.org/whl/cu121", "--no-cache-dir"],
                    capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo
                )
                # Xformers
                subprocess.run(
                    [venv_py, "-m", "pip", "install", "xformers", "--index-url", "https://download.pytorch.org/whl/cu121", "--no-cache-dir"],
                    capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo
                )
            else:
                subprocess.run(
                    [venv_py, "-m", "pip", "install", "torch", "torchvision", "torchaudio", "--no-cache-dir"],
                    capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, startupinfo=startupinfo
                )
            
            return True
        except Exception as e:
            self.log(t("ui.launcher.log.sd_venv_error", default="❌ [SD] Venv error: {error}", error=str(e)), "SD")
            return False


    def install_bot_dependencies(self):
        """Installs dependencies for the bot"""
        try:
            self.log(t("ui.launcher.log.bot_installing_deps", default="📦 [BOT] Installing dependencies..."), "BOT")
            
            requirements_file = os.path.join(BASE_DIR, "requirements.txt")
            if not os.path.exists(requirements_file):
                # Create default requirements if missing
                with open(requirements_file, "w") as f:
                    f.write("python-telegram-bot==20.7\n")
                    f.write("requests==2.31.0\n")
                    f.write("aiohttp==3.9.1\n")
                    f.write("python-dotenv==1.0.0\n")
                    f.write("Pillow==10.2.0\n")
                    f.write("psutil==5.9.8\n")
                    f.write("huggingface_hub>=0.23.0\n")
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            process = subprocess.Popen(
                [PYTHON_EXE, "-m", "pip", "install", "-r", requirements_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            # Read output to prevent blocking
            stdout, stderr = process.communicate()
            
            if process.returncode == 0:
                self.log(t("ui.launcher.log.bot_deps_success", default="✅ [BOT] Dependencies installed"), "BOT")
                return True
            else:
                self.log(t("ui.launcher.log.bot_deps_error", default="❌ [BOT] Dependencies error: {error}", error=stderr), "BOT")
                return False
                
        except Exception as e:
            self.log(t("ui.launcher.log.bot_deps_critical", default="❌ [BOT] Critical error: {error}", error=str(e)), "BOT")
            return False

class OneClickInstaller:
    def __init__(self, installer: Installer, log_callback: Callable[[str, str], None]):
        self.installer = installer
        self.log = log_callback
        self.steps = [
            ("check_python", t("ui.launcher.setup.step.python", default="Checking Python environment...")),
            ("check_git", t("ui.launcher.setup.step.git", default="Checking Git...")),
            ("install_ollama", t("ui.launcher.setup.step.ollama", default="Installing LLM Engine (Ollama)...")),
            ("install_sd", t("ui.launcher.setup.step.sd", default="Installing Image Generator (Stable Diffusion)...")),
            ("install_bot", t("ui.launcher.setup.step.bot", default="Installing Bot Dependencies..."))
        ]
        
    def run_installation(self, progress_callback: Callable[[int, str], None]) -> bool:
        """Runs the full installation process"""
        total_steps = len(self.steps)
        
        for i, (step_id, step_desc) in enumerate(self.steps):
            progress = int((i / total_steps) * 100)
            progress_callback(progress, step_desc)
            
            success = False
            try:
                if step_id == "check_python":
                    # Python is assumed to be present as launcher runs on it, 
                    # but we verify paths
                    if os.path.exists(PYTHON_EXE):
                        success = True
                    else:
                        # Should not happen if launcher is running
                        self.log("⚠️ Python path issue detected", "SYSTEM")
                        success = True # Proceed anyway
                        
                elif step_id == "check_git":
                    # Check if git is available
                    try:
                        subprocess.run([GIT_CMD, "--version"], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        success = True
                    except:
                        self.log("⚠️ Git not found, some features may fail", "SYSTEM")
                        # We might want to install git here if missing
                        success = True # Proceed for now
                        
                elif step_id == "install_ollama":
                    if os.path.exists(OLLAMA_EXE):
                        success = True
                    else:
                        success = self.installer.download_ollama()
                        
                elif step_id == "install_sd":
                    if os.path.exists(os.path.join(SD_DIR, "venv")):
                        success = True
                    else:
                        if self.installer.install_sd():
                            success = self.installer.create_sd_venv()
                        else:
                            success = False
                            
                elif step_id == "install_bot":
                    success = self.installer.install_bot_dependencies()
                    
            except Exception as e:
                self.log(f"❌ Error in step {step_id}: {e}", "SYSTEM")
                success = False
            
            if not success:
                self.log(f"❌ Installation failed at step: {step_desc}", "SYSTEM")
                return False
                
        progress_callback(100, t("ui.launcher.setup.complete", default="Installation Complete!"))
        return True
