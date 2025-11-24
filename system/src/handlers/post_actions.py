import logging
import asyncio
import base64
import aiohttp
import urllib3
import os
import html
import re
from typing import Optional, Dict, Any, List, Union

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
from aiogram.exceptions import TelegramAPIError

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
    except Exception: pass
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
            except Exception: continue
            
    return built if built else None

def _get_text(state_data: Dict[str, Any]) -> str:
    """Returns the active text (rewritten or original)."""
    return (state_data.get('text') or state_data.get('raw_text') or "").strip()

def _sanitize_html_text(text: str) -> str:
    """
    Очищает текст от проблемных символов и экранирует HTML-сущности.
    Заменяет Unicode символы, которые могут вызвать проблемы с парсингом HTML.
    """
    if not text:
        return text
    
    # Сначала защищаем существующие HTML теги
    protected_tags = []
    tag_pattern = r'<[^>]+>'
    
    def protect_tag(match):
        tag = match.group(0)
        placeholder = f"__PROTECTED_TAG_{len(protected_tags)}__"
        protected_tags.append(tag)
        return placeholder
    
    # Защищаем теги
    text = re.sub(tag_pattern, protect_tag, text)
    
    # Заменяем проблемные Unicode символы на обычные (ПОСЛЕ защиты тегов)
    # Это важно, чтобы не затронуть символы внутри тегов
    # Используем более агрессивную замену всех вариантов многоточия
    replacements = {
        '\u2026': '...',  # HORIZONTAL ELLIPSIS (U+2026) - стандартное многоточие
        '\u22EF': '...',  # MIDLINE HORIZONTAL ELLIPSIS (U+22EF)
        '\uFE19': '...',  # PRESENTATION FORM FOR VERTICAL HORIZONTAL ELLIPSIS (U+FE19)
        '…': '...',       # Многоточие Unicode на обычное (fallback)
        '—': '-',         # Длинное тире на обычное
        '–': '-',         # Короткое тире на обычное
        '"': '"',         # Левая двойная кавычка
        '"': '"',         # Правая двойная кавычка
        ''': "'",         # Левая одинарная кавычка
        ''': "'",         # Правая одинарная кавычка
        '«': '"',         # Левая угловая кавычка
        '»': '"',         # Правая угловая кавычка
        '‹': "'",         # Левая одинарная угловая кавычка
        '›': "'",         # Правая одинарная угловая кавычка
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Экранируем HTML-сущности
    text = html.escape(text)
    
    # Восстанавливаем защищенные теги
    for i, tag in enumerate(protected_tags):
        text = text.replace(f"__PROTECTED_TAG_{i}__", tag)
    
    # Финальная проверка - заменяем любые оставшиеся проблемные символы многоточия
    # которые могут вызвать ошибки парсинга (включая все возможные варианты)
    text = re.sub(r'[\u2026\u22EF\uFE19\u22EE\u2E2E]', '...', text)
    
    # Дополнительная проверка - удаляем любые символы, которые могут быть интерпретированы как HTML теги
    # но не являются валидными HTML тегами
    text = re.sub(r'<[^>]*\.\.\.[^>]*>', '...', text)
    
    return text

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
    Prioritizes Zaglushka.png, falls back to 1px Base64 if missing.
    """
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
    # Очищаем текст от проблемных символов для HTML парсинга
    text = _sanitize_html_text(text)
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
    
    # Более длинный текст для более широких кнопок
    menu_text = "📋 Выберите действие для работы с постом:"
    last_ids = data.get('last_message_ids', [])
    markup_id = data.get('last_markup_id')
    last_content_id = last_ids[0] if last_ids else None

    # Определяем, что редактируем
    # edit_message_id может быть либо ID контента, либо ID меню
    # Приоритет: если передан edit_message_id и он совпадает с last_content_id - редактируем контент
    # Если передан edit_message_id и он совпадает с markup_id - редактируем меню
    # Если не передан, но есть last_content_id - пытаемся редактировать контент
    
    editing_content_id = None
    editing_menu_id = None
    
    if edit_message_id:
        if edit_message_id == last_content_id and last_content_id:
            editing_content_id = last_content_id
        elif edit_message_id == markup_id and markup_id:
            editing_menu_id = markup_id
    elif last_content_id:
        # Если edit_message_id не передан, но есть контент - пытаемся его редактировать
        editing_content_id = last_content_id
    
    # Если не редактируем контент, но есть меню - редактируем меню
    if not editing_content_id and markup_id:
        editing_menu_id = markup_id
    
    # Редактируем или отправляем новый контент
    new_ids = []
    content_edited = False
    
    try:
        if editing_content_id and last_content_id:
            # Пытаемся отредактировать существующий контент
            try:
                if content_type == "text":
                    # Редактируем текстовое сообщение
                    await bot.edit_message_text(
                        text=text,
                        chat_id=chat_id,
                        message_id=last_content_id,
                        parse_mode="HTML"
                    )
                    new_ids = [last_content_id]
                    content_edited = True
                elif content_type == "photo" and media_obj:
                    # Редактируем фото (капшн и/или медиа)
                    try:
                        # Пытаемся отредактировать медиа и капшн
                        await bot.edit_message_media(
                            chat_id=chat_id,
                            message_id=last_content_id,
                            media=InputMediaPhoto(media=media_obj, caption=text, parse_mode="HTML")
                        )
                        new_ids = [last_content_id]
                        content_edited = True
                    except TelegramAPIError:
                        # Если не удалось отредактировать медиа, редактируем только капшн
                        await bot.edit_message_caption(
                            chat_id=chat_id,
                            message_id=last_content_id,
                            caption=text,
                            parse_mode="HTML"
                        )
                        new_ids = [last_content_id]
                        content_edited = True
                elif content_type == "video" and media_obj:
                    # Редактируем видео (капшн и/или медиа)
                    try:
                        await bot.edit_message_media(
                            chat_id=chat_id,
                            message_id=last_content_id,
                            media=InputMediaVideo(media=media_obj, caption=text, parse_mode="HTML")
                        )
                        new_ids = [last_content_id]
                        content_edited = True
                    except TelegramAPIError:
                        # Если не удалось отредактировать медиа, редактируем только капшн
                        await bot.edit_message_caption(
                            chat_id=chat_id,
                            message_id=last_content_id,
                            caption=text,
                            parse_mode="HTML"
                        )
                        new_ids = [last_content_id]
                        content_edited = True
            except TelegramAPIError:
                # Если не удалось отредактировать, удаляем и отправляем новое
                content_edited = False
        
        if not content_edited:
            # Удаляем старый контент (кроме того, который редактируем) и отправляем новый
            ids_to_delete = [mid for mid in last_ids if mid != editing_content_id]
            await _safe_delete(bot, chat_id, ids_to_delete)
            
            if content_type == "album" and media_group:
                media_group[0].caption = text
                media_group[0].parse_mode = "HTML"
                msgs = await bot.send_media_group(chat_id, media=media_group)
                new_ids = [m.message_id for m in msgs]
            elif content_type == "photo":
                m = await bot.send_photo(chat_id, media_obj, caption=text, parse_mode="HTML")
                new_ids = [m.message_id]
            elif content_type == "video":
                m = await bot.send_video(chat_id, media_obj, caption=text, parse_mode="HTML")
                new_ids = [m.message_id]
            else:
                m = await bot.send_message(chat_id, text, parse_mode="HTML")
                new_ids = [m.message_id]
    except TelegramAPIError as e:
        # Fallback if media failed
        await _safe_delete(bot, chat_id, last_ids)
        # Очищаем текст от проблемных символов перед отправкой ошибки
        safe_text = _sanitize_html_text(text[:1000]) if text else ""
        error_text = f"⚠️ Ошибка медиа: {str(e)[:200]}"
        if safe_text:
            error_text += f"\n\n{safe_text}"
        try:
            # Пробуем с HTML
            err_m = await bot.send_message(chat_id, error_text, parse_mode="HTML")
        except:
            try:
                # Если не работает, пробуем без форматирования
                err_m = await bot.send_message(chat_id, error_text, parse_mode=None)
            except:
                # Если и это не работает, отправляем простой текст
                err_m = await bot.send_message(chat_id, "⚠️ Ошибка при отправке поста. Проверьте текст на наличие специальных символов.")
        new_ids = [err_m.message_id]
    
    # Обновляем ID контента (если отредактировали, сохраняем старый, иначе новый)
    if not content_edited:
        await state.update_data(last_message_ids=new_ids)
    
    # КРИТИЧЕСКИ ВАЖНО: Меню ВСЕГДА должно быть отправлено ПОСЛЕ контента
    # ЛОГИКА: 
    # - Если контент был отредактирован - редактируем меню (не пересоздаем)
    # - Если контент был создан заново - создаем меню заново (удаляем старое)
    # - Если контент был создан из-за ошибки - создаем меню заново
    
    # Небольшая задержка для гарантии, что контент полностью обработан
    await asyncio.sleep(0.2)
    
    # Определяем, нужно ли пересоздавать меню
    should_recreate_menu = not content_edited  # Если контент создан заново - пересоздаем меню
    
    if markup_id and not should_recreate_menu:
        # Меню существует и контент был отредактирован - редактируем меню
        try:
            await bot.edit_message_text(
                text=menu_text,
                chat_id=chat_id,
                message_id=markup_id,
                reply_markup=nav_kb,
                parse_mode="HTML"
            )
            # Меню отредактировано, ID остается тем же
        except TelegramAPIError:
            # Если не удалось отредактировать (например, текст не изменился, но кнопки изменились)
            # Пробуем еще раз с force=True (через edit_message_reply_markup)
            try:
                await bot.edit_message_reply_markup(
                    chat_id=chat_id,
                    message_id=markup_id,
                    reply_markup=nav_kb
                )
                # Если нужно обновить текст, пробуем еще раз
                try:
                    await bot.edit_message_text(
                        text=menu_text,
                        chat_id=chat_id,
                        message_id=markup_id,
                        reply_markup=nav_kb,
                        parse_mode="HTML"
                    )
                except:
                    pass
            except TelegramAPIError:
                # Если и это не сработало, только тогда пересоздаем
                try:
                    await _safe_delete(bot, chat_id, [markup_id])
                except:
                    pass
                m_menu = await bot.send_message(chat_id, menu_text, reply_markup=nav_kb, parse_mode="HTML")
                await state.update_data(last_markup_id=m_menu.message_id)
    else:
        # Меню нужно пересоздать (контент создан заново или меню не существует)
        if markup_id:
            # Удаляем старое меню перед созданием нового
            await _safe_delete(bot, chat_id, [markup_id])
        
        # Создаем новое меню ПОСЛЕ контента
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
    """Обработчик генерации изображения"""
    # Сразу отвечаем на callback, чтобы кнопка не задерживалась
    await cb.answer()
    
    d = await state.get_data()
    prompt = d.get('image_prompt')
    
    # Если промпт не сохранен, генерируем его из текста
    if not prompt:
        txt = d.get('text') or d.get('raw_text')
        if txt:
            # Сначала генерируем промпт из текста с помощью LLM
            logger.info(f"🎨 Генерация промпта для изображения из текста (длина: {len(txt)} символов)")
            prompt = await create_image_prompt(txt)
            
            # Если генерация не удалась, используем простой перевод
            if not prompt:
                logger.warning("⚠️ Не удалось сгенерировать промпт, используем перевод")
                prompt = await translate_prompt_to_english(txt[:1000])
        else:
            await cb.answer("❌ Нет текста для генерации промпта.", show_alert=True)
            return
    
    if not prompt:
        await cb.answer("❌ Не удалось создать промпт для изображения.", show_alert=True)
        return
    
    logger.info(f"✅ Используется промпт для генерации: {prompt[:100]}...")
    
    mid = cb.message.message_id
    chat_id = cb.message.chat.id
    
    # Обновляем сообщение с индикатором загрузки
    try:
        await bot.edit_message_text(
            text="🎨 <b>Stable Diffusion:</b> Генерирую промпт и рисую...", 
            chat_id=chat_id, 
            message_id=mid,
            parse_mode="HTML"
        )
    except:
        pass
    
    task = asyncio.create_task(animate_message(bot, chat_id, mid, "Генерация"))

    try:
        img_bytes, _ = await async_generate_stable_diffusion_image(
            bot, chat_id, mid, prompt, cb.from_user.id, task
        )
        if img_bytes:
            await state.update_data(
                generated_image_bytes=img_bytes,
                image_base64=base64.b64encode(img_bytes).decode('utf-8'),
                has_generated_image=True,
                force_no_media=False,
                image_prompt=prompt
            )
            logger.info(f"✅ Изображение успешно сгенерировано для пользователя {cb.from_user.id}")
        else:
            logger.error("❌ Генерация изображения вернула None")
            await bot.edit_message_text(
                text="❌ <b>Ошибка:</b> Не удалось сгенерировать изображение.", 
                chat_id=chat_id, 
                message_id=mid,
                parse_mode="HTML"
            )
    except Exception as e:
        logger.error(f"❌ Ошибка Stable Diffusion: {e}", exc_info=True)
        try:
            await bot.edit_message_text(
                text=f"❌ <b>Ошибка генерации:</b>\n{str(e)[:200]}", 
                chat_id=chat_id, 
                message_id=mid,
                parse_mode="HTML"
            )
        except:
            pass
    finally:
        if not task.done(): 
            task.cancel()
        await state.update_data(last_markup_id=mid)
        is_fwd = (d.get("source") == "forwarded_post")
        await render_preview_post(bot, chat_id, state, is_forwarded=is_fwd, edit_message_id=mid)

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
        
        next_idx = d.get('current_post_index', 0) + 1
        total = d.get('total_posts', 1)
        
        await state.update_data(
            current_post_index=next_idx,
            last_message_ids=[], 
            last_markup_id=None,
            text=None, generated_image_bytes=None, image_base64=None, 
            original_photo_file_id=None, original_video_file_id=None, media_group_raw=None
        )

        txt = "✅ <b>Опубликовано!</b>"
        if next_idx >= total: txt += "\n🏁 Список завершен."
        await bot.send_message(chat_id, txt, reply_markup=post_publish_actions_keyboard())

    except Exception as e:
        logger.exception("Pub Error")
        await _safe_delete(bot, chat_id, stat_msg.message_id)
        await bot.send_message(chat_id, f"❌ Ошибка: {e}")
        # Не передаем edit_message_id, так как это ошибка и нужно показать состояние
        await render_preview_post(bot, chat_id, state)

@router.callback_query(F.data == "return_found_posts")
async def cb_next_post(cb: CallbackQuery, state: FSMContext, bot: Bot):
    from handlers.topics import _load_post_to_state

    d = await state.get_data()
    res = d.get('search_results', [])
    idx = d.get('current_post_index', 0)

    if idx >= len(res):
        await cb.message.edit_text("🏁 Конец.", reply_markup=topics_keyboard())
        return

    await _safe_delete(bot, cb.message.chat.id, cb.message.message_id)
    _load_post_to_state(d, res[idx])
    await state.update_data(d)
    await state.set_state(FormState.viewing_post)
    # Передаем ID меню для редактирования
    await render_preview_post(bot, cb.message.chat.id, state, edit_message_id=cb.message.message_id)