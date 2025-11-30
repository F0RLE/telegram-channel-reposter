"""
Direct Text Generation Module
Provides 1-to-1 text generation using local Ollama instance without Telegram bot dependency.
"""

import os
import requests
import json
from typing import Optional, Dict, Any


def get_env_path() -> str:
    """Get path to .env file"""
    appdata = os.environ.get("APPDATA", "")
    return os.path.join(appdata, "TelegramBotData", "data", "configs", ".env")


def get_setting(key: str, default: str = "") -> str:
    """Get setting from .env file"""
    env_path = get_env_path()
    if not os.path.exists(env_path):
        return default
    
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith(f'{key}='):
                    return line.split('=', 1)[1].strip().strip('"\'')
    except:
        pass
    return default


def generate_text_direct(
    prompt: str,
    model: Optional[str] = None,
    system_prompt: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> Dict[str, Any]:
    """
    Generate text directly using local Ollama instance.
    
    Args:
        prompt: User input text
        model: Ollama model name (default from settings or first available)
        system_prompt: System prompt (default from settings)
        temperature: Generation temperature (default from settings)
        max_tokens: Maximum tokens to generate
            temperature = float(get_setting("LLM_TEMPERATURE", "0.7"))
        except:
            temperature = 0.7
    
    # Dynamic model validation
    # If model is not specified or not found, try to find a valid one
    try:
        available = get_available_models()
        if available:
            if not model:
                model = available[0]
            elif model not in available:
                # Try fuzzy match
                found = False
                for m in available:
                    if model in m or m in model:
                        model = m
                        found = True
                        break
                if not found:
                    model = available[0]
    except:
        pass

    if not model:
         model = "qwen2.5:3b" # Fallback

    # Ollama API endpoint
    url = "http://localhost:11434/api/generate"
    
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,
        "temperature": temperature,
        "stream": False
    }
    
    if max_tokens:
        payload["options"] = {"num_predict": max_tokens}
    
    try:
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        
        return {
            "success": True,
            "response": result.get("response", ""),
            "model": model,
            "error": None
        }
    
    except requests.exceptions.ConnectionError:
        return {
            "success": False,
            "response": "",
            "model": model,
            "error": "❌ Не удалось подключиться к Ollama. Убедитесь, что Ollama запущена."
        }
    
    except requests.exceptions.Timeout:
        return {
            "success": False,
            "response": "",
            "model": model,
            "error": "⏱️ Превышено время ожидания ответа от Ollama."
        }
    
    except Exception as e:
        error_msg = str(e)
        # Check if model not found
        if "model" in error_msg.lower() and "not found" in error_msg.lower():
            return {
                "success": False,
                "response": "",
                "model": model,
                "error": f"❌ Модель '{model}' не найдена в Ollama.\n\nУстановите её командой:\nollama pull {model}"
            }
        return {
            "success": False,
            "response": "",
            "model": model,
            "error": f"❌ Ошибка генерации: {error_msg}"
        }


def get_available_models() -> list:
    """Get list of available Ollama models"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        return [m["name"] for m in models]
    except:
        return []


def check_ollama_running() -> bool:
    """Check if Ollama is running"""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except:
        return False
