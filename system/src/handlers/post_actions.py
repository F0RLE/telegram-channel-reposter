import logging
import asyncio
import base64
import aiohttp
import urllib3
import os
import html
import re
from typing import Optional, Dict, Any, List, Union
from collections import defaultdict

from aiogram import Router, types, Bot, F
from aiogram.types import (
    BufferedInputFile, 
    FSInputFile,
    InputMediaPhoto, 
    InputMediaVideo, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    Message, 
    CallbackQuery
)
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest

# Local Imports
from core.fsm_states import FormState
from core.animation import animate_message
from core.utils import load_published_posts, save_published_posts, safe_delete_message
from modules.llm import rewrite_text, translate_prompt_to_english, create_image_prompt
from modules.image_gen import async_generate_stable_diffusion_image
from config.settings import TARGET_CHANNEL_ID

# Keyboards
from keyboards.inline import (
    actions_submenu_keyboard,
    confirm_publish_keyboard,
    get_post_navigation_keyboard,
    media_actions_keyboard,
    text_actions_keyboard,
    post_publish_actions_keyboard,
    topics_keyboard,
    back_main_keyboard,
    cancel_text_input_keyboard,
)

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)
router = Router()
router.message.filter(F.chat.type == "private")

# ==========================================
# 1. SETUP PATHS & CONSTANTS
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZAGLUSHKA_PATH = os.path.join(BASE_DIR, 'modules', 'Images', 'Zaglushka.png')

# 1x1 Transparent Pixel (Base64) fallback
BLANK_1PX_B64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# Lock for rendering to prevent race conditions
_render_locks = defaultdict(asyncio.Lock)

# ==========================================
# 2. HELPERS
# ==========================================

# Use centralized utility function
_safe_delete = safe_delete_message

async def _fetch_bytes(session: aiohttp.ClientSession, url: str) -> Optional[bytes]:
    """Downloads bytes from URL ignoring SSL errors."""
    try:
        async with session.get(url, ssl=False, timeout=10) as response:
            if response.status == 200:
                return await response.read()
            else:
                logger.warning(f"Failed to fetch {url}: status {response.status}")
    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
    return None

async def _build_media_group(state_data: Dict[str, Any]) -> Optional[List[Union[InputMediaPhoto, InputMediaVideo]]]:
    """Constructs InputMedia objects from state data."""
    raw = state_data.get('media_group_raw')
    if not raw: return None

    built = []
    async with aiohttp.ClientSession() as session:
        for i, item in enumerate(raw):
            try:
                media_source = None
                mtype = item.get('type', 'photo')
                
                # Source resolution
                if item.get('file_id'):
                    media_source = item['file_id']
                elif item.get('url'):
                    media_source = await _fetch_bytes(session, item['url'])
                    if media_source:
                        ext = "mp4" if mtype == "video" else "jpg"
                        media_source = BufferedInputFile(media_source, filename=f"file_{i}.{ext}")

                if not media_source: continue

                # Create InputMedia object
                if mtype == 'video':
                    im = InputMediaVideo(media=media_source)
                else:
                    im = InputMediaPhoto(media=media_source)
                
                if item.get('caption'):
                    im.caption = item['caption']
                    im.parse_mode = "HTML"
                
                built.append(im)
            except Exception as e:
                logger.error(f"Error building media item {i}: {e}")
                continue
            
    return built if built else None

def _get_text(state_data: Dict[str, Any]) -> str:
    """Returns the active text (rewritten or original)."""
    return (state_data.get('text') or state_data.get('raw_text') or "").strip()

def _sanitize_html_text(text: str) -> str:
    """
    Sanitizes text for HTML parsing.
    Escapes HTML entities but preserves intended tags if possible (simplified for safety).
    """
    if not text:
        return text
    
    # Simple and safe approach: escape everything first
    # If you need to support specific tags, it's better to use a proper parser
    # But for now, let's stick to basic escaping to prevent errors
    return html.escape(text)

# ==========================================
# 3. RENDER LOGIC (CORE)
# ==========================================
async def render_preview_post(
    bot: Bot, 
    chat_id: int, 
    state: FSMContext, 
    total_posts: int = None, 
    current_index: int = None,
    is_forwarded: bool = False,
    edit_message_id: int = None
):
    """
    Displays the post content.
    Uses a lock to prevent race conditions.
    """
    async with _render_locks[chat_id]:
        try:
            await _render_preview_post_unsafe(
                bot, chat_id, state, total_posts, current_index, is_forwarded, edit_message_id
            )
        except Exception as e:
            logger.error(f"Critical error in render_preview_post: {e}", exc_info=True)
            # Try to notify user about error
            try:
                await bot.send_message(chat_id, "⚠️ Произошла ошибка при отображении поста.")
            except:
                pass

async def _render_preview_post_unsafe(
    bot: Bot, 
    chat_id: int, 
    state: FSMContext, 
    total_posts: int = None, 
    current_index: int = None,
    is_forwarded: bool = False,
    edit_message_id: int = None
):
    data = await state.get_data()

    # Update Indices
    if is_forwarded:
        current_index, total_posts = 0, 1
    elif current_index is None:
        current_index = int(data.get("current_post_index", 0))
    
    if not total_posts:
        total_posts = len(data.get("search_results") or []) or 1

    await state.update_data(current_post_index=current_index, total_posts=total_posts)

    # Prepare Content
    text = _get_text(data)
    # Use safe text for rendering
    safe_text = _sanitize_html_text(text)
    force_no_media = data.get('force_no_media', False)
    
    content_type = "text"
    media_obj = None
    media_group = None

    # A. Generated Image
    if data.get('has_generated_image') and not force_no_media:
        b_img = data.get('generated_image_bytes')
        if b_img:
            content_type = "photo"
            media_obj = BufferedInputFile(b_img, filename="gen.png")
        elif data.get('image_base64'):
            try:
                b_img = base64.b64decode(data['image_base64'])
                content_type = "photo"
                media_obj = BufferedInputFile(b_img, filename="gen.png")
            except: pass

    # B. Media Group (Album)
    if content_type == "text" and not force_no_media and data.get('media_group_raw'):
        media_group = await _build_media_group(data)
        if media_group:
            content_type = "album" if len(media_group) > 1 else "photo"
            if content_type == "photo": media_obj = media_group[0].media

    # C. Original Single Media
    if content_type == "text" and not force_no_media:
        if data.get('original_photo_file_id'):
            content_type = "photo"
            media_obj = data['original_photo_file_id']
        elif data.get('original_video_file_id'):
            content_type = "video"
            media_obj = data['original_video_file_id']

    # D. Text as Photo (Stub Logic)
    if content_type == "text" and len(text) < 1024:
        content_type = "photo"
        if os.path.exists(ZAGLUSHKA_PATH):
            # Use physical file if exists
            media_obj = FSInputFile(ZAGLUSHKA_PATH)
        else:
            # Fallback to transparent pixel to prevent crash
            media_obj = BufferedInputFile(base64.b64decode(BLANK_1PX_B64), filename="blank.png")

    # Render Keyboard
    nav_kb = get_post_navigation_keyboard(
        current=current_index,
        total=total_posts,
        has_media=(content_type != "text"),
        link=data.get('link'),
        is_single_post=is_forwarded,
        back_callback="back_main" if is_forwarded else "back_topics"
    )
    
    menu_text = "📋 Выберите действие для работы с постом:"
    last_ids = data.get('last_message_ids', [])
    markup_id = data.get('last_markup_id')
    last_content_id = last_ids[0] if last_ids else None

    # Determine what to edit
    editing_content_id = None
    
    if edit_message_id:
        if edit_message_id == last_content_id:
            editing_content_id = last_content_id
    elif last_content_id:
        editing_content_id = last_content_id
    
    # Try to edit content
    new_ids = []
    content_edited = False
    
    try:
        if editing_content_id:
            try:
                if content_type == "text":
                    await bot.edit_message_text(
                        text=safe_text,
                        chat_id=chat_id,
                        message_id=editing_content_id,
                        parse_mode="HTML"
                    )
                    new_ids = [editing_content_id]
                    content_edited = True
                elif content_type == "photo" and media_obj:
                    try:
                        await bot.edit_message_media(
                            chat_id=chat_id,
                            message_id=editing_content_id,
                            media=InputMediaPhoto(media=media_obj, caption=safe_text, parse_mode="HTML")
                        )
                        new_ids = [editing_content_id]
                        content_edited = True
                    except TelegramAPIError:
                        await bot.edit_message_caption(
                            chat_id=chat_id,
                            message_id=editing_content_id,
                            caption=safe_text,
                            parse_mode="HTML"
                        )
                        new_ids = [editing_content_id]
                        content_edited = True
                elif content_type == "video" and media_obj:
                    try:
                        await bot.edit_message_media(
                            chat_id=chat_id,
                            message_id=editing_content_id,
                            media=InputMediaVideo(media=media_obj, caption=safe_text, parse_mode="HTML")
                        )
                        new_ids = [editing_content_id]
                        content_edited = True
                    except TelegramAPIError:
                        await bot.edit_message_caption(
                            chat_id=chat_id,
                            message_id=editing_content_id,
                            caption=safe_text,
                            parse_mode="HTML"
                        )
                        new_ids = [editing_content_id]
                        content_edited = True
            except TelegramAPIError:
                content_edited = False
        
        if not content_edited:
            # Delete old content and send new
            ids_to_delete = [mid for mid in last_ids if mid != editing_content_id]
            await _safe_delete(bot, chat_id, ids_to_delete)
            
            if content_type == "album" and media_group:
                media_group[0].caption = safe_text
                media_group[0].parse_mode = "HTML"
                msgs = await bot.send_media_group(chat_id, media=media_group)
                new_ids = [m.message_id for m in msgs]
            elif content_type == "photo":
                m = await bot.send_photo(chat_id, media_obj, caption=safe_text, parse_mode="HTML")
                new_ids = [m.message_id]
            elif content_type == "video":
                m = await bot.send_video(chat_id, media_obj, caption=safe_text, parse_mode="HTML")
                new_ids = [m.message_id]
            else:
                m = await bot.send_message(chat_id, safe_text, parse_mode="HTML")
                new_ids = [m.message_id]
    except TelegramAPIError as e:
        # Fallback if media failed
        await _safe_delete(bot, chat_id, last_ids)
        error_text = f"⚠️ Ошибка медиа: {str(e)[:200]}"
        try:
            err_m = await bot.send_message(chat_id, error_text)
            new_ids = [err_m.message_id]
        except:
            new_ids = []
    
    if not content_edited:
        await state.update_data(last_message_ids=new_ids)
    
    # Handle Menu
    # Always recreate menu if content was recreated to ensure it's at the bottom
    should_recreate_menu = not content_edited
    
    if markup_id and not should_recreate_menu:
        try:
            await bot.edit_message_text(
                text=menu_text,
                chat_id=chat_id,
                message_id=markup_id,
                reply_markup=nav_kb,
                parse_mode="HTML"
            )
        except TelegramAPIError:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=markup_id,
                    reply_markup=nav_kb
                )
            except TelegramAPIError:
                should_recreate_menu = True
    
    if should_recreate_menu:
        if markup_id:
            await _safe_delete(bot, chat_id, [markup_id])
        
        m_menu = await bot.send_message(chat_id, menu_text, reply_markup=nav_kb, parse_mode="HTML")
        await state.update_data(last_markup_id=m_menu.message_id)

# ==========================================
# 4. MENUS & NAVIGATION
# ==========================================

async def _upd_menu(cb: CallbackQuery, text: str, kb: InlineKeyboardMarkup):
    try: await cb.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except: await cb.answer()

@router.callback_query(F.data == "open_actions_menu")
async def cb_open_menu(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    has_media = bool(
        data.get('has_generated_image') or 
        data.get('original_photo_file_id') or 
        data.get('original_video_file_id') or 
        data.get('media_group_raw')
    ) and not data.get('force_no_media')
    
    await _upd_menu(cb, "<b>⚙️ Меню действий</b>", actions_submenu_keyboard(has_media))

@router.callback_query(F.data == "open_text_actions")
async def cb_text_acts(cb: CallbackQuery):
    await _upd_menu(cb, "<b>📝 Работа с текстом</b>", text_actions_keyboard())

@router.callback_query(F.data == "open_media_actions")
async def cb_media_acts(cb: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    has_media = bool(d.get('has_media') or d.get('has_generated_image'))
    await _upd_menu(cb, "<b>🖼 Работа с медиа</b>", media_actions_keyboard(has_media))

@router.callback_query(F.data == "back_to_post_actions")
async def cb_back_main(cb: CallbackQuery, state: FSMContext, bot: Bot):
    """Возвращает меню к навигационному меню поста без пересоздания контента"""
    data = await state.get_data()
    chat_id = cb.message.chat.id
    
    # Получаем текущие данные поста
    current_index = int(data.get("current_post_index", 0))
    total_posts = int(data.get("total_posts", 1))
    is_forwarded = (data.get("source") == "forwarded_post")
    
    # Создаем навигационное меню поста
    nav_kb = get_post_navigation_keyboard(
        current=current_index,
        total=total_posts,
        has_media=bool(
            data.get('has_generated_image') or
            data.get('original_photo_file_id') or
            data.get('original_video_file_id') or
            data.get('media_group_raw')
        ),
        link=data.get('link'),
        is_single_post=is_forwarded,
        back_callback="back_main" if is_forwarded else "back_topics"
    )
    
    menu_text = "📋 Выберите действие для работы с постом:"
    
    # Просто редактируем меню обратно к навигационному меню
    try:
        await bot.edit_message_text(
            text=menu_text,
            chat_id=chat_id,
            message_id=cb.message.message_id,
            reply_markup=nav_kb,
            parse_mode="HTML"
        )
    except TelegramAPIError:
        # Если не удалось отредактировать, пробуем обновить только кнопки
        try:
            await bot.edit_message_reply_markup(
                chat_id=chat_id,
                message_id=cb.message.message_id,
                reply_markup=nav_kb
            )
        except TelegramAPIError:
            # Если и это не сработало, просто отвечаем на callback
            await cb.answer()

# ==========================================
# 5. TEXT EDITING
# ==========================================

@router.callback_query(F.data == "rewrite_text")
async def cb_rewrite(cb: CallbackQuery, state: FSMContext, bot: Bot):
    d = await state.get_data()
    raw = d.get('raw_text') or d.get('text')
    if not raw: return await cb.answer("Нет текста!", show_alert=True)

    menu_id = cb.message.message_id
    await bot.edit_message_text(
        text="⏳ <b>LLM:</b> Думаю...", 
        chat_id=cb.message.chat.id, 
        message_id=menu_id
    )
    
    task = asyncio.create_task(animate_message(bot, cb.message.chat.id, menu_id, "Рерайт (LLM)"))
    
    try:
        new_txt = await rewrite_text(raw)
        if new_txt: await state.update_data(text=new_txt)
    except Exception as e:
        logger.error(f"Ошибка LLM: {e}")
        await cb.answer("Ошибка LLM", show_alert=True)
    finally:
        if not task.done(): task.cancel()
        await state.update_data(last_markup_id=menu_id)
        is_fwd = (d.get("source") == "forwarded_post")
        await render_preview_post(bot, cb.message.chat.id, state, is_forwarded=is_fwd, edit_message_id=menu_id)

@router.callback_query(F.data == "manual_text_input")
async def cb_manual_text(cb: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    cur = d.get('text', '')
    await state.set_state(FormState.awaiting_text_input)
    await _upd_menu(cb, f"Отправьте новый текст.\n\nТекущий:\n<code>{cur[:100]}...</code>", cancel_text_input_keyboard())

@router.message(F.text, FormState.awaiting_text_input)
async def msg_manual_text(msg: Message, state: FSMContext, bot: Bot):
    await state.update_data(text=msg.text)
    await _safe_delete(bot, msg.chat.id, msg.message_id)
    await state.set_state(FormState.viewing_post)
    d = await state.get_data()
    await render_preview_post(bot, msg.chat.id, state, is_forwarded=(d.get("source")=="forwarded_post"))

@router.callback_query(F.data == "cancel_text_input")
async def cb_cancel_text(cb: CallbackQuery, state: FSMContext):
    await state.set_state(FormState.viewing_post)
    await cb_open_menu(cb, state)

@router.callback_query(F.data == "choose_remove_media")
async def cb_remove_media(cb: CallbackQuery, state: FSMContext, bot: Bot):
    """Removes media from the post."""
    await state.update_data(
        force_no_media=True,
        has_generated_image=False,
        generated_image_bytes=None,
        image_base64=None,
        original_photo_file_id=None,
        original_video_file_id=None,
        media_group_raw=None
    )
    d = await state.get_data()
    is_fwd = (d.get("source") == "forwarded_post")
    await render_preview_post(bot, cb.message.chat.id, state, is_forwarded=is_fwd, edit_message_id=cb.message.message_id)
    await cb.answer("Медиа удалено")

# ==========================================
# 6. IMAGE GENERATION
# ==========================================

@router.callback_query(F.data == "generate_image")
async def cb_gen_img(cb: CallbackQuery, state: FSMContext, bot: Bot):
    """Обработчик генерации изображения (как в старой версии)"""
    # Сразу отвечаем на callback, чтобы кнопка не задерживалась
    await cb.answer()
    
    chat_id = cb.message.chat.id
    user_id = cb.from_user.id
    d = await state.get_data()

    prompt = d.get('image_prompt')
    
    # Если промпта нет, пытаемся создать его из текста (как в старой версии)
    if not prompt:
        text_source = d.get('text') or d.get('raw_text')
        if not text_source:
            await cb.answer("Нет текста и промпта!", show_alert=True)
            return
        
        # Используем перевод (как в старой версии)
        try:
            prompt = await translate_prompt_to_english(text_source[:1000])
        except Exception as e:
            logger.error(f"Ошибка перевода промпта: {e}")
            prompt = None
            
    if not prompt:
        await cb.answer("Не удалось получить промпт.", show_alert=True)
        return

    # Берем ID сообщения с меню
    menu_msg_id = cb.message.message_id

    # 1. Редактируем меню в статус "Рисую..."
    try:
        await bot.edit_message_text(
            chat_id=chat_id,
            message_id=menu_msg_id,
            text="🖌 <b>Stable Diffusion:</b> Рисую...",
            parse_mode="HTML"
        )
    except TelegramAPIError:
        msg = await bot.send_message(chat_id, "🖌 Рисую...")
        menu_msg_id = msg.message_id

    # 2. Анимация в меню
    animation_task = asyncio.create_task(animate_message(bot, chat_id, menu_msg_id, "Генерация изображения"))

    try:
        # Вызов генератора
        img_bytes, _ = await async_generate_stable_diffusion_image(
            bot=bot,
            chat_id=chat_id,
            animation_msg_id=menu_msg_id,
            prompt=prompt,
            user_id=user_id,
            progress_task=animation_task,
            neg_prompt=None
        )
        
        if img_bytes:
            await state.update_data(
                generated_image_bytes=img_bytes,
                image_base64=base64.b64encode(img_bytes).decode('utf-8'),
                has_media=True,
                has_generated_image=True,
                force_no_media=False,
                image_prompt=prompt
            )
        else:
            # Если байтов нет, но ошибки не вылетело
            await bot.edit_message_text(chat_id=chat_id, message_id=menu_msg_id, text="❌ Пустой ответ от SD.")
            await asyncio.sleep(2)
            
    except Exception as e:
        logger.error(f"SD Generation Error: {e}", exc_info=True)
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=menu_msg_id, text="❌ Ошибка Stable Diffusion.")
            await asyncio.sleep(2)
        except:
            pass
    finally:
        if not animation_task.done():
            animation_task.cancel()
        
        # 3. Указываем рендеру использовать это сообщение
        await state.update_data(last_markup_id=menu_msg_id)
        
        # 4. Вызываем рендер (обновит картинку в посте и вернет кнопки в меню)
        is_fwd = (d.get("source") == "forwarded_post")
        await render_preview_post(bot, chat_id, state, is_forwarded=is_fwd, edit_message_id=menu_msg_id)

@router.callback_query(F.data == "manual_prompt_input")
async def cb_prompt_input(cb: CallbackQuery, state: FSMContext):
    await state.set_state(FormState.awaiting_prompt_input)
    await state.update_data(instruction_message_id=cb.message.message_id)
    await cb.message.edit_text("📝 <b>Введите промпт:</b>", reply_markup=back_main_keyboard())

@router.message(F.text, FormState.awaiting_prompt_input)
async def msg_prompt_input(msg: Message, state: FSMContext, bot: Bot):
    prompt = msg.text
    d = await state.get_data()
    mid = d.get("instruction_message_id")
    await _safe_delete(bot, msg.chat.id, msg.message_id)

    await bot.edit_message_text(
        text="🎨 Запуск генерации...", 
        chat_id=msg.chat.id, 
        message_id=mid
    )
    task = asyncio.create_task(animate_message(bot, msg.chat.id, mid, "Генерация"))

    try:
        final_prompt = await translate_prompt_to_english(prompt)
        img_bytes, _ = await async_generate_stable_diffusion_image(
            bot, msg.chat.id, mid, final_prompt, msg.from_user.id, task
        )
        if img_bytes:
            await state.update_data(
                generated_image_bytes=img_bytes,
                image_base64=base64.b64encode(img_bytes).decode('utf-8'),
                has_generated_image=True, 
                force_no_media=False,
                image_prompt=final_prompt
            )
    finally:
        if not task.done(): task.cancel()
        await state.set_state(FormState.viewing_post)
        await state.update_data(last_markup_id=mid)
        is_fwd = (d.get("source") == "forwarded_post")
        await render_preview_post(bot, msg.chat.id, state, is_forwarded=is_fwd)

# ==========================================
# 7. PUBLISH
# ==========================================

@router.callback_query(F.data == "confirm_publish")
async def cb_pub_conf(cb: CallbackQuery):
    await _upd_menu(cb, "🚀 <b>Публикация</b>\nУверены?", confirm_publish_keyboard())

@router.callback_query(F.data == "publish")
async def cb_publish(cb: CallbackQuery, state: FSMContext, bot: Bot):
    if not TARGET_CHANNEL_ID:
        return await cb.answer("❌ ID канала не настроен!", show_alert=True)

    chat_id = cb.message.chat.id
    d = await state.get_data()
    text = _get_text(d)
    # Очищаем текст перед публикацией
    text = _sanitize_html_text(text)
    
    stat_msg = await bot.send_message(chat_id, "🚀 Публикую...")
    
    try:
        force_no = d.get('force_no_media', False)
        media_group = await _build_media_group(d)
        
        if d.get('has_generated_image') and not force_no:
             b = d.get('generated_image_bytes')
             if not b:
                 img_b64 = d.get('image_base64')
                 if img_b64:
                     b = base64.b64decode(img_b64)
             if b:
                 await bot.send_photo(TARGET_CHANNEL_ID, BufferedInputFile(b, "p.png"), caption=text, parse_mode="HTML")
        elif media_group and not force_no and len(media_group) > 1:
             media_group[0].caption = text
             media_group[0].parse_mode = "HTML"
             await bot.send_media_group(TARGET_CHANNEL_ID, media=media_group)
        elif not force_no and (d.get('original_photo_file_id') or d.get('original_video_file_id')):
             pid = d.get('original_photo_file_id')
             vid = d.get('original_video_file_id')
             if pid: await bot.send_photo(TARGET_CHANNEL_ID, pid, caption=text, parse_mode="HTML")
             else: await bot.send_video(TARGET_CHANNEL_ID, vid, caption=text, parse_mode="HTML")
        else:
             await bot.send_message(TARGET_CHANNEL_ID, text, parse_mode="HTML", disable_web_page_preview=True)

        if d.get('link'):
            p = load_published_posts()
            p.append(d['link'])
            save_published_posts(p)

        delete_ids = [stat_msg.message_id] + (d.get('last_message_ids') or [])
        if d.get('last_markup_id'):
            delete_ids.append(d.get('last_markup_id'))
        await _safe_delete(bot, chat_id, delete_ids)
    except Exception as e:
        logger.error(f"Error publishing: {e}")
        await bot.send_message(chat_id, f"❌ Ошибка публикации: {e}")