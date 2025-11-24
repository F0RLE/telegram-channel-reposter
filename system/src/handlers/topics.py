import logging
import asyncio
import time
from typing import Optional, List, Dict, Any, Union
from datetime import datetime, timezone

from aiogram import Router, types, Bot, F
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

# Local Imports
from core.fsm_states import FormState
from core.utils import safe_delete_message
from modules.parser import aggregate_topic_posts
from keyboards.inline import topics_keyboard, cancel_jump_keyboard
from core.animation import animate_message
from config.settings import TELEGRAM_CHANNELS, reload_channels

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type == "private")

# ==========================================
# 1. CACHE & LOCKS
# ==========================================
_PARSE_CACHE: Dict[str, tuple] = {}
CACHE_TTL = 300  # 5 minutes

_USER_LOCK: Dict[int, float] = {}
LOCK_TIMEOUT = 1.0 # Prevent double-clicks

def _check_lock(user_id: int) -> bool:
    now = time.time()
    if now - _USER_LOCK.get(user_id, 0) < LOCK_TIMEOUT:
        return False
    _USER_LOCK[user_id] = now
    return True

# ==========================================
# 2. HELPERS
# ==========================================

# Use centralized utility function
_safe_delete = safe_delete_message

def _load_post_to_state(state_data: Dict[str, Any], post_data: Dict[str, Any]):
    """
    Resets state fields and loads new post data into FSM.
    """
    raw = post_data.get("text") or post_data.get("raw_text") or ""
    
    # Clean slate
    clean_data = {
        "raw_text": raw,
        "text": raw, # Reset edits
        "link": post_data.get("link"),
        
        # Media flags
        "has_media": False,
        "has_generated_image": False,
        "force_no_media": False,
        
        # Reset binaries/ids
        "generated_image_bytes": None,
        "image_base64": None,
        "original_photo_file_id": None,
        "original_video_file_id": None,
        "media_group_raw": None,
        
        # Prompts - используем сохраненный или None (будет сгенерирован при генерации)
        "image_prompt": post_data.get("image_prompt"),
    }
    state_data.update(clean_data)

    # Restore saved progress if exists (e.g. user generated image then navigated away)
    if post_data.get("saved_gen_bytes"):
        state_data["has_generated_image"] = True
        state_data["generated_image_bytes"] = post_data["saved_gen_bytes"]
        state_data["image_base64"] = post_data.get("saved_gen_b64")
    
    if post_data.get("saved_text"):
        state_data["text"] = post_data["saved_text"]

    # Load original media if no generated image
    normalized = []
    if post_data.get("media_urls"):
        for u in post_data["media_urls"]:
            normalized.append({"type": "photo", "url": u})
    
    if normalized:
        state_data["media_group_raw"] = normalized
        state_data["has_media"] = True

async def _show_current_post(bot: Bot, chat_id: int, state: FSMContext, index: int, edit_message_id: int = None):
    """
    Loads post at 'index' and calls render.
    """
    data = await state.get_data()
    results = data.get("search_results") or []
    
    if not results:
        await bot.send_message(chat_id, "❌ Список пуст.")
        return

    # Bounds check
    index = max(0, min(index, len(results) - 1))

    # Load data
    local_data = dict(data)
    local_data["current_post_index"] = index
    _load_post_to_state(local_data, results[index])
    
    await state.update_data(local_data)
    
    # Lazy Import to prevent Cycle
    from handlers.post_actions import render_preview_post
    await render_preview_post(bot, chat_id, state, len(results), index, edit_message_id=edit_message_id)

async def _save_current_progress(state: FSMContext):
    """
    Saves current text edits and generated images back to search_results list.
    So when user clicks 'Back', their work is not lost.
    """
    data = await state.get_data()
    results = data.get("search_results", [])
    idx = data.get("current_post_index", 0)
    
    if results and 0 <= idx < len(results):
        # Save Text
        results[idx]["saved_text"] = data.get("text")
        # Save Image
        if data.get("has_generated_image"):
            results[idx]["saved_gen_bytes"] = data.get("generated_image_bytes")
            results[idx]["saved_gen_b64"] = data.get("image_base64")
        
        await state.update_data(search_results=results)

# ==========================================
# 3. HANDLERS
# ==========================================

@router.callback_query(F.data.startswith("topic:"), FormState.awaiting_topic)
async def callback_topic_chosen(cb: types.CallbackQuery, state: FSMContext, bot: Bot):
    user_id = cb.from_user.id
    chat_id = cb.message.chat.id
    topic_key = cb.data.split(":", 1)[1]

    if not _check_lock(user_id): return await cb.answer()

    # UI Update
    msg_id = cb.message.message_id
    display_name = "🔥 Все темы" if topic_key == "all" else topic_key
    
    await bot.edit_message_text(
        text=f"🔍 Ищу посты: <b>{display_name}</b>...", 
        chat_id=chat_id, 
        message_id=msg_id, 
        parse_mode="HTML"
    )
    
    # Animation Task
    task = asyncio.create_task(animate_message(bot, chat_id, msg_id, "Парсинг каналов"))

    search_results = []
    try:
        # Check Cache
        now = time.time()
        if topic_key in _PARSE_CACHE and (now - _PARSE_CACHE[topic_key][0] < CACHE_TTL):
            search_results = _PARSE_CACHE[topic_key][1]
        else:
            # Перезагружаем каналы для актуальности
            reload_channels()
            # Parse
            targets = list(TELEGRAM_CHANNELS.keys()) if topic_key == "all" else [topic_key]
            
            tasks = [aggregate_topic_posts(t, max_per_channel=30) for t in targets]
            raw_res = await asyncio.gather(*tasks)
            
            for r in raw_res: search_results.extend(r)
            
            # Sort Newest First
            search_results.sort(
                key=lambda x: datetime.fromisoformat(x.get('timestamp').replace('Z', '+00:00')) 
                              if x.get('timestamp') else datetime.min.replace(tzinfo=timezone.utc), 
                reverse=True
            )
            
            # Update Cache
            _PARSE_CACHE[topic_key] = (now, search_results)

    except Exception as e:
        logger.error(f"Ошибка парсинга: {e}")
    finally:
        if not task.done(): task.cancel()

    # Handle Empty
    if not search_results:
        await bot.edit_message_text(
            text=f"❌ По теме <b>{display_name}</b> ничего нового.", 
            chat_id=chat_id, 
            message_id=msg_id, 
            parse_mode="HTML"
        )
        await asyncio.sleep(2)
        await bot.edit_message_text(
            text="Выберите тему:", 
            chat_id=chat_id, 
            message_id=msg_id, 
            reply_markup=topics_keyboard()
        )
        return

    # Start Viewing
    await _safe_delete(bot, chat_id, msg_id) # Delete 'Searching...' msg

    await state.update_data(
        source="parser",
        search_results=search_results,
        current_post_index=0,
        last_message_ids=[],
        last_markup_id=None
    )
    await state.set_state(FormState.viewing_post)
    
    await _show_current_post(bot, chat_id, state, 0)


@router.callback_query(F.data == "back_topics", FormState.viewing_post)
async def callback_back_topics(cb: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    chat_id = cb.message.chat.id

    # Cleanup Post Messages
    ids = data.get("last_message_ids") or []
    await _safe_delete(bot, chat_id, ids)
    
    markup_id = data.get("last_markup_id")
    
    await state.clear()
    await state.set_state(FormState.awaiting_topic)
    
    # Restore Menu
    text = "Выберите тему для поиска:"
    kb = topics_keyboard()
    
    if markup_id:
        try:
            await bot.edit_message_text(
                text=text, 
                chat_id=chat_id, 
                message_id=markup_id, 
                reply_markup=kb
            )
            return
        except TelegramBadRequest:
            await _safe_delete(bot, chat_id, markup_id)
            
    await cb.message.answer(text, reply_markup=kb)


# ==========================================
# 4. NAVIGATION
# ==========================================

@router.callback_query(F.data.in_({"next_post", "prev_post"}), FormState.viewing_post)
async def callback_navigate(cb: types.CallbackQuery, state: FSMContext, bot: Bot):
    if not _check_lock(cb.from_user.id): return await cb.answer()
    
    # Save current work before moving!
    await _save_current_progress(state)

    data = await state.get_data()
    idx = data.get("current_post_index", 0)
    direction = 1 if cb.data == "next_post" else -1
    
    # Передаем ID контента для редактирования (если есть), иначе ID меню
    # Это обеспечит плавное переключение - редактирование вместо отправки нового
    last_content_id = None
    last_ids = data.get('last_message_ids', [])
    if last_ids:
        last_content_id = last_ids[0]
    
    # Используем ID контента для редактирования, чтобы контент редактировался, а меню оставалось внизу
    edit_id = last_content_id if last_content_id else data.get('last_markup_id')
    
    await _show_current_post(bot, cb.message.chat.id, state, idx + direction, edit_message_id=edit_id)
    await cb.answer()


@router.callback_query(F.data == "trigger_jump", FormState.viewing_post)
async def callback_jump_ask(cb: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    total = len(data.get("search_results", []))
    msg_id = cb.message.message_id
    
    await state.set_state(FormState.awaiting_post_jump)
    await bot.edit_message_text(
        text=f"🔢 Введите номер поста (1-{total}):", 
        chat_id=cb.message.chat.id, 
        message_id=msg_id, 
        reply_markup=cancel_jump_keyboard()
    )
    await cb.answer()


@router.callback_query(F.data == "cancel_jump", FormState.awaiting_post_jump)
async def callback_jump_cancel(cb: types.CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(FormState.viewing_post)
    # Restore view
    data = await state.get_data()
    markup_id = data.get('last_markup_id')
    await _show_current_post(bot, cb.message.chat.id, state, data.get("current_post_index", 0), edit_message_id=markup_id)


@router.message(FormState.awaiting_post_jump)
async def message_jump_input(msg: types.Message, state: FSMContext, bot: Bot):
    chat_id = msg.chat.id
    await _safe_delete(bot, chat_id, msg.message_id) # Del user input
    
    data = await state.get_data()
    total = len(data.get("search_results", []))
    
    # Сохраняем прогресс перед переходом
    await _save_current_progress(state)
    
    # Получаем ID для редактирования
    last_content_id = None
    last_ids = data.get('last_message_ids', [])
    if last_ids:
        last_content_id = last_ids[0]
    edit_id = last_content_id if last_content_id else data.get("last_markup_id")

    try:
        target = int(msg.text)
        if 1 <= target <= total:
            await state.set_state(FormState.viewing_post)
            await _show_current_post(bot, chat_id, state, target - 1, edit_message_id=edit_id)
            return
    except ValueError:
        pass
    
    # Error feedback
    markup_id = data.get("last_markup_id")
    if markup_id:
        try:
            await bot.edit_message_text(
                text=f"⚠️ Ошибка! Введите число от 1 до {total}:", 
                chat_id=chat_id, 
                message_id=markup_id, 
                reply_markup=cancel_jump_keyboard()
            )
        except: pass