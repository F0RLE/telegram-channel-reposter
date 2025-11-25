import os
import json
import logging
from typing import List, Union, Optional
from aiogram import Bot

logger = logging.getLogger(__name__)

# Import after logger to avoid circular imports
try:
    from config.settings import PUBLISHED_POSTS_FILE
except ImportError:
    # Fallback for when config is not available
    PUBLISHED_POSTS_FILE = None

def load_published_posts() -> List[str]:
    """
    Loads the list of already published URLs/IDs.
    Returns an empty list if file doesn't exist or is corrupted.
    
    Returns:
        List of published post URLs/IDs
    """
    if not PUBLISHED_POSTS_FILE or not os.path.exists(PUBLISHED_POSTS_FILE):
        return []
    try:
        with open(PUBLISHED_POSTS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Validate that it's a list of strings
            if isinstance(data, list):
                return [str(item) for item in data if item]
            return []
    except Exception as e:
        logger.error(f"Ошибка загрузки базы постов: {e}")
        return []

def save_published_posts(links: List[str]) -> None:
    """
    Saves the list of published links using Atomic Write (Safe Save).
    Writes to a temp file first, then renames it to prevent data corruption.
    
    Args:
        links: List of published post URLs/IDs to save
    """
    if not PUBLISHED_POSTS_FILE:
        logger.warning("PUBLISHED_POSTS_FILE not configured, skipping save")
        return
    
    # Ensure directory exists
    folder = os.path.dirname(PUBLISHED_POSTS_FILE)
    if folder and not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)

    # Temp file path
    temp_file = PUBLISHED_POSTS_FILE + ".tmp"

    try:
        # Write to temp file
        with open(temp_file, 'w', encoding='utf-8') as f:
            json.dump(links, f, indent=4, ensure_ascii=False)
        
        # Atomic replace
        os.replace(temp_file, PUBLISHED_POSTS_FILE)
        
    except Exception as e:
        logger.error(f"Критическая ошибка сохранения базы: {e}")
        # Clean up temp file if failed
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass


async def safe_delete_message(
    bot: Bot, 
    chat_id: int, 
    msg_ids: Union[int, List[int], None]
) -> None:
    """
    Safely deletes one or multiple messages.
    Centralized utility function to avoid code duplication.
    
    Args:
        bot: Telegram bot instance
        chat_id: Chat ID where messages are located
        msg_ids: Single message ID, list of IDs, or None
    """
    if not msg_ids:
        return
    
    if isinstance(msg_ids, int):
        msg_ids = [msg_ids]
    
    for mid in set(msg_ids):
        if not mid:
            continue
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception as e:
            # Log unexpected errors but don't fail
            if "message to delete not found" not in str(e).lower():
                logger.warning(f"Error deleting message {mid}: {e}")