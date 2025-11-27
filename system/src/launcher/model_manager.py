"""
Model management module for launcher
Handles Ollama models, GGUF files, and SD models
"""
import os
import subprocess
from typing import List, Dict, Optional

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
    from .config import OLLAMA_EXE, OLLAMA_DIR, OLLAMA_MODELS_DIR, MODELS_LLM_DIR
except (ImportError, ValueError):
    from config import OLLAMA_EXE, OLLAMA_DIR, OLLAMA_MODELS_DIR, MODELS_LLM_DIR


class ModelManager:
    """Manages LLM models (Ollama and GGUF)"""
    
    def __init__(self, log_callback=None):
        """
        Initialize ModelManager
        
        Args:
            log_callback: Optional callback function for logging (log(message, tag))
        """
        self.log = log_callback or (lambda msg, tag="MODEL": print(f"[{tag}] {msg}"))
    
    def get_ollama_models(self) -> List[str]:
        """Get list of Ollama models"""
        models = []
        try:
            if not os.path.exists(OLLAMA_EXE):
                return models  # Ollama not installed
            
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            result = subprocess.run(
                [OLLAMA_EXE, "list"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=OLLAMA_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines[1:]:  # Skip header
                    if line.strip():
                        parts = line.split()
                        if parts:
                            model_name = parts[0]
                            models.append(model_name)
        except Exception:
            # Don't log error, just return empty list
            pass
        return models
    
    def get_gguf_models(self) -> List[Dict[str, str]]:
        """Get list of GGUF files from models directory"""
        models = []
        try:
            if os.path.exists(MODELS_LLM_DIR):
                for file in os.listdir(MODELS_LLM_DIR):
                    if file.lower().endswith('.gguf'):
                        file_path = os.path.join(MODELS_LLM_DIR, file)
                        if os.path.isfile(file_path):
                            models.append({
                                'name': os.path.splitext(file)[0],
                                'file': file,
                                'path': file_path,
                                'type': 'gguf'
                            })
        except Exception as e:
            self.log(t("ui.launcher.log.gguf_scan_error", default="⚠️ [LLM] Ошибка при сканировании GGUF файлов: {error}", error=str(e)), "LLM")
        return models
    
    def check_ollama_model(self, model_name: str) -> bool:
        """Check if model exists in Ollama"""
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            # Run ollama list to check models
            result = subprocess.run(
                [OLLAMA_EXE, "list"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=OLLAMA_DIR,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            if result.returncode == 0:
                return model_name in result.stdout
            return False
        except Exception:
            return False
    
    def import_gguf_to_ollama(self, model_path: str, model_name: str, env: Optional[Dict] = None) -> bool:
        """
        Automatically import GGUF model into Ollama
        
        Args:
            model_path: Path to GGUF file
            model_name: Model name for Ollama
            env: Environment variables dictionary (if None, uses current environment)
        
        Returns:
            True if import successful, False otherwise
        """
        try:
            # Create Modelfile for GGUF import
            modelfile_path = os.path.join(OLLAMA_DIR, f"{model_name}.Modelfile")
            
            with open(modelfile_path, 'w', encoding='utf-8') as f:
                f.write(f"FROM {model_path}\n")
                f.write("TEMPLATE \"\"\"{{ .Prompt }}\"\"\"\n")
                f.write("PARAMETER temperature 0.7\n")
                f.write("PARAMETER top_p 0.9\n")
            
            # Import model (DO NOT close processes - they are managed by calling code)
            self.log(t("ui.launcher.log.importing_model", default="📦 [LLM] Импорт модели {model}...", model=model_name), "LLM")
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            # Use passed environment or current
            import_env = env if env else os.environ.copy()
            
            result = subprocess.run(
                [OLLAMA_EXE, "create", model_name, "-f", modelfile_path],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=OLLAMA_DIR,
                env=import_env,
                creationflags=subprocess.CREATE_NO_WINDOW,
                startupinfo=startupinfo
            )
            
            if result.returncode == 0:
                self.log(t("ui.launcher.log.model_imported", default="✅ [LLM] Модель {model} успешно импортирована", model=model_name), "LLM")
                return True
            else:
                self.log(t("ui.launcher.log.import_error", default="⚠️ [LLM] Ошибка импорта: {error}", error=result.stderr), "LLM")
                return False
        except Exception as e:
            self.log(t("ui.launcher.log.import_exception", default="❌ [LLM] Ошибка при импорте модели: {error}", error=str(e)), "LLM")
            return False

    def download_from_hf(self, repo_id: str, filename: Optional[str] = None, local_dir: Optional[str] = None) -> Optional[str]:
        """
        Download model from Hugging Face Hub
        
        Args:
            repo_id: Hugging Face repository ID (e.g. 'Qwen/Qwen3-8B')
            filename: Optional filename to download. If None, downloads entire repo (snapshot)
            local_dir: Directory to save files. If None, uses default cache or MODELS_LLM_DIR
            
        Returns:
            Path to downloaded file or directory, or None if failed
        """
        try:
            from huggingface_hub import snapshot_download, hf_hub_download
        except ImportError:
            self.log(t("ui.launcher.log.hf_hub_missing", default="❌ Hugging Face Hub library not found. Please install requirements."), "MODEL")
            return None

        try:
            self.log(t("ui.launcher.log.hf_download_start", default="⬇️ [HF] Starting download for {repo}...", repo=repo_id), "MODEL")
            
            # Use provided local_dir or default to MODELS_LLM_DIR if not specified
            # Note: snapshot_download defaults to ~/.cache/huggingface if local_dir is None
            # If we want to force it to our models dir, we should specify it.
            # But the user said "Default to local cache", so maybe we leave it as None unless specified?
            # However, for our system, we probably want it in our managed directory if it's a GGUF file.
            # For now, I'll respect the argument.
            
            if filename:
                # Download single file
                result_path = hf_hub_download(repo_id=repo_id, filename=filename, local_dir=local_dir)
                self.log(t("ui.launcher.log.hf_download_file_success", default="✅ [HF] File downloaded: {path}", path=result_path), "MODEL")
                return result_path
            else:
                # Download entire repo
                result_path = snapshot_download(repo_id=repo_id, local_dir=local_dir)
                self.log(t("ui.launcher.log.hf_download_repo_success", default="✅ [HF] Model downloaded to: {path}", path=result_path), "MODEL")
                return result_path
                
        except Exception as e:
            self.log(t("ui.launcher.log.hf_download_error", default="❌ [HF] Download error: {error}", error=str(e)), "MODEL")
            return None



