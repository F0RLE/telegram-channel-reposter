"""
Auto-updater module for Telegram Channel Reposter
Checks GitHub for updates and downloads them
"""
import os
import sys
import json
import threading
import subprocess
import urllib.request
import zipfile
import shutil
from typing import Optional, Callable, Tuple
from datetime import datetime

# GitHub repository info
GITHUB_REPO = "F0RLE/telegram-channel-reposter"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_COMMITS_URL = f"https://api.github.com/repos/{GITHUB_REPO}/commits/main"

# Version file
VERSION_FILE = os.path.join(os.environ.get("APPDATA", ""), "TelegramBotData", "data", "configs", "version.json")

class Updater:
    """Auto-updater for the application"""
    
    def __init__(self, log_callback: Callable = None):
        self.log_callback = log_callback or print
        self.current_version = self._load_version()
        self.update_available = False
        self.latest_version = None
        self.latest_commit = None
        self.download_url = None
        self.update_info = None
    
    def _load_version(self) -> dict:
        """Load current version info"""
        default = {
            "version": "1.1.0",
            "commit": None,
            "updated_at": None
        }
        try:
            if os.path.exists(VERSION_FILE):
                with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return default
    
    def _save_version(self, version: str, commit: str = None):
        """Save version info"""
        try:
            os.makedirs(os.path.dirname(VERSION_FILE), exist_ok=True)
            data = {
                "version": version,
                "commit": commit,
                "updated_at": datetime.now().isoformat()
            }
            with open(VERSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except:
            pass
    
    def check_for_updates(self, callback: Callable = None) -> bool:
        """
        Check GitHub for updates
        Returns True if update is available
        """
        def check():
            try:
                # Check latest commit
                req = urllib.request.Request(
                    GITHUB_COMMITS_URL,
                    headers={'User-Agent': 'TelegramChannelReposter/1.0'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    latest_commit = data.get('sha', '')[:7]
                    commit_message = data.get('commit', {}).get('message', '')
                    commit_date = data.get('commit', {}).get('committer', {}).get('date', '')
                    
                    self.latest_commit = latest_commit
                    self.update_info = {
                        'commit': latest_commit,
                        'message': commit_message.split('\n')[0],  # First line
                        'date': commit_date
                    }
                    
                    # Check if we have a newer commit
                    current_commit = self.current_version.get('commit')
                    if current_commit and current_commit != latest_commit:
                        self.update_available = True
                        self.download_url = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip"
                    elif not current_commit:
                        # First run or no commit info
                        self.update_available = True
                        self.download_url = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip"
                    else:
                        self.update_available = False
                    
                    if callback:
                        callback(self.update_available, self.update_info)
                    return self.update_available
                    
            except Exception as e:
                self.log_callback(f"❌ [UPDATE] Ошибка проверки обновлений: {e}")
                if callback:
                    callback(False, None)
                return False
        
        # Run in thread
        thread = threading.Thread(target=check, daemon=True)
        thread.start()
        return True
    
    def download_update(self, progress_callback: Callable = None, complete_callback: Callable = None):
        """
        Download update from GitHub
        progress_callback(percent, status_text)
        complete_callback(success, message)
        """
        def download():
            try:
                if not self.download_url:
                    if complete_callback:
                        complete_callback(False, "URL обновления не найден")
                    return
                
                if progress_callback:
                    progress_callback(0, "Начинаем загрузку...")
                
                # Create temp directory
                temp_dir = os.path.join(os.environ.get("APPDATA", ""), "TelegramBotData", "temp", "update")
                os.makedirs(temp_dir, exist_ok=True)
                
                zip_path = os.path.join(temp_dir, "update.zip")
                
                # Download with progress
                req = urllib.request.Request(
                    self.download_url,
                    headers={'User-Agent': 'TelegramChannelReposter/1.0'}
                )
                
                with urllib.request.urlopen(req, timeout=60) as response:
                    total_size = int(response.headers.get('content-length', 0))
                    downloaded = 0
                    block_size = 8192
                    
                    with open(zip_path, 'wb') as f:
                        while True:
                            buffer = response.read(block_size)
                            if not buffer:
                                break
                            f.write(buffer)
                            downloaded += len(buffer)
                            
                            if total_size > 0 and progress_callback:
                                percent = int((downloaded / total_size) * 50)  # 0-50%
                                progress_callback(percent, f"Загрузка... {downloaded // 1024} KB")
                
                if progress_callback:
                    progress_callback(50, "Распаковка...")
                
                # Extract update
                extract_dir = os.path.join(temp_dir, "extracted")
                if os.path.exists(extract_dir):
                    shutil.rmtree(extract_dir)
                
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                if progress_callback:
                    progress_callback(70, "Применение обновления...")
                
                # Find extracted folder
                extracted_folders = os.listdir(extract_dir)
                if not extracted_folders:
                    if complete_callback:
                        complete_callback(False, "Архив пустой")
                    return
                
                source_dir = os.path.join(extract_dir, extracted_folders[0])
                
                # Get project root (go up from launcher dir)
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
                
                # Copy files (excluding some)
                exclude_files = ['.env', 'analytics.json', 'version.json', 'channels.json', 'generation_config.json']
                exclude_dirs = ['__pycache__', '.git', 'venv', 'env']
                
                files_updated = 0
                for root, dirs, files in os.walk(source_dir):
                    # Filter directories
                    dirs[:] = [d for d in dirs if d not in exclude_dirs]
                    
                    rel_path = os.path.relpath(root, source_dir)
                    dest_root = os.path.join(project_root, rel_path) if rel_path != '.' else project_root
                    
                    # Create directory
                    os.makedirs(dest_root, exist_ok=True)
                    
                    for file in files:
                        if file in exclude_files:
                            continue
                        
                        src_file = os.path.join(root, file)
                        dest_file = os.path.join(dest_root, file)
                        
                        try:
                            shutil.copy2(src_file, dest_file)
                            files_updated += 1
                        except (PermissionError, OSError):
                            pass  # Skip locked files
                
                if progress_callback:
                    progress_callback(90, "Завершение...")
                
                # Save new version
                if self.latest_commit:
                    self._save_version("1.0.0", self.latest_commit)
                
                # Cleanup
                try:
                    shutil.rmtree(temp_dir)
                except:
                    pass
                
                if progress_callback:
                    progress_callback(100, "Готово!")
                
                if complete_callback:
                    complete_callback(True, f"Обновление установлено! Обновлено файлов: {files_updated}")
                
            except Exception as e:
                self.log_callback(f"❌ [UPDATE] Ошибка загрузки: {e}")
                if complete_callback:
                    complete_callback(False, str(e))
        
        # Run in thread
        thread = threading.Thread(target=download, daemon=True)
        thread.start()
    
    def get_current_version(self) -> str:
        """Get current version string"""
        commit = self.current_version.get('commit', 'unknown')
        return f"v{self.current_version.get('version', '1.1.0')} ({commit[:7] if commit else '?'})"
    
    def mark_as_updated(self, commit: str = None):
        """Mark current version as updated"""
        self._save_version(
            self.current_version.get('version', '1.1.0'),
            commit or self.latest_commit
        )
        self.update_available = False


# Global updater instance
_updater = None

def get_updater(log_callback: Callable = None) -> Updater:
    """Get global updater instance"""
    global _updater
    if _updater is None:
        _updater = Updater(log_callback)
    return _updater

