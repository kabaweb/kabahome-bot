"""Server tools: SSH execution, Docker commands, Portainer API."""

import os
import subprocess
import httpx
from dotenv import load_dotenv

load_dotenv()

SSH_HOST = os.getenv("SSH_HOST", "192.168.1.99")
SSH_USER = os.getenv("SSH_USER", "root")
SSH_PASSWORD = os.getenv("SSH_PASSWORD", "uEd6433159357@@")
PORTAINER_URL = os.getenv("PORTAINER_URL", "http://192.168.1.99:9000")
PORTAINER_USER = os.getenv("PORTAINER_USER", "admin")
PORTAINER_PASSWORD = os.getenv("PORTAINER_PASSWORD", "pEd6433159357@@")


def _ssh_exec_raw(command: str, timeout: int = 30) -> str:
    """Execute a command on kabahome via SSH using paramiko."""
    try:
        import paramiko
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(SSH_HOST, username=SSH_USER, password=SSH_PASSWORD, timeout=10)
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        client.close()
        result = out
        if err:
            result += "\n[STDERR]\n" + err
        return result.strip() or "(sem output)"
    except Exception as e:
        return f"Erro SSH: {str(e)}"


def ssh_exec(command: str, timeout: int = 30) -> str:
    return _ssh_exec_raw(command, timeout)


def docker_ps() -> str:
    return _ssh_exec_raw("docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'")


def docker_service_ls() -> str:
    return _ssh_exec_raw("docker service ls --format 'table {{.Name}}\t{{.Replicas}}\t{{.Image}}'")


def docker_logs(service: str, lines: int = 50) -> str:
    return _ssh_exec_raw(f"docker service logs {service} --tail {lines} 2>&1")


def disk_usage() -> str:
    return _ssh_exec_raw("df -h / /mnt/storage 2>/dev/null")


def ram_usage() -> str:
    return _ssh_exec_raw("free -h")


def portainer_api(method: str, path: str, body: str = "") -> str:
    try:
        auth_resp = httpx.post(
            f"{PORTAINER_URL}/api/auth",
            json={"username": PORTAINER_USER, "password": PORTAINER_PASSWORD},
            timeout=10,
        )
        jwt = auth_resp.json()["jwt"]
        url = f"{PORTAINER_URL}{path}"
        headers = {"Authorization": f"Bearer {jwt}"}
        if method.upper() == "GET":
            resp = httpx.get(url, headers=headers, timeout=15)
        elif method.upper() == "POST":
            import json
            resp = httpx.post(url, headers=headers, json=json.loads(body) if body else {}, timeout=15)
        elif method.upper() == "PUT":
            import json
            resp = httpx.put(url, headers=headers, json=json.loads(body) if body else {}, timeout=15)
        elif method.upper() == "DELETE":
            resp = httpx.delete(url, headers=headers, timeout=15)
        else:
            return "Metodo invalido"
        import json as j
        return j.dumps(resp.json(), indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Erro Portainer API: {str(e)}"


def docker_restart_service(service: str) -> str:
    return _ssh_exec_raw(f"docker service update --force {service}")


def docker_system_prune() -> str:
    return _ssh_exec_raw("docker system prune -f 2>&1")


def uptime() -> str:
    return _ssh_exec_raw("uptime")


AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ssh_exec",
            "description": "Execute a shell command on kabahome server (192.168.1.99) via SSH.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute"},
                    "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)"},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docker_ps",
            "description": "List all running Docker containers on kabahome.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docker_service_ls",
            "description": "List all Docker Swarm services and their replica status.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docker_logs",
            "description": "Get recent logs from a Docker Swarm service.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {"type": "string", "description": "Service name"},
                    "lines": {"type": "integer", "description": "Number of log lines (default 50)"},
                },
                "required": ["service"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "disk_usage",
            "description": "Show disk usage on kabahome.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ram_usage",
            "description": "Show RAM and swap usage on kabahome.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "portainer_api",
            "description": "Call Portainer API to manage stacks, containers, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {"type": "string", "description": "HTTP method: GET, POST, PUT, DELETE"},
                    "path": {"type": "string", "description": "API path (e.g., /api/stacks)"},
                    "body": {"type": "string", "description": "JSON body for POST/PUT requests"},
                },
                "required": ["method", "path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "docker_restart_service",
            "description": "Force restart a Docker Swarm service.",
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {"type": "string", "description": "Service name to restart"},
                },
                "required": ["service"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "uptime",
            "description": "Show server uptime and load average.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]

TOOL_EXECUTORS = {
    "ssh_exec": ssh_exec,
    "docker_ps": docker_ps,
    "docker_service_ls": docker_service_ls,
    "docker_logs": docker_logs,
    "disk_usage": disk_usage,
    "ram_usage": ram_usage,
    "portainer_api": portainer_api,
    "docker_restart_service": docker_restart_service,
    "uptime": uptime,
}


# --- Database tools (shared memory) ---
from db_tools import (
    get_session_summary,
    add_action,
    get_pending,
    update_context,
    mark_done,
)

AVAILABLE_TOOLS.extend([
    {
        "type": "function",
        "function": {
            "name": "get_session_summary",
            "description": "Get complete summary of the current session: pending items, recent actions, and current server state.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_action",
            "description": "Register a new action in the shared memory database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "description": "Type: install, config, fix, diagnostic, pending"},
                    "category": {"type": "string", "description": "Category: docker, cloudflare, media, security, bot, database"},
                    "description": {"type": "string", "description": "Description of the action"},
                    "status": {"type": "string", "description": "Status: done, pending, failed, in_progress"},
                    "details": {"type": "string", "description": "Additional details (optional)"},
                },
                "required": ["action_type", "category", "description", "status"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pending",
            "description": "List all pending items from the shared memory database.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_context",
            "description": "Update or set a key-value context about the server state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Context key (e.g., disco_sistema, ram, ultima_acao)"},
                    "value": {"type": "string", "description": "Context value"},
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_done",
            "description": "Mark a pending action as completed by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action_id": {"type": "integer", "description": "The action ID to mark as done"},
                },
                "required": ["action_id"],
            },
        },
    },
])

TOOL_EXECUTORS.update({
    "get_session_summary": get_session_summary,
    "add_action": add_action,
    "get_pending": get_pending,
    "update_context": update_context,
    "mark_done": mark_done,
})
