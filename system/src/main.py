import sys
import os
import time
import asyncio
import logging
import signal
import json

# ==========================================
# 1. CORRECT ENCODING IN WINDOWS CONSOLE
# ==========================================
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ==========================================
# 2. SETUP PATHS & LOGGING
# ==========================================
# Add current directory to sys.path to ensure imports work correctly
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Initialize logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("bot")

# Reduce noise from libraries
for lib in ['aiogram', 'httpcore', 'httpx', 'aiohttp']:
    logging.getLogger(lib).setLevel(logging.WARNING)

# ==========================================
# 3. IMPORTS
# ==========================================
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

try:
    from config.settings import BOT_TOKEN, CONFIG_DIR
    from core.bot_manager import BotManager
    from core.utils import safe_delete_message
    from handlers.start import router as start_router
    from handlers.topics import router as topics_router
    from handlers.post_actions import router as post_actions_router
    from handlers.forward import router as forward_router
    from handlers.chat import router as chat_router
except ImportError as e:
    logger.critical(f"❌ IMPORT ERROR: {e}")
    sys.exit(1)

# ==========================================
# 4. CLEANUP LOGIC
# ==========================================
MESSAGES_TO_DELETE_FILE = os.path.join(CONFIG_DIR, "messages_to_delete.json")

async def cleanup_last_messages(bot: Bot, dispatcher: Dispatcher):
    """
    Cleans up the last messages (menus, previews) when the bot shuts down.
    """
    logger.info("🗑️ Starting cleanup of last messages...")
    storage = dispatcher.storage
    
    # Check if storage is accessible
    if not isinstance(storage, MemoryStorage) or not hasattr(storage, 'storage'):
        return

    messages_to_save = {}
    
    try:
        # Iterate over all active states
        keys = list(storage.storage.keys())
        for key in keys:
            try:
                data = await storage.get_data(key=key)
                if not data: continue

                # Extract chat_id
                chat_id = key.chat_id if hasattr(key, "chat_id") else key[1]
                
                # Collect message IDs to delete
                ids_to_delete = []
                if data.get("last_message_id"):
                    ids_to_delete.append(data.get("last_message_id"))
                if data.get("last_message_ids"):
                    ids_to_delete.extend(data.get("last_message_ids"))
                if data.get("last_markup_id"):
                    ids_to_delete.append(data.get("last_markup_id"))
                
                # Delete messages
                failed_ids = []
                for mid in set(ids_to_delete):
                    if not mid: continue
                    try:
                        await bot.delete_message(chat_id, mid)
                    except Exception:
                        failed_ids.append(mid)
                
                if failed_ids:
                    if str(chat_id) not in messages_to_save:
                        messages_to_save[str(chat_id)] = []
                    messages_to_save[str(chat_id)].extend(failed_ids)
                
                # Clear state
                await storage.set_state(key=key, state=None)
                await storage.set_data(key=key, data={})
                
            except Exception as e:
                logger.error(f"Error cleaning up session {key}: {e}")

    except Exception as e:
        logger.error(f"Error iterating storage: {e}")

    # Save failed deletions to file
    if messages_to_save:
        try:
            with open(MESSAGES_TO_DELETE_FILE, 'w', encoding='utf-8') as f:
                json.dump(messages_to_save, f, indent=2)
            logger.info(f"💾 Saved {sum(len(v) for v in messages_to_save.values())} messages to delete later")
        except Exception as e:
            logger.error(f"Failed to save messages to delete: {e}")

async def delete_saved_messages(bot: Bot):
    """Deletes messages saved from previous run"""
    if not os.path.exists(MESSAGES_TO_DELETE_FILE):
        return
        
    try:
        with open(MESSAGES_TO_DELETE_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for chat_id, msg_ids in data.items():
            await safe_delete_message(bot, int(chat_id), msg_ids)
            
        os.remove(MESSAGES_TO_DELETE_FILE)
        logger.info("✅ Cleaned up saved messages from previous run")
    except Exception as e:
        logger.error(f"Error processing saved messages: {e}")

# ==========================================
# 5. MAIN BOT LOGIC
# ==========================================
bot_manager = BotManager()

async def on_startup(dispatcher: Dispatcher, bot: Bot):
    logger.info("🚀 Bot startup hooks running...")
    await bot.delete_webhook(drop_pending_updates=True)
    await delete_saved_messages(bot)
    print("✅ Bot started")

async def on_shutdown(dispatcher: Dispatcher, bot: Bot):
    logger.info("🛑 Bot shutdown hooks running...")
    await cleanup_last_messages(bot, dispatcher)
    await bot.session.close()
    logger.info("✅ Bot session closed")

async def main():
    if not BOT_TOKEN:
        logger.critical("❌ Bot token is missing!")
        return

    # Initialize Bot Manager
    bot_manager.initialize(BOT_TOKEN)
    bot = bot_manager.bot
    dp = bot_manager.dispatcher

    # Register Routers
    dp.include_routers(start_router, topics_router, post_actions_router, forward_router, chat_router)

    # Register Lifecycle Hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Start Polling
    try:
        logger.info("📡 Starting polling...")
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    except Exception as e:
        logger.critical(f"❌ Polling failed: {e}")
    finally:
        # Ensure everything is closed
        if bot.session and not bot.session.closed:
            await bot.session.close()

if __name__ == "__main__":
    try:
        # Windows specific event loop policy
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.critical(f"❌ Fatal error: {e}", exc_info=True)

