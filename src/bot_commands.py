import os
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from src.utils.logger import get_logger
from src.storage.sqlite import get_last_digest_date, get_articles_by_date
from src.storage.redis_cache import get_dlq_items, clear_dlq

log = get_logger(__name__)

# Ensure ADMIN_CHAT_ID is set
ADMIN_CHAT_ID = int(os.getenv('ADMIN_CHAT_ID', '0'))

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    await update.message.reply_text(
        "🤖 <b>AI Daily Digest Bot</b>\n\n"
        "Este bot envia um resumo diário de notícias sobre IA e computação.\n\n"
        "Comandos disponíveis:\n"
        "/start - Esta mensagem\n"
        "/status - Verificar status do sistema\n"
        "/test - Enviar digest de teste (admin)\n"
        "/retry_failed - Reprocessar artigos com falha (admin)",
        parse_mode='HTML',
    )

async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /status command."""
    last_digest = get_last_digest_date()
    if last_digest:
        # get_articles_by_date already filters for 'processed' status
        # but here we might want all articles for that date to show progress
        # For simplicity, let's use the date to count
        from src.storage.sqlite import get_connection
        import sqlite3
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT status, COUNT(*) as count FROM processed_articles WHERE date_processed LIKE ? GROUP BY status",
                (f"{last_digest[:10]}%",)
            )
            stats = {row['status']: row['count'] for row in cursor.fetchall()}
        
        total = sum(stats.values())
        sent = stats.get('sent', 0)
        processed = stats.get('processed', 0)
        skipped = stats.get('skipped', 0)
        failed = stats.get('failed', 0)

        text = (
            f"📊 <b>Status</b>\n\n"
            f"Último digest: {last_digest[:10]}\n"
            f"Total hoje: {total}\n"
            f"✅ Enviados: {sent}\n"
            f"🔄 Processados (aguardando): {processed}\n"
            f"⏭️ Ignorados: {skipped}\n"
            f"❌ Falhas: {failed}"
        )
    else:
        text = "📊 <b>Status</b>\n\nNenhum digest enviado ainda."

    await update.message.reply_text(text, parse_mode='HTML')

async def test_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /test command (Admin only)."""
    if update.effective_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ Acesso negado. Este comando é exclusivo para administradores.")
        return

    await update.message.reply_text("🔄 Iniciando envio do digest de teste...")

    from src.dispatchers.telegram import process_dispatch
    # Run the task synchronously for the test
    result = process_dispatch(chat_id=update.effective_chat.id)

    await update.message.reply_text(f"✅ Teste completo.\nMensagens enviadas: {result.get('sent', 0)}\nArtigos totais: {result.get('total_articles', 0)}")

async def retry_failed_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /retry_failed command (Admin only)."""
    if update.effective_user.id != ADMIN_CHAT_ID:
        await update.message.reply_text("⛔ Acesso negado.")
        return

    dlq_items = get_dlq_items()
    if not dlq_items:
        await update.message.reply_text("✅ DLQ vazia. Nenhum artigo para reprocessar.")
        return

    count = len(dlq_items)
    from src.processors.extractor import process_extract

    for item in dlq_items:
        process_extract.delay(item)

    clear_dlq()

    log.info("dlq_retry_initiated", count=count)
    await update.message.reply_text(f"🔄 {count} artigos movidos para a fila de extração.")

def setup_handlers(app: Application):
    """Registers all command handlers with the application."""
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("test", test_handler))
    app.add_handler(CommandHandler("retry_failed", retry_failed_handler))
