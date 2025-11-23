import logging
import asyncio
from typing import Dict, List, Union, Optional

from aiogram import Router, types, F, Bot, BaseMiddleware
from aiogram.fsm.context import FSMContext

from core.fsm_states import FormState
from keyboards.inline import back_main_keyboard
# Local import for rendering the result
from handlers.post_actions import render_preview_post

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type == "private")

# ==========================================
# 1. MIDDLEWARE (ALBUM HANDLER)
# ==========================================
class AlbumMiddleware(BaseMiddleware):
    """
    Collects multiple messages with the same media_group_id into a single list.
    Prevents the bot from triggering multiple times for one album.
    """
    def __init__(self, latency: float = 0.6):
        # Latency increased to 0.6s to handle slow connections better
        self.latency = latency
        self.album_data: Dict[str, List[types.Message]] = {}

    async def __call__(self, handler, event, data):
        if not event.media_group_id:
            return await handler(event, data)
        
        media_group_id = str(event.media_group_id)
        
        try:
            self.album_data[media_group_id].append(event)
            return # Stop processing here, wait for the rest
        except KeyError:
            # First message of the album
            self.album_data[media_group_id] = [event]
            await asyncio.sleep(self.latency)
            
            # Retrieve and remove the album from cache
            data["album"] = self.album_data.pop(media_group_id)
            return await handler(event, data)

# Apply middleware
router.message.middleware(AlbumMiddleware())

# ==========================================
# 2. HELPERS
# ==========================================
from core.utils import safe_delete_message as _safe_delete

# ==========================================
# 3. HANDLERS
# ==========================================
@router.callback_query(F.data == "forward_post")
async def cb_start_forward(cb: types.CallbackQuery, state: FSMContext, bot: Bot):
    """
    Entry point: User clicked "Forward Post" in main menu.
    """
    await state.clear()
    await state.set_state(FormState.awaiting_forwarded_post)
    
    msg = await cb.message.edit_text(
        "📤 <b>Пересылка поста</b>\n\n"
        "Перешлите сюда сообщение из другого канала, отправьте картинку, видео или просто напишите текст.",
        reply_markup=back_main_keyboard(),
        parse_mode="HTML"
    )
    await state.update_data(instruction_message_id=msg.message_id)


@router.message(
    F.text | F.photo | F.video | F.document, 
    FormState.awaiting_forwarded_post
)
async def msg_handle_forward(
    message: types.Message, 
    state: FSMContext, 
    bot: Bot, 
    album: List[types.Message] = None
):
    """
    Handles incoming content (Single message or Album).
    """
    chat_id = message.chat.id
    msgs = album or [message]

    # Delete user messages to keep chat clean
    for m in msgs: 
        await _safe_delete(bot, chat_id, m.message_id)
    
    # Delete instruction message
    data = await state.get_data()
    if data.get("instruction_message_id"):
        await _safe_delete(bot, chat_id, data["instruction_message_id"])

    # Extract Data
    raw_text_parts = []
    media_group_raw = []
    
    for m in msgs:
        # 1. Extract Text
        txt = m.caption or m.text
        if txt: 
            raw_text_parts.append(txt)
        
        # 2. Extract Media
        if m.photo:
            media_group_raw.append({"type": "photo", "file_id": m.photo[-1].file_id})
        elif m.video:
            media_group_raw.append({"type": "video", "file_id": m.video.file_id})
        elif m.document:
            # Handle uncompressed images sent as files
            mime = m.document.mime_type or ""
            if mime.startswith("image"):
                media_group_raw.append({"type": "photo", "file_id": m.document.file_id})
            elif mime.startswith("video"):
                media_group_raw.append({"type": "video", "file_id": m.document.file_id})

    # Join text if multiple captions exist
    final_text = "\n".join(raw_text_parts)

    # Prepare State Data
    update_data = {
        "source": "forwarded_post", 
        "raw_text": final_text,
        "text": final_text,
        "has_media": bool(media_group_raw),
        "media_group_raw": media_group_raw,
        
        # Reset single file fields
        "original_photo_file_id": None,
        "original_video_file_id": None,
        
        "force_no_media": False,
        "current_post_index": 0,
        "search_results": [],
        "last_message_ids": [],
        "last_markup_id": None
    }
    
    # If only 1 media file, set it as main (optimization for render)
    if len(media_group_raw) == 1:
        item = media_group_raw[0]
        if item['type'] == 'photo': 
            update_data['original_photo_file_id'] = item['file_id']
        elif item['type'] == 'video': 
            update_data['original_video_file_id'] = item['file_id']

    await state.update_data(update_data)
    await state.set_state(FormState.viewing_post)
    
    # Render the result
    await render_preview_post(bot, chat_id, state, is_forwarded=True)