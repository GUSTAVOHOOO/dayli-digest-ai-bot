import asyncio
import os
from typing import List
from telegram import Bot
from telegram.error import RetryAfter
from telegram.constants import ParseMode
from src.utils.logger import get_logger
from src.utils.config_loader import load_env

# Ensure env is loaded
load_env()
log = get_logger(__name__)

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')

class TelegramDispatcher:
    """Handles sending messages to Telegram with rate limiting and flood protection."""

    def __init__(self):
        if not BOT_TOKEN:
            log.error("telegram_token_missing")
            # We don't raise here to allow the class to be instantiated for imports/tests
            # but methods will fail if token is empty
        self.bot = Bot(token=BOT_TOKEN)
        self.rate_limit_delay = 1.0  # seconds between messages

    async def _send_single(self, chat_id: int, text: str) -> bool:
        """Sends a single message to a chat."""
        if not BOT_TOKEN:
            log.error("send_failed_token_missing")
            return False

        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
            return True
        except RetryAfter as e:
            log.warning("flood_wait", seconds=e.retry_after)
            await asyncio.sleep(e.retry_after)
            return await self._send_single(chat_id, text)
        except Exception as e:
            log.error("send_message_error", chat_id=chat_id, error=str(e))
            return False

    async def send_message(self, chat_id: int, text: str) -> bool:
        """Async interface for sending a single message."""
        return await self._send_single(chat_id, text)

    async def send_messages(self, chat_id: int, messages: List[str]) -> int:
        """Sends multiple messages with rate limiting."""
        sent = 0
        for msg in messages:
            success = await self._send_single(chat_id, msg)
            if success:
                sent += 1
                if sent < len(messages):
                    await asyncio.sleep(self.rate_limit_delay)
            else:
                log.error("message_send_failed", chat_id=chat_id, index=sent)

        log.info("messages_sent", chat_id=chat_id, sent=sent, total=len(messages))
        return sent

    def send_messages_sync(self, chat_id: int, messages: List[str]) -> int:
        """Sync wrapper for sending messages, suitable for Celery workers."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        try:
            return loop.run_until_complete(self.send_messages(chat_id, messages))
        finally:
            # We don't close the loop if we didn't create it
            pass

from datetime import datetime
from src.celery_app import app
from src.storage.sqlite import get_articles_by_date, save_article

@app.task(
    name='src.dispatchers.telegram.process_dispatch',
    bind=True,
    acks_late=True,
)
def process_dispatch(self, chat_id: int = None):
    """Celery task to dispatch processed articles to Telegram."""
    if chat_id is None:
        chat_id = int(os.getenv('ADMIN_CHAT_ID', '0'))

    today = datetime.now().strftime('%Y-%m-%d')
    min_score = float(os.getenv('MIN_SCORE_THRESHOLD', '6.0'))
    
    log.info("dispatch_started", chat_id=chat_id, date=today, min_score=min_score)

    articles = get_articles_by_date(today, min_score=min_score)

    if not articles:
        log.info("no_articles_to_dispatch", chat_id=chat_id)
        return {"status": "ok", "sent": 0}

    articles_by_category = {}
    for article in articles:
        source = article.source
        if source not in articles_by_category:
            articles_by_category[source] = []
        articles_by_category[source].append(article)

    # Sort each category by score descending
    for source in articles_by_category:
        articles_by_category[source].sort(key=lambda a: a.score, reverse=True)

    from src.dispatchers.formatter import TelegramFormatter
    formatter = TelegramFormatter()
    messages = formatter.format_digest(articles_by_category, today)

    dispatcher = TelegramDispatcher()
    sent_count = dispatcher.send_messages_sync(chat_id, messages)

    # Mark as sent
    for article in articles:
        article.status = 'sent'
        save_article(article)

    log.info("dispatch_completed", chat_id=chat_id, total_messages=sent_count)

    return {"status": "ok", "sent": sent_count, "total_articles": len(articles)}
