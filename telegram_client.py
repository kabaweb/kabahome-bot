"""Telegram User Client via Telethon - Acesso total a conta."""

import os
import asyncio
from telethon import TelegramClient

API_ID = 22377334
API_HASH = "5bba1cc718c39fc07fdd4fe20c7c4db0"
SESSION_FILE = "/mnt/storage/docker/kabahome-bot/session/assistente_kabahome.session"


def _create_client() -> TelegramClient:
    """Create a fresh client instance."""
    return TelegramClient(SESSION_FILE, API_ID, API_HASH)


# --- Funcoes async (uso com asyncio.run) ---

async def get_me():
    """Get current user info."""
    client = _create_client()
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise Exception("Session nao autorizada.")
        return await client.get_me()
    finally:
        await client.disconnect()


async def get_dialogs(limit: int = 20):
    """Get recent conversations/chats."""
    client = _create_client()
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise Exception("Session nao autorizada.")
        dialogs = await client.get_dialogs(limit=limit)
        result = []
        for d in dialogs:
            result.append({
                "id": d.id,
                "name": d.name,
                "type": "group" if d.is_group else "channel" if d.is_channel else "user",
                "unread": d.unread_count,
            })
        return result
    finally:
        await client.disconnect()


async def get_messages(chat_id, limit: int = 20):
    """Get messages from a chat (user, group, supergroup, channel)."""
    client = _create_client()
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise Exception("Session nao autorizada.")
        messages = await client.get_messages(chat_id, limit=limit)
        result = []
        for m in messages:
            if m.message:
                result.append({
                    "id": m.id,
                    "date": str(m.date),
                    "sender": m.sender_id,
                    "text": m.message[:200],
                })
        return result
    finally:
        await client.disconnect()


async def send_message(chat_id, text: str):
    """Send a message to a chat."""
    client = _create_client()
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise Exception("Session nao autorizada.")
        msg = await client.send_message(chat_id, text)
        return {"id": msg.id, "chat_id": chat_id}
    finally:
        await client.disconnect()


async def search_messages(chat_id, query: str, limit: int = 10):
    """Search messages in a chat."""
    client = _create_client()
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise Exception("Session nao autorizada.")
        messages = await client.get_messages(chat_id, search=query, limit=limit)
        result = []
        for m in messages:
            if m.message:
                result.append({
                    "id": m.id,
                    "date": str(m.date),
                    "text": m.message[:300],
                })
        return result
    finally:
        await client.disconnect()


# --- Funcoes sincronas para uso em scripts ---

def sync_get_me():
    return asyncio.run(get_me())

def sync_get_dialogs(limit=20):
    return asyncio.run(get_dialogs(limit))

def sync_get_messages(chat_id, limit=20):
    return asyncio.run(get_messages(chat_id, limit))

def sync_send_message(chat_id, text):
    return asyncio.run(send_message(chat_id, text))


# --- Singleton client para uso prolongado (mesmo event loop) ---

_client_singleton = None

def get_client() -> TelegramClient:
    """Get or create the Telethon client singleton."""
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    return _client_singleton

async def ensure_connected():
    """Ensure singleton client is connected and authorized."""
    client = get_client()
    if not client.is_connected():
        await client.connect()
    if not await client.is_user_authorized():
        raise Exception("Telegram session nao autorizada. Faca login primeiro.")
    return client

async def disconnect_singleton():
    """Disconnect singleton client."""
    global _client_singleton
    if _client_singleton:
        await _client_singleton.disconnect()
        _client_singleton = None


# --- Test ---

if __name__ == "__main__":
    print("Testando Telegram Client...")
    me = sync_get_me()
    print(f"Conectado como: {me.first_name} (@{me.username}) | ID: {me.id} | Phone: {me.phone}")

    print("\nUltimos 5 chats:")
    dialogs = sync_get_dialogs(5)
    for d in dialogs:
        print(f"  [{d['type']}] {d['name']} (ID: {d['id']}) | Unread: {d['unread']}")
