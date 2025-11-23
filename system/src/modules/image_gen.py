import asyncio
import base64
import logging
import aiohttp
from typing import Dict, Any, Optional, Tuple

from aiogram import Bot

# Import Settings from config
from config.settings import (
    SD_API_URL, 
    IMAGE_GENERATION_TIMEOUT,
    SD_STEPS,
    SD_CFG,
    SD_WIDTH,
    SD_HEIGHT,
    SD_SAMPLER,
    SD_SCHEDULER,
    SD_POSITIVE_PROMPT_PREFIX,
    SD_NEGATIVE_PROMPT_DEFAULT,
    ADETAILER_FACE_CONFIG,
    ADETAILER_HAND_CONFIG,
    ADETAILER_PERSON_CONFIG,
    ADETAILER_CLOTHING_CONFIG
)

logger = logging.getLogger(__name__)

async def _async_sd_api_request(payload: Dict[str, Any], timeout: int, max_retries: int = 2) -> Dict[str, Any]:
    """
    Sends a POST request to the SD WebUI API with retry mechanism and rate limiting.
    
    Args:
        payload: Request payload dictionary
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        
    Returns:
        Response JSON dictionary
        
    Raises:
        RuntimeError: On API errors or connection failures
    """
    from core.error_handler import retry_with_backoff, RetryConfig, ErrorHandler
    from launcher.core.rate_limiter import sd_rate_limiter
    
    # Apply rate limiting
    await sd_rate_limiter.acquire("sd_api")
    
    logger.info(f"SD Request: {payload['width']}x{payload['height']}, Steps: {payload['steps']}")
    
    retry_config = RetryConfig(
        max_attempts=max_retries,
        initial_delay=2.0,
        max_delay=30.0,
        retryable_exceptions=(aiohttp.ClientError, asyncio.TimeoutError, RuntimeError)
    )
    
    @retry_with_backoff(config=retry_config)
    async def _make_request():
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            # Use ssl=False for local connections (127.0.0.1)
            async with session.post(SD_API_URL, json=payload, ssl=False) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    error_msg = f"API Error {resp.status}: {text}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)
                return await resp.json()
    
    try:
        return await _make_request()
    except aiohttp.ClientConnectorError as e:
        error_msg = ErrorHandler.handle_api_error(
            e,
            "Не удалось подключиться к Stable Diffusion. Проверьте, запущен ли он в Лаунчере (порт 7860)."
        )
        raise RuntimeError(error_msg)
    except Exception as e:
        error_msg = ErrorHandler.handle_api_error(e, "Ошибка запроса к Stable Diffusion API")
        raise RuntimeError(error_msg)

async def async_generate_stable_diffusion_image(
    bot: Bot,
    chat_id: int,
    animation_msg_id: int,
    prompt: str,
    user_id: int,
    progress_task: asyncio.Task,
    neg_prompt: Optional[str] = None,
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Main generation function with Full ADetailer Pipeline (4 passes).
    
    Args:
        bot: Telegram bot instance
        chat_id: Chat ID for sending messages
        animation_msg_id: Message ID for progress animation
        prompt: Image generation prompt
        user_id: User ID for logging
        progress_task: Task for progress animation
        neg_prompt: Optional negative prompt
        
    Returns:
        Tuple of (image_bytes, prompt) or (None, None) on error
    """
    
    from core.monitoring import record_api_call
    import time
    
    start_time = time.time()
    logger.info(f"Generating for user {user_id}...")

    # Construct Prompt
    full_prompt = f"{SD_POSITIVE_PROMPT_PREFIX}{prompt}, highly detailed, masterpiece, best quality, 8k"
    full_neg_prompt = (
        f"{SD_NEGATIVE_PROMPT_DEFAULT}, {neg_prompt}" if neg_prompt else SD_NEGATIVE_PROMPT_DEFAULT
    )

    # Payload construction
    payload = {
        "prompt": full_prompt,
        "negative_prompt": full_neg_prompt,
        "width": SD_WIDTH,  
        "height": SD_HEIGHT,
        "steps": SD_STEPS,
        "cfg_scale": SD_CFG,
        "sampler_name": SD_SAMPLER,
        "scheduler": SD_SCHEDULER,
        "seed": -1,
        "batch_size": 1,
        "alwayson_scripts": {
            "ADetailer": {
                "args": [
                    True,                    # Enable
                    ADETAILER_FACE_CONFIG,   # Pass 1
                    ADETAILER_HAND_CONFIG,   # Pass 2
                    ADETAILER_PERSON_CONFIG, # Pass 3
                    ADETAILER_CLOTHING_CONFIG # Pass 4
                ]
            }
        }
    }

    error_message = "Неизвестная ошибка."
    
    try:
        # Call API
        result = await _async_sd_api_request(payload, IMAGE_GENERATION_TIMEOUT)

        if not result or "images" not in result or not result["images"]:
            raise RuntimeError("API вернул пустой результат.")

        # Decode Image
        img_data = base64.b64decode(result["images"][0])
        duration = time.time() - start_time
        record_api_call("sd", True, duration)
        logger.info("Generation success.")
        return img_data, prompt

    except Exception as e:
        duration = time.time() - start_time
        record_api_call("sd", False, duration)
        record_error("sd_generation", str(e))
        error_message = str(e)
        logger.error(f"Gen Fail: {e}")
    
    finally:
        # Stop animation
        if progress_task and not progress_task.done():
            progress_task.cancel()

    # Show error UI
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=animation_msg_id,
            text=f"❌ <b>Ошибка генерации:</b>\n{error_message}",
            parse_mode="HTML"
        )
    except Exception:
        pass 

    return None, None