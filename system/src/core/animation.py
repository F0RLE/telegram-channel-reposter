import asyncio
import logging
import time
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramRetryAfter

logger = logging.getLogger(__name__)

# Frames for the loading spinner animation
SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

async def animate_message(
    bot: Bot, 
    chat_id: int, 
    message_id: int, 
    process_name: str = "Загрузка",
    is_media_message: bool = False 
):
    """
    Updates a message periodically to show a spinner and elapsed time.
    Run this as an asyncio.Task and cancel it when the process is done.
    """
    start_time = time.time()
    frame_idx = 0
    
    # Template: "Title" \n "Spinner ⏳ X sec."
    text_template = "<b>{name}</b>\n\n<code>{spinner}</code> ⏳ {elapsed} сек."

    async def _do_edit(text_to_edit: str):
        try:
            if is_media_message:
                await bot.edit_message_caption(
                    chat_id=chat_id, message_id=message_id, 
                    caption=text_to_edit, parse_mode="HTML"
                )
            else:
                await bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id, 
                    text=text_to_edit, parse_mode="HTML"
                )
        except TelegramBadRequest:
            # Message is not modified or deleted - ignore
            pass
        except TelegramRetryAfter as e:
            # Flood limit hit - wait
            await asyncio.sleep(e.retry_after)
        except Exception:
            pass

    try:
        while True:
            elapsed = int(time.time() - start_time)
            spinner = SPINNER_FRAMES[frame_idx % len(SPINNER_FRAMES)]
            
            new_text = text_template.format(
                name=process_name,
                spinner=spinner,
                elapsed=elapsed
            )

            await _do_edit(new_text)

            frame_idx += 1
            
            # Update interval: 1.0 second (User Request)
            await asyncio.sleep(1.0) 

    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Animation error: {e}")