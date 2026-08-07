"""Kabahome Bot - Telegram assistant for server management."""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

load_dotenv()

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
    user = update.effective_user
    user_id = user.id
    text = update.message.text

    if not is_allowed(user_id):
        await update.message.reply_text("Acesso nao autorizado.")
        return

    if text.startswith("/"):
        return

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    response = chat(user_id, text)

    if len(response) > 4000:
        chunks = [response[i:i+3800] for i in range(0, len(response), 3800)]
        for i, chunk in enumerate(chunks):
            prefix = f"({i+1}/{len(chunks)})\n" if len(chunks) > 1 else ""
            await update.message.reply_text(prefix + chunk, parse_mode=None)
    else:
        await update.message.reply_text(response, parse_mode=None)


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    response = chat(user_id, "Me de um resumo rapido do status do servidor: containers, disco, RAM, uptime. Seja breve.")
    await update.message.reply_text(response, parse_mode=None)


async def discos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    response = chat(user_id, "Mostre o uso de disco do servidor.")
    await update.message.reply_text(response, parse_mode=None)


async def ram_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    response = chat(user_id, "Mostre o uso de RAM do servidor (free -h).")
    await update.message.reply_text(response, parse_mode=None)


async def containers_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    response = chat(user_id, "Liste todos os containers em execucao no servidor.")
    await update.message.reply_text(response, parse_mode=None)


async def servicos_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    response = chat(user_id, "Liste todos os servicos Docker Swarm com status das replicas.")
    await update.message.reply_text(response, parse_mode=None)


async def logs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_allowed(user_id):
        return
    service = " ".join(context.args) if context.args else ""
    if not service:
        await update.message.reply_text("Uso: /logs <nome-do-servico>")
        return
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    response = chat(user_id, f"Mostre os logs do servico {service} (ultimas 30 linhas).")
    await update.message.reply_text(response, parse_mode=None)


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

    if WEBHOOK_URL:
        logger.info(f"Tentando registrar webhook: {WEBHOOK_URL}")
        webhook_ok = False
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                app.bot.set_webhook(
                    url=f"{WEBHOOK_URL}",
                    drop_pending_updates=True,
                )
            )
            loop.close()
            webhook_info = asyncio.new_event_loop()
            asyncio.set_event_loop(webhook_info)
            info = webhook_info.run_until_complete(app.bot.get_webhook_info())
            webhook_info.close()
            logger.info(f"Webhook registrado: {info.url}")
            webhook_ok = True
        except Exception as e:
            logger.warning(f"Falha ao registrar webhook: {e}")
            logger.warning("Usando polling como fallback...")
            webhook_ok = False

        if webhook_ok:
            logger.info(f"Iniciando servidor webhook na porta {PORT}...")
            app.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                webhook_url=WEBHOOK_URL,
                drop_pending_updates=True,
            )
        else:
            logger.info("Iniciando em modo polling...")
            app.run_polling(drop_pending_updates=True)
    else:
        logger.info("Iniciando em modo polling...")
        app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()

