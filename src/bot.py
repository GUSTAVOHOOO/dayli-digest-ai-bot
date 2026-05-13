import os
from telegram.ext import ApplicationBuilder
from src.bot_commands import setup_handlers
from src.utils.logger import get_logger
from src.utils.config_loader import load_env

# Ensure env is loaded
load_env()
log = get_logger(__name__)

from src.storage.sqlite import init_db
from src.utils.health import start_health_server

def main():
    """Starts the Telegram bot."""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        log.error("telegram_token_missing_cannot_start_bot")
        return

    log.info("bot_initializing")
    
    # Initialize database
    init_db()
    start_health_server()
    
    # Build application
    app = ApplicationBuilder().token(token).build()

    # Setup handlers
    setup_handlers(app)

    log.info("bot_started_polling")
    
    # Start polling
    app.run_polling()

if __name__ == '__main__':
    main()
