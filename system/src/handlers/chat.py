"""Chat handler for LLM conversation mode"""
import logging
import asyncio
import re
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from core.fsm_states import FormState
from core.animation import animate_message
from modules.llm import rewrite_text, translate_prompt_to_english
from modules.image_gen import async_generate_stable_diffusion_image
from keyboards.inline import main_menu_keyboard
from config.settings import OLLAMA_API_BASE, OLLAMA_MODEL

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(F.chat.type == "private")

# Ключевые слова для определения запроса на генерацию изображения
IMAGE_GENERATION_KEYWORDS = [
    r"нарисуй",
    r"сгенерируй.*(изображение|картинк|фото|image)",
    r"создай.*(изображение|картинк|фото|image)",  
    r"покажи.*(как выглядит)",
    r"визуализируй",
    r"generate.*image",
    r"create.*image",
    r"draw"
]

def _detect_image_request(text: str) -> Optional[str]:
    """
    Detects if user is requesting image generation.
    Returns the subject to generate if detected, None otherwise.
    """
    text_lower = text.lower()
    
    for pattern in IMAGE_GENERATION_KEYWORDS:
        match = re.search(pattern, text_lower)
        if match:
            # Extract subject after the keyword
            # Simple heuristic: take everything after the match
            subject = text[match.end():].strip()
            # Remove common trailing words
            subject = re.sub(r'\b(пожалуйста|please)\b', '', subject, flags=re.IGNORECASE).strip()
            return subject if subject else text
    
    return None

async def _call_llm(user_message: str) -> Optional[str]:
    """
    Calls LLM for chat response.
    Uses the rewrite_text function as a simple LLM call.
    """
    import aiohttp
    import json
    
    try:
        async with aiohttp.ClientSession() as session:
            payload = {
                "model": OLLAMA_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": "Ты — полезный ассистент. Отвечай кратко, по делу и дружелюбно."
                    },
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                "stream": False
            }
            
            async with session.post(
                f"{OLLAMA_API_BASE}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("message", {}).get("content", "").strip()
                else:
                    logger.error(f"LLM API error: {response.status}")
                    return None
    except Exception as e:
        logger.error(f"LLM call error: {e}")
        return None

@router.callback_query(F.data == "chat_mode")
async def cb_start_chat(cb: CallbackQuery, state: FSMContext):
    """Entry point: User clicked 'Chat with Bot' in main menu."""
    await state.clear()
    await state.set_state(FormState.chatting)
    
    await cb.message.edit_text(
        "💬 <b>Режим общения</b>\n\n"
        "Задавайте вопросы или попросите нарисовать картинку!\n\n"
        "Команда /menu - вернуться в главное меню",
        parse_mode="HTML"
    )

@router.message(F.text == "/menu", FormState.chatting)
async def cmd_back_to_menu(msg: Message, state: FSMContext):
    """Return to main menu from chat mode."""
    await state.clear()
    await msg.answer(
        "🏠 <b>Главное меню</b>",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )

@router.message(F.text, FormState.chatting)
async def msg_chat(msg: Message, state: FSMContext, bot: Bot):
    """Handle user messages in chat mode."""
    user_text = msg.text
    
    # Check if user wants to generate an image
    image_subject = _detect_image_request(user_text)
    
    if image_subject:
        # Image generation mode
        status_msg = await msg.answer("🎨 <b>Stable Diffusion</b>\n\nГенерирую изображение...", parse_mode="HTML")
        animation_task = asyncio.create_task(
            animate_message(bot, msg.chat.id, status_msg.message_id, "Генерация изображения")
        )
        
        try:
            # Translate to English
            prompt = await translate_prompt_to_english(image_subject)
            
            # Generate image
            img_bytes, _ = await async_generate_stable_diffusion_image(
                bot=bot,
                chat_id=msg.chat.id,
                animation_msg_id=status_msg.message_id,
                prompt=prompt,
                user_id=msg.from_user.id,
                progress_task=animation_task
            )
            
            if img_bytes:
                # Send the generated image
                from aiogram.types import BufferedInputFile
                await bot.delete_message(msg.chat.id, status_msg.message_id)
                await msg.answer_photo(
                    BufferedInputFile(img_bytes, "generated.png"),
                    caption=f"✅ Готово!\n\n💡 Промпт: <code>{prompt}</code>",
                    parse_mode="HTML"
                )
            else:
                await bot.edit_message_text(
                    "❌ Не удалось сгенерировать изображение.",
                    chat_id=msg.chat.id,
                    message_id=status_msg.message_id
                )
        except Exception as e:
            logger.error(f"Image generation error in chat: {e}")
            try:
                await bot.edit_message_text(
                    f"❌ Ошибка генерации: {str(e)[:100]}",
                    chat_id=msg.chat.id,
                    message_id=status_msg.message_id
                )
            except:
                pass
        finally:
            if not animation_task.done():
                animation_task.cancel()
    
    else:
        # Regular LLM chat mode
        status_msg = await msg.answer("🤖 <b>LLM</b>\n\nДумаю...", parse_mode="HTML")
        animation_task = asyncio.create_task(
            animate_message(bot, msg.chat.id, status_msg.message_id, "Обработка запроса")
        )
        
        try:
            response = await _call_llm(user_text)
            
            if response:
                await bot.edit_message_text(
                    f"💬 {response}",
                    chat_id=msg.chat.id,
                    message_id=status_msg.message_id,
                    parse_mode="HTML"
                )
            else:
                await bot.edit_message_text(
                    "❌ Не удалось получить ответ от LLM.",
                    chat_id=msg.chat.id,
                    message_id=status_msg.message_id
                )
        except Exception as e:
            logger.error(f"LLM chat error: {e}")
            try:
                await bot.edit_message_text(
                    f"❌ Ошибка: {str(e)[:100]}",
                    chat_id=msg.chat.id,
                    message_id=status_msg.message_id
                )
            except:
                pass
        finally:
            if not animation_task.done():
                animation_task.cancel()
