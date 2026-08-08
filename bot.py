"""Kabahome Bot - Telegram assistant for server management."""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

# Health check server imports
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"<h1>Kabahome Bot Online</h1><p>Assistente do servidor kabahome</p>")
    def do_POST(self):
        self.send_response(200)
        self.end_headers()
    def log_message(self, format, *args):
        pass  # quiet

def start_health_server(port):
    """Start a minimal HTTP server for Cloudflare tunnel health checks."""
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Health check server listening on port {port}")
    return server

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from llm import chat, clear_history

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
PORT = int(os.getenv("PORT", "8080"))
ALLOWED_USERS = os.getenv("ALLOWED_USERS", "")

allowed_ids = set()
if ALLOWED_USERS:
    for uid in ALLOWED_USERS.split(","):
        uid = uid.strip()
        if uid.isdigit():
            allowed_ids.add(int(uid))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("kabahome-bot")


def is_allowed(user_id: int) -> bool:
    if not allowed_ids:
        return True
    return user_id in allowed_ids


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"*Kabahome Bot* - Assistente do servidor\n\n"
        f"Ola, {user.first_name}! Pergunte o que quiser sobre o servidor "
        f"kabahome (192.168.1.99).\n\n"
        f"*Comandos:*\n"
        f"/status - Status rapido\n"
        f"/discos - Uso de disco\n"
        f"/ram - Uso de memoria\n"
        f"/containers - Lista containers\n"
        f"/servicos - Lista servicos Swarm\n"
        f"/logs <servico> - Logs\n"
        f"/limpar - Limpa historico",
        parse_mode="Markdown",
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process all text messages through the LLM with robust error handling."""
    user = update.effective_user
    user_id = user.id
    text = update.message.text

    if not is_allowed(user_id):
        await update.message.reply_text("???? Acesso nao autorizado.")
        return

    if text.startswith("/"):
        return

    # Send immediate "processing" message so user knows bot is working
    status_msg = await update.message.reply_text("??? Processando... aguarde um momento.")

    try:
        # Show typing indicator
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        # Process through LLM (this may take a while)
        response = chat(user_id, text)

        # Check if response is valid
        if not response or response.strip() == "":
            response = "?????? Nao consegui processar sua solicitacao. Tente novamente."

        # Delete the "processing" message
        try:
            await status_msg.delete()
        except Exception:
            pass

        # Send the real response
        if len(response) > 4000:
            chunks = [response[i:i+3800] for i in range(0, len(response), 3800)]
            for i, chunk in enumerate(chunks):
                prefix = f"({i+1}/{len(chunks)})\n" if len(chunks) > 1 else ""
                if i == 0:
                    await update.message.reply_text(prefix + chunk, parse_mode=None)
                else:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=prefix + chunk
                    )
        else:
            await update.message.reply_text(response, parse_mode=None)

    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {e}")
        try:
            await status_msg.edit_text(f"??? Erro ao processar: {str(e)[:200]}\nTente novamente.")
        except Exception:
            await update.message.reply_text("??? Ocorreu um erro. Tente novamente.")
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return
    status_msg = await update.message.reply_text("??? Consultando status...")
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        response = get_status()
        try:
            await status_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(response, parse_mode=None)
    except Exception as e:
        await status_msg.edit_text(f"??? Erro: {str(e)[:200]}")
async def discos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return
    status_msg = await update.message.reply_text("??? Consultando discos...")
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        response = get_discos()
        try:
            await status_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(response, parse_mode=None)
    except Exception as e:
        await status_msg.edit_text(f"??? Erro: {str(e)[:200]}")
async def ram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return
    status_msg = await update.message.reply_text("??? Consultando RAM...")
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        response = get_ram()
        try:
            await status_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(response, parse_mode=None)
    except Exception as e:
        await status_msg.edit_text(f"??? Erro: {str(e)[:200]}")
async def containers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return
    status_msg = await update.message.reply_text("??? Consultando containers...")
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        response = get_containers()
        try:
            await status_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(response, parse_mode=None)
    except Exception as e:
        await status_msg.edit_text(f"??? Erro: {str(e)[:200]}")
async def servicos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return
    status_msg = await update.message.reply_text("??? Consultando servicos...")
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        response = get_servicos()
        try:
            await status_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(response, parse_mode=None)
    except Exception as e:
        await status_msg.edit_text(f"??? Erro: {str(e)[:200]}")
async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return
    if not context.args:
        await update.message.reply_text("Uso: /logs <nome-do-servico>")
        return
    status_msg = await update.message.reply_text("??? Buscando logs...")
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        response = get_logs(" ".join(context.args))
        try:
            await status_msg.delete()
        except Exception:
            pass
        await update.message.reply_text(response, parse_mode=None)
    except Exception as e:
        await status_msg.edit_text(f"??? Erro: {str(e)[:200]}")
async def limpar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return
    clear_history(user_id)
    await update.message.reply_text("Historico da conversa limpo.")


def main():
    if not TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN nao definido!")
        sys.exit(1)

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("discos", discos_cmd))
    app.add_handler(CommandHandler("ram", ram_cmd))
    app.add_handler(CommandHandler("containers", containers_cmd))
    app.add_handler(CommandHandler("servicos", servicos_cmd))
    app.add_handler(CommandHandler("logs", logs_cmd))
    app.add_handler(CommandHandler("limpar", limpar_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start health check HTTP server for Cloudflare tunnel
    # This prevents 502 Bad Gateway when accessing https://bot.kabaweb.in/
    # The health server responds to GET / with status 200
    start_health_server(PORT)
    logger.info(f"Health check server rodando na porta {PORT}")

    # Always use polling - it's more reliable and avoids event loop issues
    # Note: we do NOT register a webhook because that would disable polling
    if WEBHOOK_URL:
        logger.info(f"WEBHOOK_URL configurada ({WEBHOOK_URL}) mas usando polling para estabilidade")
        logger.info("O health server HTTP responde ao Cloudflare Tunnel na mesma porta")

    logger.info("Iniciando em modo polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

