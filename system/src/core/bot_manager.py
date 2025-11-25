"""Bot instance manager for centralized bot lifecycle management"""
import asyncio
import logging
from typing import Optional
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

logger = logging.getLogger(__name__)


class BotManager:
    """Manages bot instance and lifecycle"""
    
    def __init__(self):
        self._bot: Optional[Bot] = None
        self._dispatcher: Optional[Dispatcher] = None
        self._shutdown_event = asyncio.Event()
    
    @property
    def bot(self) -> Optional[Bot]:
        """Get bot instance"""
        return self._bot
    
    @property
    def dispatcher(self) -> Optional[Dispatcher]:
        """Get dispatcher instance"""
        return self._dispatcher
    
    @property
    def shutdown_event(self) -> asyncio.Event:
        """Get shutdown event"""
        return self._shutdown_event
    
    def initialize(self, bot_token: str) -> None:
        """
        Initialize bot and dispatcher instances.
        
        Args:
            bot_token: Telegram bot token
        """
        from aiogram.client.default import DefaultBotProperties
        
        self._bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode="HTML"))
        self._dispatcher = Dispatcher(storage=MemoryStorage())
        logger.info("Bot and dispatcher initialized")
    
    async def close(self) -> None:
        """Close bot session"""
        if self._bot:
            try:
                await self._bot.session.close()
                logger.info("Bot session closed")
            except Exception as e:
                logger.error(f"Error closing bot session: {e}")
    
    def is_initialized(self) -> bool:
        """Check if bot is initialized"""
        return self._bot is not None and self._dispatcher is not None

