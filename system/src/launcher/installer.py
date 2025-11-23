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
        DIR_TEMP, OLLAMA_EXE, OLLAMA_DIR, SD_DIR, GIT_CMD, 
        SD_REPO, MODELS_SD_DIR, ADETAILER_REPO, PYTHON_EXE
    )
except (ImportError, ValueError):
    from config import (
        DIR_TEMP, OLLAMA_EXE, OLLAMA_DIR, SD_DIR, GIT_CMD, 
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

