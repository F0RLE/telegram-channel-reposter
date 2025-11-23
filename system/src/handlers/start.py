import logging
import asyncio
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

# Imports
from keyboards.inline import main_menu_keyboard, topics_keyboard
from core.fsm_states import FormState 

logger = logging.getLogger(__name__)
router = Router()

# ==========================================
# 1. START COMMAND
# ==========================================
@router.message(Command("start"))
async def command_start_handler(message: types.Message, state: FSMContext):
    """
    Handle /start command. Resets everything.
    
    Args:
        message: Telegram message object
        state: FSM context for state management
    """
    user_id = message.from_user.id
    await state.clear()
    
    logger.info(f"Пользователь {user_id} запустил бота.") 

    await message.answer(
        "Привет! Что будем делать?",
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML"
    )

# ==========================================
# 2. BACK TO MAIN MENU (Unified)
# ==========================================
@router.callback_query(F.data.in_({"back_main", "back_to_main"}))
async def callback_back_main(cb: types.CallbackQuery, state: FSMContext):
    """
    Returns user to Main Menu. 
    Handles deletion of media messages if necessary.
    
    Args:
        cb: Callback query object
        state: FSM context for state management
    """
    await state.clear()
    
    # Try to edit the message to Main Menu
    try:
        await cb.message.edit_text(
            "Привет! Что будем делать?",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
    except TelegramBadRequest:
        # If message had media (photo/video), we cannot edit it to text.
        # Delete old message and send a new one.
        try: await cb.message.delete()
        except: pass
        
        await cb.message.answer(
            "Привет! Что будем делать?",
            reply_markup=main_menu_keyboard(),
            parse_mode="HTML"
        )
        
    await cb.answer()

# ==========================================
# 3. CHOOSE TOPIC
# ==========================================
@router.callback_query(F.data == "choose_topic")
async def callback_choose_topic(cb: types.CallbackQuery, state: FSMContext):
    """
    Opens the Topic Selection menu.
    Resets all generation data to avoid conflicts.
    """
    # Explicitly reset data fields
    await state.set_data({
        'source': 'parser',
        'current_post_index': 0,
        'search_results': None,
        # Clear content fields
        'raw_text': None, 'text': None, 'link': None,
        'has_media': False, 'force_no_media': False,
        'has_generated_image': False, 'generated_image_bytes': None,
        'original_photo_file_id': None, 'original_video_file_id': None
    })
    
    await state.set_state(FormState.awaiting_topic)

    await cb.message.edit_text(
        "<b>Выберите тему</b> для поиска постов:",
        reply_markup=topics_keyboard(),
        parse_mode="HTML"
    )
    await cb.answer()

# ==========================================
# 4. IGNORE HANDLER
# ==========================================
@router.callback_query(F.data == "ignore")
async def callback_ignore(cb: types.CallbackQuery):
    """
    Empty handler for decorative buttons (like page counters).
    """
    await cb.answer()