import sys
import os
import time
import asyncio
import logging

# ==========================================
# 1. КОРРЕКТНАЯ КОДИРОВКА В КОНСОЛИ WINDOWS
# ==========================================
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ==========================================
# 2. УМНЫЙ ПОИСК ПУТЕЙ
# ==========================================
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)

# Проверяем debug режим из переменной окружения
DEBUG_MODE = os.environ.get("DEBUG_MODE", "false").lower() in ("true", "1", "yes")

has_modules_here = os.path.exists(os.path.join(current_dir, "modules"))
has_modules_up = os.path.exists(os.path.join(parent_dir, "modules"))

if DEBUG_MODE:
    print(f"[DEBUG] Точка запуска: {current_dir}")

if has_modules_here:
    if DEBUG_MODE:
        print("[DEBUG] ✅ Папки найдены РЯДОМ с main.py")
    sys.path.insert(0, current_dir)
elif has_modules_up:
    if DEBUG_MODE:
        print(f"[DEBUG] ⚠️ Папки найдены УРОВНЕМ ВЫШЕ ({parent_dir}). Подключаю их.")
    sys.path.insert(0, parent_dir)

else:
    print("\n❌ КРИТИЧЕСКАЯ ОШИБКА: Папки с кодом не найдены!")
    print(f"Бот искал папку 'modules' здесь:\n  1. {current_dir}\n  2. {parent_dir}")
    print("\nРЕШЕНИЕ: Переместите папки (modules, handlers, config, core, keyboards) рядом с main.py!")
    time.sleep(30)
    sys.exit(1)

# ==========================================
# 3. ИМПОРТЫ И ЗАПУСК
# ==========================================
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

try:
    from config.settings import BOT_TOKEN
    from core.fsm_states import FormState
    from handlers.start import router as start_router
    from handlers.topics import router as topics_router
    from handlers.post_actions import router as post_actions_router
    from handlers.forward import router as forward_router
except ImportError as e:
    print(f"\n❌ ОШИБКА ИМПОРТА: {e}")
    print("Пути sys.path сейчас:")
    for p in sys.path:
        print("  -", p)
    time.sleep(30)
    sys.exit(1)

# ==========================================
# 4. ЛОГИРОВАНИЕ
# ==========================================

class RussianFormatter(logging.Formatter):
    """Форматтер для русификации логов"""
    LEVEL_NAMES = {
        'DEBUG': 'ОТЛАДКА',
        'INFO': 'ИНФО',
        'WARNING': 'ПРЕДУПРЕЖДЕНИЕ',
        'ERROR': 'ОШИБКА',
        'CRITICAL': 'КРИТИЧЕСКАЯ ОШИБКА'
    }
    
    def format(self, record):
        # Переводим уровень логирования
        if record.levelname in self.LEVEL_NAMES:
            record.levelname = self.LEVEL_NAMES[record.levelname]
        return super().format(record)

# Настраиваем логирование с русификацией
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
# 5. ОЧИСТКА "ПОСЛЕДНИХ СООБЩЕНИЙ"
# ==========================================
async def delete_all_last_messages(bot: Bot, dispatcher: Dispatcher):
    storage = dispatcher.storage
    if not isinstance(storage, MemoryStorage):
        return

    try:
        keys = list(storage.storage.keys())
    except:
        return

    target_state = FormState.viewing_post.state

    for key in keys:
        try:
            state = await storage.get_state(key=key)
            if state == target_state:
                data = await storage.get_data(key=key)
                msg_id = data.get("last_message_id")

                if msg_id:
                    try:
                        chat_id = key.chat_id if hasattr(key, "chat_id") else key[1]
                        await bot.delete_message(chat_id, msg_id)
                    except:
                        pass

                await storage.set_state(key=key, state=None)

        except Exception:
            pass

# ==========================================
# 6. ЗАПУСК БОТА
# ==========================================
async def main():
    if not BOT_TOKEN:
        logger.error("❌ Токен бота отсутствует. Укажите его в настройках лаунчера.")
        print("❌ Токен бота отсутствует. Укажите его в настройках лаунчера.")
        await asyncio.sleep(10)
        return

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())

    dp.shutdown.register(delete_all_last_messages)
    dp.include_routers(start_router, topics_router, post_actions_router, forward_router)

    # Выводим сообщение о запуске сразу после инициализации
    print("✅ Бот запущен")
    logger.info("✅ Бот запущен и готов к работе")

    # Удаляем webhook и ожидаем немного перед запуском polling
    await bot.delete_webhook(drop_pending_updates=True)
    await asyncio.sleep(1)  # Небольшая задержка для избежания конфликтов
    
    # Запускаем polling с обработкой конфликтов
    try:
        await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
    except Exception as e:
        if "Conflict" in str(e) or "getUpdates" in str(e):
            logger.warning(f"Конфликт обновлений, ожидание... {e}")
            await asyncio.sleep(5)
            await dp.start_polling(bot, allowed_updates=["message", "callback_query"])
        else:
            logger.error(f"Ошибка при запуске polling: {e}")
            raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот остановлен пользователем.")
    except Exception as e:
        logger.critical(f"❌ Критическая ошибка: {e}", exc_info=True)
        time.sleep(10)
