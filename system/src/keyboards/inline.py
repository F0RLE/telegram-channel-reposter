from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config.settings import TELEGRAM_CHANNELS, reload_channels

def main_menu_keyboard() -> InlineKeyboardMarkup:
    """
    Start Menu: Choose Topic or Manual Forward.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="📰 Выбрать тему", callback_data="choose_topic")
    builder.button(text="📤 Переслать пост", callback_data="forward_post")
    builder.adjust(1)
    return builder.as_markup()

def topics_keyboard() -> InlineKeyboardMarkup:
    """
    List of available topics from channels.json.
    Перезагружает каналы перед созданием клавиатуры для актуальности.
    """
    # Перезагружаем каналы для актуальности
    reload_channels()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="🔥 Все темы", callback_data="topic:all")
    
    for topic in TELEGRAM_CHANNELS.keys():
        builder.button(text=topic, callback_data=f"topic:{topic}")
    
    builder.adjust(1, 2) # 1 wide row, then 2 columns
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_main"))
    return builder.as_markup()

def get_post_navigation_keyboard(
    current: int, 
    total: int, 
    has_media: bool, 
    link: str = None,
    is_single_post: bool = False,
    back_callback: str = "back_topics",
    has_pending_messages: bool = False
) -> InlineKeyboardMarkup:
    """
    Main Post Navigation (Prev/Next/Counter/Actions).
    """
    builder = InlineKeyboardBuilder()
    
    # Navigation Row (Only if it's a list of posts)
    if not is_single_post:
        row_btns = []
        
        # Prev Button
        if current > 0:
            row_btns.append(InlineKeyboardButton(text="⬅️", callback_data="prev_post"))
        else:
            # Spacer for alignment
            row_btns.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            
        # Counter (Click to Jump)
        row_btns.append(InlineKeyboardButton(text=f" {current + 1} / {total} ", callback_data="trigger_jump"))
        
        # Next Button
        if current < total - 1:
            row_btns.append(InlineKeyboardButton(text="➡️", callback_data="next_post"))
        else:
            row_btns.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
            
        builder.row(*row_btns)
    
    # Message cleanup buttons (for forwarded posts)
    if has_pending_messages:
        builder.row(
            InlineKeyboardButton(text="✅ Оставить сообщения", callback_data="keep_user_messages"),
            InlineKeyboardButton(text="🗑️ Удалить сообщения", callback_data="delete_user_messages")
        )
    
    # Original Link
    if link:
        builder.row(InlineKeyboardButton(text="🔗 Оригинал поста", url=link))
    
    # Action Menu
    builder.row(InlineKeyboardButton(text="⚙️ Меню действий", callback_data="open_actions_menu"))
    
    # Back Button
    back_text = "🔙 В главное меню" if back_callback == "back_main" else "🔙 К списку тем"
    builder.row(InlineKeyboardButton(text=back_text, callback_data=back_callback))
    
    return builder.as_markup()

def actions_submenu_keyboard(has_media: bool) -> InlineKeyboardMarkup:
    """
    Submenu: Edit Text, Edit Media, Publish.
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✍️ Текст", callback_data="open_text_actions"))
    builder.row(InlineKeyboardButton(text="🖼️ Медиа", callback_data="open_media_actions"))
    builder.row(InlineKeyboardButton(text="🚀 Опубликовать", callback_data="confirm_publish"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_post_actions"))
    return builder.as_markup()

def text_actions_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🤖 Переписать (LLM)", callback_data="rewrite_text"))
    builder.row(InlineKeyboardButton(text="📝 Ввести вручную", callback_data="manual_text_input"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="open_actions_menu")) 
    return builder.as_markup()

def media_actions_keyboard(has_media: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✨ Сгенерировать (SD)", callback_data="generate_image"))
    builder.row(InlineKeyboardButton(text="📝 Задать Промпт", callback_data="manual_prompt_input")) 
    # builder.row(InlineKeyboardButton(text="📎 Загрузить свое", callback_data="manual_media_input")) # Optional
    
    if has_media:
        builder.row(InlineKeyboardButton(text="🗑️ Удалить медиа", callback_data="choose_remove_media"))
        builder.row(InlineKeyboardButton(text="🗑️ Удалить всё медиа", callback_data="remove_all_media"))
        
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="open_actions_menu"))
    return builder.as_markup()

def confirm_publish_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Да, опубликовать", callback_data="publish"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="open_actions_menu")) 
    return builder.as_markup()

def post_publish_actions_keyboard() -> InlineKeyboardMarkup:
    """
    Shown after successful publish.
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➡️ Следующий пост", callback_data="return_found_posts"))
    builder.row(InlineKeyboardButton(text="🔙 К списку тем", callback_data="back_topics"))
    return builder.as_markup()

def back_main_keyboard() -> InlineKeyboardMarkup:
    """
    General Cancel button -> Main Menu.
    """
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="back_main"))
    return builder.as_markup()

def cancel_text_input_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_text_input"))
    return builder.as_markup()

def cancel_jump_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Отмена", callback_data="cancel_jump"))
    return builder.as_markup()