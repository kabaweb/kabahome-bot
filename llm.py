"""OmniRoute LLM client - OpenAI-compatible API."""

import os
import json
import httpx
from dotenv import load_dotenv
from prompt import SYSTEM_PROMPT, DB_CONTEXT_INSTRUCTIONS
from tools import AVAILABLE_TOOLS, TOOL_EXECUTORS

load_dotenv()

OMNIROUTE_URL = os.getenv("OMNIROUTE_URL", "http://omniroute:20128/v1")
OMNIROUTE_MODEL = os.getenv("OMNIROUTE_MODEL", "high-availability")
OMNIROUTE_API_KEY = os.getenv("OMNIROUTE_API_KEY", "")

conversations: dict[int, list[dict]] = {}
MAX_HISTORY = 20


def get_client() -> httpx.Client:
    headers = {"Content-Type": "application/json"}
    if OMNIROUTE_API_KEY:
        headers["Authorization"] = f"Bearer {OMNIROUTE_API_KEY}"
    return httpx.Client(base_url=OMNIROUTE_URL, headers=headers, timeout=120.0)


def chat(chat_id: int, user_message: str) -> str:
    if chat_id not in conversations:
        conversations[chat_id] = [{"role": "system", "content": SYSTEM_PROMPT + DB_CONTEXT_INSTRUCTIONS}]
        if len(conversations) > 100:
            old_keys = sorted(conversations.keys())[:-50]
            for k in old_keys:
                del conversations[k]

    history = conversations[chat_id]
    history.append({"role": "user", "content": user_message})

    if len(history) > MAX_HISTORY + 1:
        history = [history[0]] + history[-(MAX_HISTORY - 1):]
        conversations[chat_id] = history

    try:
        client = get_client()
        return _chat_loop(client, chat_id, history)
    except Exception as e:
        return f"Erro ao conectar com OmniRoute: {str(e)}"


def _chat_loop(client: httpx.Client, chat_id: int, messages: list[dict], depth: int = 0) -> str:
    if depth > 5:
        return "Loop de ferramentas muito longo. Tente uma pergunta mais direta."

    try:
        resp = client.post(
            "/chat/completions",
            json={
                "model": OMNIROUTE_MODEL,
                "messages": messages,
                "tools": AVAILABLE_TOOLS,
                "tool_choice": "auto",
                "max_tokens": 2048,
                "temperature": 0.3,
            },
        )
        resp.raise_for_status()
        data = resp.json()
    except httpx.HTTPError as e:
        return f"Erro OmniRoute HTTP: {str(e)}"
    except Exception as e:
        return f"Erro OmniRoute: {str(e)}"

    choice = data["choices"][0]
    msg = choice["message"]

    if msg.get("tool_calls"):
        messages.append(msg)
        tool_results = []

        for tool_call in msg["tool_calls"]:
            func_name = tool_call["function"]["name"]
            func_args = json.loads(tool_call["function"]["arguments"])

            executor = TOOL_EXECUTORS.get(func_name)
            if executor:
                try:
                    if func_args:
                        result = executor(**func_args)
                    else:
                        result = executor()
                except Exception as e:
                    result = f"Erro ao executar {func_name}: {str(e)}"
            else:
                result = f"Ferramenta desconhecida: {func_name}"

            tool_results.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": str(result)[:4000],
            })

        messages.extend(tool_results)
        conversations[chat_id] = messages
        return _chat_loop(client, chat_id, messages, depth + 1)

    content = msg.get("content", "") or "(sem resposta)"
    messages.append({"role": "assistant", "content": content})
    conversations[chat_id] = messages
    return content


def clear_history(chat_id: int):
    if chat_id in conversations:
        del conversations[chat_id]
    return "Historico limpo."
