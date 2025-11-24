import logging
import re
import asyncio
import aiohttp
import os
import json
from typing import Optional, Dict, Any

# Import settings
from config.settings import (
    OLLAMA_API_BASE, 
    OLLAMA_MODEL, 
    OLLAMA_API_KEY,
    LLM_TEMP,
    LLM_CTX,
    LLM_REWRITE_SYSTEM_PROMPT,
    LLM_REWRITE_USER_PROMPT,
    LLM_REWRITE_CLICHES,
    GEN_CONFIG_PATH
)

# Кэш для настроек переписывания
_cached_rewrite_settings = None
_cached_settings_mtime = None

def _reload_rewrite_settings():
    """Перезагружает настройки переписывания из файла"""
    global _cached_rewrite_settings, _cached_settings_mtime
    
    try:
        # Проверяем время модификации файла
        if os.path.exists(GEN_CONFIG_PATH):
            current_mtime = os.path.getmtime(GEN_CONFIG_PATH)
            if _cached_settings_mtime == current_mtime and _cached_rewrite_settings:
                # Настройки не изменились, используем кэш
                return _cached_rewrite_settings
            
            # Загружаем новые настройки
            with open(GEN_CONFIG_PATH, 'r', encoding='utf-8') as f:
                gen_cfg = json.load(f)
            
            system_prompt = gen_cfg.get("llm_rewrite_system_prompt", LLM_REWRITE_SYSTEM_PROMPT)
            user_prompt = gen_cfg.get("llm_rewrite_user_prompt", LLM_REWRITE_USER_PROMPT)
            cliches_raw = gen_cfg.get("llm_rewrite_cliches", None)
            
            # Parse cliches - может быть строка или список
            if cliches_raw is None:
                # Используем значение по умолчанию из settings
                if isinstance(LLM_REWRITE_CLICHES, list):
                    cliches = LLM_REWRITE_CLICHES
                elif isinstance(LLM_REWRITE_CLICHES, str):
                    cliches = [c.strip() for c in LLM_REWRITE_CLICHES.split(",") if c.strip()]
                else:
                    cliches = []
            elif isinstance(cliches_raw, str):
                cliches = [c.strip() for c in cliches_raw.split(",") if c.strip()]
            elif isinstance(cliches_raw, list):
                cliches = cliches_raw
            else:
                cliches = []
            
            _cached_rewrite_settings = {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "cliches": cliches
            }
            _cached_settings_mtime = current_mtime
            
            logger.info(f"✅ Настройки переписывания перезагружены из файла")
            logger.debug(f"📋 Системный промпт: {system_prompt[:150]}...")
            logger.debug(f"📋 Пользовательский промпт: {user_prompt[:150]}...")
            logger.debug(f"📋 Клише: {cliches}")
            return _cached_rewrite_settings
    except Exception as e:
        logger.warning(f"⚠️ Ошибка перезагрузки настроек переписывания: {e}, используем значения по умолчанию")
    
    # Возвращаем значения по умолчанию
    default_cliches = LLM_REWRITE_CLICHES
    if isinstance(default_cliches, str):
        default_cliches = [c.strip() for c in default_cliches.split(",") if c.strip()]
    elif not isinstance(default_cliches, list):
        default_cliches = []
    
    return {
        "system_prompt": LLM_REWRITE_SYSTEM_PROMPT,
        "user_prompt": LLM_REWRITE_USER_PROMPT,
        "cliches": default_cliches
    }

logger = logging.getLogger(__name__)

# ==========================================
# 1. HELPERS
# ==========================================

def _build_payload(prompt: str, system: Optional[str] = None, temp: float = 0.7) -> Dict[str, Any]:
    """
    Constructs the JSON payload for OpenAI-compatible API (Ollama/Llama.cpp).
    """
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    
    # Validate model name
    model_name = OLLAMA_MODEL if OLLAMA_MODEL and OLLAMA_MODEL.strip() else "local-model"
    if not model_name or model_name == "local-model":
        logger.warning(f"⚠️ Using default model name 'local-model'. Make sure SELECTED_LLM_MODEL is set in .env")
    
    return {
        "model": model_name,
        "messages": messages,
        "temperature": temp,
        "max_tokens": LLM_CTX, # Context window limit
    }

async def _safe_request(payload: Dict[str, Any], max_retries: int = 3) -> Optional[str]:
    """
    Sends async request to LLM server with retry mechanism and rate limiting.
    
    Args:
        payload: Request payload dictionary
        max_retries: Maximum number of retry attempts
        
    Returns:
        Response content string or None on error
    """
    from core.error_handler import retry_with_backoff, RetryConfig, ErrorHandler
    from launcher.core.rate_limiter import llm_rate_limiter
    
    # Apply rate limiting
    await llm_rate_limiter.acquire("llm_api")
    
    headers = {
        "Authorization": f"Bearer {OLLAMA_API_KEY}", 
        "Content-Type": "application/json"
    }
    url = f"{OLLAMA_API_BASE}/chat/completions"
    
    retry_config = RetryConfig(
        max_attempts=max_retries,
        initial_delay=1.0,
        max_delay=10.0,
        retryable_exceptions=(aiohttp.ClientError, asyncio.TimeoutError)
    )
    
    @retry_with_backoff(config=retry_config)
    async def _make_request():
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
            # Use ssl=False for local connections (127.0.0.1)
            async with session.post(url, json=payload, headers=headers, ssl=False) as response:
                if response.status != 200:
                    err_text = await response.text()
                    error_msg = f"LLM API Error {response.status}: {err_text}"
                    logger.error(error_msg)
                    raise aiohttp.ClientResponseError(
                        request_info=response.request_info,
                        history=response.history,
                        status=response.status,
                        message=error_msg
                    )
                
                data = await response.json()
                # Extract content from OpenAI-format response
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                if not content:
                    raise ValueError("Empty response from LLM")
                return content
    
    try:
        return await _make_request()
    except aiohttp.ClientConnectorError:
        error_msg = ErrorHandler.handle_api_error(
            Exception("Connection failed"),
            "Не удалось подключиться к LLM. Проверьте, запущен ли сервер (порт 11434)."
        )
        logger.error(error_msg)
        return None
    except Exception as e:
        error_msg = ErrorHandler.handle_api_error(e, "Ошибка запроса к LLM")
        logger.error(error_msg)
        return None

# ==========================================
# 2. REWRITE LOGIC
# ==========================================

async def rewrite_text(post_text: str) -> Optional[str]:
    """
    Rewrites text to make it engaging.
    Expected format: "Title ||| Body"
    
    Args:
        post_text: Original text to rewrite
        
    Returns:
        Rewritten text in HTML format with bold title, or original text on error
    """
    # Перезагружаем настройки перед каждым запросом (на случай изменения в лаунчере)
    settings = _reload_rewrite_settings()
    
    # Use cliches from settings
    CLICHES = [re.escape(c.strip()) for c in settings["cliches"] if c.strip()] if settings["cliches"] else []

    # Use system prompt from settings
    system = settings["system_prompt"]
    if not system or not system.strip():
        logger.warning("⚠️ Системный промпт пуст, используем значение по умолчанию")
        system = LLM_REWRITE_SYSTEM_PROMPT

    # Use user prompt from settings, replacing {text} placeholder
    user_prompt_template = settings["user_prompt"]
    if not user_prompt_template or not user_prompt_template.strip():
        logger.warning("⚠️ Пользовательский промпт пуст, используем значение по умолчанию")
        user_prompt_template = LLM_REWRITE_USER_PROMPT
    
    prompt = user_prompt_template.replace("{text}", post_text.strip())
    
    # Логируем используемые промпты для отладки
    logger.info(f"📝 Переписывание текста (длина: {len(post_text)} символов)")
    logger.debug(f"📝 Системный промпт: {system[:200]}...")
    logger.debug(f"📝 Пользовательский промпт: {prompt[:200]}...")
    logger.debug(f"📝 Клише для удаления: {CLICHES}")
    
    # Use temperature from settings
    payload = _build_payload(prompt, system, temp=LLM_TEMP)
    logger.debug(f"📤 Отправка запроса к LLM: model={payload['model']}, temp={payload['temperature']}")
    
    from core.monitoring import record_api_call, record_error
    import time
    
    start_time = time.time()
    res = await _safe_request(payload)
    duration = time.time() - start_time
    
    if not res:
        logger.error("❌ LLM вернул пустой ответ")
        record_api_call("llm", False, duration)
        record_error("llm_rewrite", "empty_response")
        return post_text # Fallback to original
    
    logger.info(f"✅ LLM ответ получен за {duration:.2f}с, длина ответа: {len(res)} символов")
    logger.debug(f"📥 Ответ LLM: {res[:300]}...")
    
    record_api_call("llm", True, duration)

    # Post-processing
    text = res
    if CLICHES:
        original_text = text
        for c in CLICHES:
            text = re.sub(c, '', text, flags=re.IGNORECASE)
        if text != original_text:
            logger.debug(f"🧹 Удалены клише из текста")

    # Remove system artifacts, but KEEP markdown (*, `) for HTML parser
    text = re.sub(r"[#@][a-zA-Z0-9_]+", '', text) # Remove hashtags/mentions
    text = text.replace('«', '"').replace('»', '"').strip()

    # Try splitting by separator
    parts = text.split('|||', 1)
    
    if len(parts) == 2:
        title = parts[0].strip()
        body = parts[1].strip()
        # Format: Bold Title + Body
        return f"<b>{title}</b>\n\n{body}"
    else:
        # Fallback: Try splitting by first double newline
        parts = text.split('\n\n', 1)
        if len(parts) == 2:
             return f"<b>{parts[0].strip()}</b>\n\n{parts[1].strip()}"
        
        return text.strip()

# ==========================================
# 3. PROMPT ENGINEERING
# ==========================================

async def create_image_prompt(post_text: str) -> Optional[str]:
    """
    Generates a Stable Diffusion prompt based on text.
    
    Args:
        post_text: Text to generate prompt from (max 1000 chars)
        
    Returns:
        Generated prompt string or None on error
    """
    if not post_text:
        logger.warning("⚠️ Пустой текст для генерации промпта изображения")
        return None

    logger.info(f"🎨 Генерация промпта для изображения из текста (длина: {len(post_text)} символов)")

    system = (
        "You are a Stable Diffusion prompt engineer. "
        "Create a detailed, comma-separated English prompt describing the visual subject of the text. "
        "Include lighting, style (realistic, 8k), and mood. "
        "Output ONLY the prompt."
    )

    from core.monitoring import record_api_call
    import time
    
    instruction = f"Text:\n{post_text[:1000]}\n\nCreate visual prompt:"
    payload = _build_payload(instruction, system, temp=0.7)
    
    logger.debug(f"📤 Отправка запроса на генерацию промпта: {instruction[:200]}...")
    
    start_time = time.time()
    res = await _safe_request(payload)
    duration = time.time() - start_time
    record_api_call("llm", res is not None, duration)
    
    if not res:
        logger.error("❌ LLM не вернул промпт для изображения")
        return None

    logger.debug(f"📥 Получен ответ от LLM для промпта: {res[:200]}...")

    # Cleanup
    original_res = res
    res = re.sub(r'^(prompt:|result:)\s*', '', res, flags=re.I)
    res = res.replace('\n', ' ').replace('"', '').strip()
    
    if res != original_res:
        logger.debug(f"🧹 Очищен промпт: {res[:200]}...")
    
    logger.info(f"✅ Сгенерирован промпт для изображения: {res[:100]}...")
    return res

# ==========================================
# 4. TRANSLATION
# ==========================================

async def translate_prompt_to_english(text: str) -> Optional[str]:
    """
    Translates user input to English for SD.
    Uses low temperature for accuracy.
    
    Args:
        text: Text to translate
        
    Returns:
        English translation or original text if already English/on error
    """
    if not text: return None

    # If text is already ASCII (English), skip LLM
    if text.isascii():
        return text

    system = (
        "You are a translator. Translate the input text into English for an image generator. "
        "Be concise and precise. Output ONLY the English translation."
    )

    from core.monitoring import record_api_call
    import time
    
    payload = _build_payload(f"Input:\n{text.strip()}", system, temp=0.3)
    
    start_time = time.time()
    res = await _safe_request(payload)
    duration = time.time() - start_time
    record_api_call("llm", res is not None, duration)
    
    return res.strip() if res else text