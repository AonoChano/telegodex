"""CodexBridge v2 — Telegram ↔ Codex CLI integration via app-server.

Exports:
    CodexDaemon: Persistent ``codex app-server`` subprocess manager.
    CodexSessionManager: Telegram chat_id → Codex threadId mapping.
    ApprovalHandler: Converts app-server approval requests to Telegram inline buttons.
    Parse helpers: Instruction prefix routing (/, !, @).
    JsonRpcTransport / JsonRpcError: JSON-RPC 2.0 stdio transport.
"""

from .approvals import ApprovalHandler
from .commands import (
    format_file_suggestions,
    format_slash_suggestions,
    list_directory,
    list_skills,
    parse_instruction_prefix,
)
from .daemon import CodexDaemon, codex_daemon
from .jsonrpc import JsonRpcError, JsonRpcTransport
from .session import CodexSessionManager

__all__ = [
    "CodexDaemon",
    "codex_daemon",
    "CodexSessionManager",
    "ApprovalHandler",
    "JsonRpcTransport",
    "JsonRpcError",
    "parse_instruction_prefix",
    "list_skills",
    "list_directory",
    "format_slash_suggestions",
    "format_file_suggestions",
]
