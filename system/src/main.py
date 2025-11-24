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
# 2. SMART PATH SEARCH
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Check debug mode from environment variable
DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() in ("true", "1", "yes")

has_modules_here = os.path.exists(os.path.join(current_dir, "modules"))
has_modules_up = os.path.exists(os.path.join(parent_dir, "modules"))

# Initialize logger early for debug messages
logging.basicConfig(level=logging.DEBUG if DEBUG_MODE else logging.INFO, format='%(message)s')
logger = logging.getLogger("bot")

if DEBUG_MODE:
    logger.debug(f"Startup point: {current_dir}")

if has_modules_here:
    if DEBUG_MODE:
        logger.debug("✅ Folders found NEXT TO main.py")
    sys.path.insert(0, current_dir)
elif has_modules_up:
    if DEBUG_MODE:
        logger.debug(f"⚠️ Folders found ONE LEVEL UP ({parent_dir}). Connecting them.")
    sys.path.insert(0, parent_dir)
else:
    error_msg = (
        "\n❌ CRITICAL ERROR: Code folders not found!\n"
        f"Bot searched for 'modules' folder here:\n  1. {current_dir}\n  2. {parent_dir}\n"
        "\nSOLUTION: Move folders (modules, handlers, config, core, keyboards) next to main.py!"
    )
    print(error_msg)
    logger.critical(error_msg)
    time.sleep(30)
    sys.exit(1)

# ==========================================
# 3. IMPORTS AND STARTUP
# ==========================================
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

try:
    from config.settings import BOT_TOKEN, CONFIG_DIR
    from core.fsm_states import FormState
    from handlers.start import router as start_router
    from handlers.topics import router as topics_router
    from handlers.post_actions import router as post_actions_router
    from handlers.forward import router as forward_router
except ImportError as e:
    error_msg = f"\n❌ IMPORT ERROR: {e}\nCurrent sys.path:"
    print(error_msg)
    for p in sys.path:
        print(f"  - {p}")
    logger.critical(error_msg)
    time.sleep(30)
    sys.exit(1)

# ==========================================
# 4. LOGGING CONFIGURATION
# ==========================================

class RussianFormatter(logging.Formatter):
    """Formatter for Russian log localization"""
    LEVEL_NAMES = {
        'DEBUG': 'ОТЛАДКА',
        'INFO': 'ИНФО',
        'WARNING': 'ПРЕДУПРЕЖДЕНИЕ',
        'ERROR': 'ОШИБКА',
        'CRITICAL': 'КРИТИЧЕСКАЯ ОШИБКА'
    }
    
    def format(self, record):
        # Translate log level names
        if record.levelname in self.LEVEL_NAMES:
            record.levelname = self.LEVEL_NAMES[record.levelname]
        return super().format(record)

# Configure logging with Russian localization
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(RussianFormatter("%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
logging.basicConfig(
    level=logging.INFO,
    handlers=[handler],
    force=True
)
logger = logging.getLogger("bot")

for lib in ['aiogram', 'httpcore', 'httpx']:
    logging.getLogger(lib).setLevel(logging.WARNING)

# ==========================================
# 5. CLEANUP "LAST MESSAGES"
# ==========================================
# Файл для сохранения сообщений, которые нужно удалить при следующем запуске
MESSAGES_TO_DELETE_FILE = os.path.join(CONFIG_DIR, "messages_to_delete.json")

def save_messages_to_delete(chat_id: int, message_ids: list):
    """Сохраняет ID сообщений для удаления при следующем запуске"""
    try:
        messages_to_delete = {}
        if os.path.exists(MESSAGES_TO_DELETE_FILE):
            try:
                with open(MESSAGES_TO_DELETE_FILE, 'r', encoding='utf-8') as f:
                    messages_to_delete = json.load(f)
            except:
                messages_to_delete = {}
        
        chat_key = str(chat_id)
        if chat_key not in messages_to_delete:
            messages_to_delete[chat_key] = []
        
        # Добавляем новые ID, избегая дубликатов
        existing = set(messages_to_delete[chat_key])
        for msg_id in message_ids:
            if msg_id and msg_id not in existing:
                messages_to_delete[chat_key].append(msg_id)
        
        with open(MESSAGES_TO_DELETE_FILE, 'w', encoding='utf-8') as f:
            json.dump(messages_to_delete, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения сообщений для удаления: {e}")

async def delete_saved_messages(bot: Bot):
    """Удаляет сообщения, сохраненные в файле (при запуске бота)"""
    if not os.path.exists(MESSAGES_TO_DELETE_FILE):
        return
    
    try:
        with open(MESSAGES_TO_DELETE_FILE, 'r', encoding='utf-8') as f:
            messages_to_delete = json.load(f)
        
        deleted_count = 0
        for chat_key, msg_ids in messages_to_delete.items():
            try:
                chat_id = int(chat_key)
                for msg_id in msg_ids:
                    try:
                        await bot.delete_message(chat_id, msg_id)
                        deleted_count += 1
                        logger.info(f"✅ Удалено сохраненное сообщение {msg_id} из чата {chat_id}")
                    except Exception as e:
                        logger.debug(f"Не удалось удалить сообщение {msg_id}: {e}")
            except (ValueError, TypeError) as e:
                logger.warning(f"⚠️ Неверный chat_id {chat_key}: {e}")
        
        # Удаляем файл после успешного удаления
        if deleted_count > 0:
            try:
                os.remove(MESSAGES_TO_DELETE_FILE)
                logger.info(f"✅ Удалено {deleted_count} сохраненных сообщений при запуске")
            except:
                pass
    except Exception as e:
        logger.error(f"❌ Ошибка удаления сохраненных сообщений: {e}")

async def delete_all_last_messages(bot: Bot, dispatcher: Dispatcher):
    """
    Удаляет все последние сообщения бота при выключении.
    Обрабатывает как last_message_id, так и last_message_ids (список).
    Если не удается удалить - сохраняет в файл для удаления при следующем запуске.
    """
    logger.info("🗑️ Начало удаления всех последних сообщений...")
    storage = dispatcher.storage
    if not isinstance(storage, MemoryStorage):
        logger.warning("⚠️ Storage не является MemoryStorage, пропускаем удаление")
        return

    try:
        keys = list(storage.storage.keys())
        logger.info(f"📋 Найдено {len(keys)} активных сессий для обработки")
    except (AttributeError, TypeError, KeyError) as e:
        logger.error(f"❌ Ошибка получения ключей storage: {e}")
        return

    deleted_count = 0
    messages_to_save = {}  # Сохраняем сообщения, которые не удалось удалить
    
    # Удаляем сообщения для всех состояний, не только viewing_post
    for key in keys:
        try:
            data = await storage.get_data(key=key)
            if not data:
                continue
            
            # Получаем chat_id
            try:
                chat_id = key.chat_id if hasattr(key, "chat_id") else key[1]
            except (AttributeError, IndexError, TypeError) as e:
                logger.warning(f"⚠️ Не удалось получить chat_id для ключа {key}: {e}")
                continue
            
            message_ids_to_delete = []
            
            # Удаляем last_message_id (одно сообщение)
            msg_id = data.get("last_message_id")
            if msg_id:
                message_ids_to_delete.append(msg_id)
            
            # Удаляем last_message_ids (список сообщений)
            msg_ids = data.get("last_message_ids", [])
            if isinstance(msg_ids, list) and msg_ids:
                message_ids_to_delete.extend(msg_ids)
            
            # Удаляем last_markup_id (сообщение с клавиатурой) - это главное меню и другие меню
            markup_id = data.get("last_markup_id")
            if markup_id:
                message_ids_to_delete.append(markup_id)
            
            # Пытаемся удалить все сообщения
            failed_ids = []
            for msg_id in message_ids_to_delete:
                if not msg_id:
                    continue
                try:
                    await bot.delete_message(chat_id, msg_id)
                    deleted_count += 1
                    logger.info(f"✅ Удалено сообщение {msg_id} из чата {chat_id}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось удалить сообщение {msg_id}: {e}")
                    failed_ids.append(msg_id)
            
            # Сохраняем сообщения, которые не удалось удалить
            if failed_ids:
                if chat_id not in messages_to_save:
                    messages_to_save[chat_id] = []
                messages_to_save[chat_id].extend(failed_ids)
            
            # Очищаем состояние
            await storage.set_state(key=key, state=None)
            await storage.set_data(key=key, data={})

        except Exception as e:
            logger.error(f"❌ Ошибка при обработке ключа {key}: {e}")
    
    # Сохраняем сообщения, которые не удалось удалить, для удаления при следующем запуске
    if messages_to_save:
        for chat_id, msg_ids in messages_to_save.items():
            save_messages_to_delete(chat_id, msg_ids)
        logger.info(f"💾 Сохранено {sum(len(ids) for ids in messages_to_save.values())} сообщений для удаления при следующем запуске")
    
    logger.info(f"✅ Удаление завершено. Всего удалено сообщений: {deleted_count}")

# ==========================================
# 6. BOT STARTUP
# ==========================================
# Глобальные переменные для graceful shutdown
_bot_instance = None
_dispatcher_instance = None
_shutdown_event = asyncio.Event()

async def graceful_shutdown():
    """Выполняет graceful shutdown: удаляет сообщения, затем завершает бота"""
    global _bot_instance, _dispatcher_instance
    
    if _bot_instance and _dispatcher_instance:
        logger.info("🔄 Начало graceful shutdown: удаление сообщений...")
        try:
            # Удаляем все последние сообщения
            await delete_all_last_messages(_bot_instance, _dispatcher_instance)
            logger.info("✅ Сообщения удалены")
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении сообщений: {e}")
        
        # Закрываем бота
        try:
            await _bot_instance.session.close()
            logger.info("✅ Бот закрыт")
        except Exception as e:
            logger.error(f"❌ Ошибка при закрытии бота: {e}")
    
    _shutdown_event.set()

async def main():
    global _bot_instance, _dispatcher_instance
    
    if not BOT_TOKEN:
        error_msg = "❌ Bot token is missing. Please set it in launcher settings."
        logger.error(error_msg)
        print(error_msg)
        await asyncio.sleep(10)
        return

    _bot_instance = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    _dispatcher_instance = Dispatcher(storage=MemoryStorage())

    _dispatcher_instance.shutdown.register(delete_all_last_messages)
    _dispatcher_instance.include_routers(start_router, topics_router, post_actions_router, forward_router)

    # Регистрируем обработчики сигналов для graceful shutdown
    if sys.platform != 'win32':
        signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(graceful_shutdown()))
        signal.signal(signal.SIGINT, lambda s, f: asyncio.create_task(graceful_shutdown()))

    # Output startup message immediately after initialization
    startup_msg = "✅ Bot started"
    print(startup_msg)
    logger.info("✅ Bot started and ready to work")

    # Delete webhook and wait a bit before starting polling
    await _bot_instance.delete_webhook(drop_pending_updates=True)
    
    # Удаляем сообщения, сохраненные при предыдущем запуске
    await delete_saved_messages(_bot_instance)
    
    await asyncio.sleep(1)  # Small delay to avoid conflicts
    
    # Start polling with conflict handling
    try:
        # Запускаем polling в фоне и ждем shutdown event
        polling_task = asyncio.create_task(
            _dispatcher_instance.start_polling(_bot_instance, allowed_updates=["message", "callback_query"])
        )
        
        # Ждем либо завершения polling, либо shutdown event
        done, pending = await asyncio.wait(
            [polling_task, asyncio.create_task(_shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Если получили shutdown event, останавливаем polling
        if _shutdown_event.is_set():
            logger.info("🛑 Остановка polling...")
            await _dispatcher_instance.stop_polling()
            # Отменяем задачу polling
            if not polling_task.done():
                polling_task.cancel()
                try:
                    await polling_task
                except asyncio.CancelledError:
                    pass
        
    except Exception as e:
        if "Conflict" in str(e) or "getUpdates" in str(e):
            logger.warning(f"Update conflict, waiting... {e}")
            await asyncio.sleep(5)
            await _dispatcher_instance.start_polling(_bot_instance, allowed_updates=["message", "callback_query"])
        else:
            logger.error(f"Error starting polling: {e}")
            raise
    finally:
        # В любом случае выполняем graceful shutdown
        logger.info("🔄 Выполнение cleanup в finally блоке...")
        await graceful_shutdown()


if __name__ == "__main__":
    bot_instance = None
    dispatcher_instance = None
    
    async def run_with_cleanup():
        global bot_instance, dispatcher_instance
        try:
            await main()
        except KeyboardInterrupt:
            logger.info("🛑 Bot stopped by user.")
        except Exception as e:
            logger.critical(f"❌ Critical error: {e}", exc_info=True)
        finally:
            # В любом случае удаляем сообщения перед завершением
            if bot_instance and dispatcher_instance:
                try:
                    logger.info("🔄 Удаление сообщений перед завершением...")
                    await delete_all_last_messages(bot_instance, dispatcher_instance)
                    logger.info("✅ Сообщения удалены")
                except Exception as e:
                    logger.error(f"❌ Ошибка при удалении сообщений: {e}")
                finally:
                    try:
                        await bot_instance.session.close()
                    except:
                        pass
    
    try:
        asyncio.run(run_with_cleanup())
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user.")
    except Exception as e:
        logger.critical(f"❌ Critical error: {e}", exc_info=True)
        time.sleep(10)
