"""Script para autenticar uma NOVA sessao Telethon para o assistente."""

import asyncio
from telethon import TelegramClient

API_ID = 22377334
API_HASH = "5bba1cc718c39fc07fdd4fe20c7c4db0"
PHONE = "+5581981829525"
SESSION_FILE = "/mnt/storage/docker/kabahome-bot/session/assistente_kabahome.session"

async def main():
    client = TelegramClient(SESSION_FILE, API_ID, API_HASH)
    await client.connect()
    
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"Ja autenticado: {me.first_name} | @{me.username} | ID: {me.id}")
        await client.disconnect()
        return
    
    print("=" * 50)
    print("LOGIN TELEGRAM - ASSISTENTE KABAHOME")
    print("=" * 50)
    print(f"Numero: {PHONE}")
    print()
    
    # Enviar codigo
    await client.send_code_request(PHONE)
    code = input("Digite o codigo recebido no Telegram: ").strip()
    
    try:
        await client.sign_in(PHONE, code)
    except Exception as e:
        if "password" in str(e).lower() or "2fa" in str(e).lower():
            password = input("Senha 2FA: ").strip()
            await client.sign_in(password=password)
        else:
            print(f"Erro: {e}")
            return
    
    me = await client.get_me()
    print(f"\nAUTENTICADO COM SUCESSO!")
    print(f"Nome: {me.first_name}")
    print(f"Usuario: @{me.username}")
    print(f"ID: {me.id}")
    print(f"Session: {SESSION_FILE}")
    
    await client.disconnect()

asyncio.run(main())
