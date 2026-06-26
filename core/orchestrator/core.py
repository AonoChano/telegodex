"""Orchestrator core — central message router and execution engine."""

from __future__ import annotations

import asyncio
import contextlib
import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from ai import AIRouter
from core.bus import Envelope, MessageBus, from_background_result
from core.orchestrator.commands import CommandRegistry
from core.orchestrator.directives import DirectiveParser
from core.orchestrator.hooks import MessageHookRegistry
from core.orchestrator.providers import ProviderManager
from core.session import SessionKey, session_manager
from extensions.codex.approvals import ApprovalHandler
from extensions.codex.commands import (
    format_file_suggestions,
    format_slash_suggestions,
    list_directory,
    list_skills,
    parse_instruction_prefix,
)
from extensions.codex.daemon import CodexDaemon
from extensions.codex.daemon import codex_daemon as _global_codex_daemon
from extensions.codex.session import CodexSessionManager
from providers.shell import ShellProvider

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _maybe_await(fn: Callable[..., Any] | None, *args: Any) -> None:
    """Call a sync or async callback, suppressing exceptions."""
    if fn is None:
        return
    try:
        result = fn(*args)
        if inspect.isawaitable(result):
            await result
    except Exception:
        pass


def _is_codex_internal_delta(delta: str) -> bool:
    """Return True if *delta* is a Codex internal status line (not user-facing)."""
    stripped = delta.strip()
    # Filter short status lines that contain internal markers.
    if len(stripped) < 120:
        lower = stripped.lower()
        if "thinking...received." in lower:
            return True
        if "i'm in " in lower and "and ready." in lower:
            return True
        if stripped.startswith("Thinking...") and "Received." in stripped:
            return True
    return False


def _extract_codex_error_notification(params: dict[str, Any]) -> tuple[str, str | None, bool, str]:
    """Return ``(message, additional_details, will_retry, codex_error_info)``.

    App-server v2 emits ``error`` notifications as
    ``{error: {message, additionalDetails}, willRetry}``, while older code in
    this project expected a flat ``{message}`` payload. Keep both shapes here so
    retry status never collapses to ``Unknown error``.
    """
    error = params.get("error")
    message = params.get("message", "Unknown error")
    additional_details = None
    codex_error_info = ""

    if isinstance(error, dict):
        message = error.get("message", message)
        additional_details = error.get("additionalDetails") or error.get("additional_details")
        codex_error_info = error.get("codexErrorInfo") or error.get("codex_error_info") or ""

    message_text = str(message or "Unknown error").strip() or "Unknown error"
    detail_text = str(additional_details).strip() if additional_details else None
    return message_text, detail_text, bool(params.get("willRetry", False)), str(codex_error_info or "")



def _markdown_code_fence(text: str, language: str = "text") -> str:
    """Return a Markdown fence that can contain *text* safely."""
    fence = "```"
    while fence in text:
        fence += "`"
    return f"{fence}{language}\n{text}\n{fence}"


_TELEGRAM_RICH_SOFT_LIMIT = 30_000
_TOOL_OUTPUT_PREVIEW_CHARS = 2_400
_TOOL_OUTPUT_COMPACT_CHARS = 600
_TOOL_COMMAND_PREVIEW_CHARS = 1_600
_TOOL_COMMAND_COMPACT_CHARS = 600


def _truncate_middle_text(text: str, limit: int, subject: str) -> str:
    """Keep the start and end of long runtime text within a character budget."""
    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit < 120:
        return text[:limit]

    marker = f"\n\n[... {subject} truncated for Telegram ...]\n\n"
    available = max(0, limit - len(marker))
    head_len = available // 2
    tail_len = available - head_len
    omitted = max(0, len(text) - head_len - tail_len)
    marker = f"\n\n[... {subject} truncated for Telegram: {omitted} chars omitted ...]\n\n"
    available = max(0, limit - len(marker))
    head_len = available // 2
    tail_len = available - head_len
    head = text[:head_len].rstrip()
    tail = text[-tail_len:].lstrip() if tail_len > 0 else ""
    result = f"{head}{marker}{tail}"
    return result[:limit]


@dataclass
class _CodexTextSegment:
    text: str = ""


@dataclass
class _CodexToolCommand:
    item_id: str
    command: str = ""
    output: str = ""
    exit_code: int | str | None = None


@dataclass
class _CodexToolSegment:
    commands: list[_CodexToolCommand] = field(default_factory=list)


class _CodexTurnRenderer:
    """Render Codex notifications into Telegram Rich Markdown.

    Assistant prose remains normal body text. Consecutive tool events are kept
    in a default-collapsed <details> block so long command logs do not drown
    out the answer while still staying available to inspect.
    """

    def __init__(self) -> None:
        self._segments: list[_CodexTextSegment | _CodexToolSegment] = []
        self._commands_by_id: dict[str, _CodexToolCommand] = {}
        self._active_command_id: str | None = None
        self._anon_command_count = 0

    def add_text(self, text: str) -> None:
        if not text:
            return
        if self._segments and isinstance(self._segments[-1], _CodexTextSegment):
            self._segments[-1].text += text
        else:
            self._segments.append(_CodexTextSegment(text=text))

    def add_error(self, text: str) -> None:
        if text.strip():
            self.add_text(text)

    def start_command(self, item: dict[str, Any]) -> None:
        item_id = str(item.get("id") or self._next_anon_command_id())
        command = str(item.get("command") or item.get("formattedCommand") or "")
        cmd = self._commands_by_id.get(item_id)
        if cmd is None:
            cmd = _CodexToolCommand(item_id=item_id, command=command)
            self._commands_by_id[item_id] = cmd
            self._current_tool_segment().commands.append(cmd)
        elif command and not cmd.command:
            cmd.command = command
        self._active_command_id = item_id

    def append_command_output(self, delta: str, item_id: str | None = None) -> None:
        if not delta:
            return
        cmd = self._command_for_update(item_id)
        cmd.output += delta

    def complete_command(self, item: dict[str, Any]) -> None:
        item_id = str(item.get("id") or self._active_command_id or self._next_anon_command_id())
        cmd = self._commands_by_id.get(item_id)
        if cmd is None:
            cmd = _CodexToolCommand(item_id=item_id)
            self._commands_by_id[item_id] = cmd
            self._current_tool_segment().commands.append(cmd)
        if not cmd.command:
            cmd.command = str(item.get("command") or item.get("formattedCommand") or "")
        if "exitCode" in item:
            cmd.exit_code = item.get("exitCode")
        aggregated = item.get("aggregatedOutput") or item.get("output") or ""
        if aggregated and aggregated not in cmd.output:
            if cmd.output and not cmd.output.endswith("\n"):
                cmd.output += "\n"
            cmd.output += str(aggregated)
        self._active_command_id = None

    def render(self) -> str:
        for options in (
            {
                "output_char_limit": _TOOL_OUTPUT_PREVIEW_CHARS,
                "command_char_limit": _TOOL_COMMAND_PREVIEW_CHARS,
                "summary_only": False,
            },
            {
                "output_char_limit": _TOOL_OUTPUT_COMPACT_CHARS,
                "command_char_limit": _TOOL_COMMAND_COMPACT_CHARS,
                "summary_only": False,
            },
            {
                "output_char_limit": 0,
                "command_char_limit": _TOOL_COMMAND_COMPACT_CHARS,
                "summary_only": False,
            },
            {
                "output_char_limit": 0,
                "command_char_limit": 0,
                "summary_only": True,
            },
        ):
            rendered = self._render_segments(**options)
            if len(rendered) <= _TELEGRAM_RICH_SOFT_LIMIT:
                return rendered
        return _truncate_middle_text(rendered, _TELEGRAM_RICH_SOFT_LIMIT, "message")

    def _render_segments(
        self,
        *,
        output_char_limit: int,
        command_char_limit: int,
        summary_only: bool,
    ) -> str:
        rendered: list[str] = []
        for segment in self._segments:
            if isinstance(segment, _CodexTextSegment):
                text = segment.text.strip("\n")
                if text:
                    rendered.append(text)
            else:
                details = self._render_tool_segment(
                    segment,
                    output_char_limit=output_char_limit,
                    command_char_limit=command_char_limit,
                    summary_only=summary_only,
                )
                if details:
                    rendered.append(details)
        return "\n\n".join(rendered).strip()

    def _current_tool_segment(self) -> _CodexToolSegment:
        if self._segments and isinstance(self._segments[-1], _CodexToolSegment):
            return self._segments[-1]
        segment = _CodexToolSegment()
        self._segments.append(segment)
        return segment

    def _command_for_update(self, item_id: str | None = None) -> _CodexToolCommand:
        resolved = str(item_id or self._active_command_id or "")
        if resolved and resolved in self._commands_by_id:
            return self._commands_by_id[resolved]
        if not resolved:
            resolved = self._next_anon_command_id()
        cmd = _CodexToolCommand(item_id=resolved)
        self._commands_by_id[resolved] = cmd
        self._current_tool_segment().commands.append(cmd)
        self._active_command_id = resolved
        return cmd

    def _next_anon_command_id(self) -> str:
        self._anon_command_count += 1
        return f"command-{self._anon_command_count}"

    @staticmethod
    def _render_tool_segment(
        segment: _CodexToolSegment,
        *,
        output_char_limit: int,
        command_char_limit: int,
        summary_only: bool,
    ) -> str:
        if summary_only:
            command_count = len(segment.commands)
            output_chars = sum(len(command.output) for command in segment.commands)
            if command_count <= 0:
                return ""
            body = (
                f"_{command_count} command(s); detailed tool activity omitted "
                "to keep this Telegram message within size limits._"
            )
            if output_chars:
                body += f"\n\n_{output_chars} chars of tool output were not echoed._"
            return f"<details><summary>Tool activity</summary>\n\n{body}\n\n</details>"

        blocks: list[str] = []
        for command in segment.commands:
            command_blocks: list[str] = []
            if command.command:
                command_blocks.append("**Exec**")
                command_text = _truncate_middle_text(
                    command.command,
                    command_char_limit,
                    "command",
                )
                command_blocks.append(_markdown_code_fence(command_text, "sh"))
            else:
                command_blocks.append("**Command output**")

            if command.output.strip():
                if output_char_limit > 0:
                    output = _truncate_middle_text(
                        command.output.rstrip(),
                        output_char_limit,
                        "tool output",
                    )
                    command_blocks.append(_markdown_code_fence(output, "text"))
                else:
                    command_blocks.append(
                        f"_Tool output omitted for Telegram ({len(command.output)} chars)._"
                    )

            if command.exit_code is not None:
                try:
                    exit_code = int(command.exit_code)
                except (TypeError, ValueError):
                    exit_code = command.exit_code
                if exit_code == 0:
                    command_blocks.append("**Success**")
                    if not command.output.strip():
                        command_blocks.append("_Command completed with no output._")
                else:
                    command_blocks.append(f"**Failed** (exit code: {exit_code})")

            blocks.append("\n\n".join(command_blocks))

        if not blocks:
            return ""
        body = "\n\n---\n\n".join(blocks)
        return f"<details><summary>Tool activity</summary>\n\n{body}\n\n</details>"


# ---------------------------------------------------------------------------
# Callbacks
# ---------------------------------------------------------------------------


@dataclass
class StreamingCallbacks:
    """Callbacks for streaming output during a turn.

    All callbacks are optional.  The ``*_delta`` callbacks receive
    ``(delta, accumulated)`` so the caller can decide when to flush.
    """

    on_text_delta: Callable[[str, str], Awaitable[None] | None] | None = None
    """(delta, accumulated_text)"""

    on_reasoning_delta: Callable[[str, str], Awaitable[None] | None] | None = None
    """(delta, accumulated_reasoning)"""

    on_command_output_delta: Callable[[str, str], Awaitable[None] | None] | None = None
    """(delta, accumulated_output)"""

    on_render_update: Callable[[str], Awaitable[None] | None] | None = None
    """(rendered_text)"""

    on_item_started: Callable[[str, dict[str, Any]], Awaitable[None] | None] = None
    """(item_type, item_dict)"""

    on_item_completed: Callable[[str, dict[str, Any]], Awaitable[None] | None] = None
    """(item_type, item_dict)"""

    on_turn_completed: Callable[[dict[str, Any], str], Awaitable[None] | None] | None = None
    """(turn_dict, final_text)"""

    on_codex_error: Callable[[str, str | None, bool], Awaitable[None] | None] | None = None
    """(error_message, additional_details, will_retry)"""

    on_error: Callable[[str], Awaitable[None] | None] | None = None
    """(error_message)"""

    on_usage: Callable[[dict[str, Any]], Awaitable[None] | None] | None = None
    """(usage_dict)"""


# ---------------------------------------------------------------------------
# Route result
# ---------------------------------------------------------------------------


@dataclass
class _RoutedAction:
    action: str
    payload: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

_NOTIFICATION_QUEUES: dict[SessionKey, asyncio.Queue[tuple[str, dict[str, Any]]]] = {}


class Orchestrator:
    """Central message orchestrator.

    Routes incoming messages through::

        CommandRegistry → DirectiveParser → NamedSession → Normal Flow

    Integrates with the existing Codex Bridge (JSON-RPC over stdio) and
    Shell Provider.
    """

    def __init__(
        self,
        ai_router: AIRouter,
        codex_daemon: CodexDaemon | None = None,
    ) -> None:
        self.commands = CommandRegistry()
        self.directives = DirectiveParser()
        self.providers = ProviderManager(ai_router)
        self.hooks = MessageHookRegistry()

        self._codex_daemon = codex_daemon or _global_codex_daemon
        self._session_manager: CodexSessionManager | None = None
        if self._codex_daemon is not None:
            self._session_manager = CodexSessionManager(self._codex_daemon)
        self._approval_handler = ApprovalHandler()
        self._approval_ui_sender: Callable[[str, dict[str, Any]], Awaitable[None] | None] | None = None
        self._shell_provider = ShellProvider()
        self._pending_shell_commands: dict[str, dict[str, Any]] = {}

        # MessageBus — shared lock pool with Telegram handlers
        self._message_bus = MessageBus(
            lock_pool=session_manager.lock_pool,
            session_injector=self,
        )

        self._register_default_commands()
        self._register_transport_handlers()

    # ------------------------------------------------------------------
    # Transport / Notification bridge
    # ------------------------------------------------------------------

    def ensure_transport_handlers(self) -> None:
        """Re-register transport handlers if the transport is now available."""
        self._register_transport_handlers()

    def set_approval_ui_sender(
        self,
        sender: Callable[[str, dict[str, Any]], Awaitable[None] | None],
    ) -> None:
        """Set a callback that sends approval UI to the user.

        The callback receives ``(method, params)`` for approval requests.
        """
        self._approval_ui_sender = sender

    def _register_transport_handlers(self) -> None:
        if self._codex_daemon is None:
            return
        transport = self._codex_daemon.transport
        if transport is not None:
            transport._on_notification = self._on_codex_notification
            transport._on_server_request = self._on_codex_server_request

    async def _on_codex_notification(self, method: str, params: dict[str, Any]) -> None:
        thread_id = params.get("threadId", "")
        if self._session_manager is None:
            return
        session_key = self._session_manager.reverse_lookup(thread_id)
        if session_key is not None:
            queue = _NOTIFICATION_QUEUES.get(session_key)
            if queue is not None:
                with contextlib.suppress(asyncio.QueueFull):
                    queue.put_nowait((method, params))
            return
        # Fallback fan-out for unmapped threads (startup handshake, etc.)
        for queue in list(_NOTIFICATION_QUEUES.values()):
            with contextlib.suppress(asyncio.QueueFull):
                queue.put_nowait((method, params))

    async def _on_codex_server_request(self, method: str, params: dict[str, Any]) -> dict[str, Any] | None:
        if method in (
            "item/commandExecution/requestApproval",
            "item/fileChange/requestApproval",
        ):

            async def send_approval_ui(
                _approval_id: str | int,
                approval_params: dict[str, Any],
            ) -> None:
                if self._approval_ui_sender is None:
                    return
                try:
                    result = self._approval_ui_sender(method, approval_params)
                    if inspect.isawaitable(result):
                        await result
                except Exception:
                    # The approval UI is best-effort: even if delivery fails, we
                    # still need to await the handler so the turn can auto-deny.
                    # But silently swallowing makes "button never appeared"
                    # impossible to diagnose — log it.
                    logger.exception(
                        f"approval UI sender failed for {method}; "
                        f"turn will auto-deny after timeout"
                    )

            return await self._approval_handler.handle_server_request(
                method,
                params,
                send_approval_ui,
            )

        return await self._approval_handler.handle_server_request(method, params)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def session_manager(self) -> CodexSessionManager | None:
        return self._session_manager

    @property
    def approval_handler(self) -> ApprovalHandler:
        return self._approval_handler

    @property
    def shell_provider(self) -> ShellProvider:
        return self._shell_provider

    @property
    def pending_shell_commands(self) -> dict[str, dict[str, Any]]:
        return self._pending_shell_commands

    @property
    def message_bus(self) -> MessageBus:
        """Return the shared MessageBus instance."""
        return self._message_bus

    # ------------------------------------------------------------------
    # SessionInjector protocol
    # ------------------------------------------------------------------

    async def can_inject(self, chat_id: int, topic_id: int | None = None) -> bool:
        """Return whether an active Codex turn exists for injection."""
        key = SessionKey(transport="telegram", chat_id=chat_id, topic_id=topic_id)
        if self._session_manager is not None and self._session_manager.is_turn_active(key):
            return True
        return key in _NOTIFICATION_QUEUES

    async def inject(self, envelope: Envelope) -> bool:
        """Inject *envelope* result into the active turn's output stream."""
        from core.session import SessionKey

        key = SessionKey(
            transport="telegram",
            chat_id=envelope.chat_id,
            topic_id=envelope.topic_id,
        )
        queue = _NOTIFICATION_QUEUES.get(key)
        if queue is None:
            return False

        prefix = "\n\n_📎 Background update:_\n" if not envelope.is_error else "\n\n_⚠️ Background error:_\n"
        text = prefix + envelope.result_text
        try:
            queue.put_nowait(("item/agentMessage/delta", {"delta": text}))
            return True
        except asyncio.QueueFull:
            return False

    # ------------------------------------------------------------------
    # MessageBus helpers
    # ------------------------------------------------------------------

    async def submit_background_result(
        self,
        chat_id: int,
        result_text: str,
        *,
        topic_id: int | None = None,
        is_error: bool = False,
        needs_injection: bool = True,
    ) -> Envelope:
        """Convenience wrapper to submit a background result envelope."""
        envelope = from_background_result(
            chat_id=chat_id,
            topic_id=topic_id,
            result_text=result_text,
            is_error=is_error,
            needs_injection=needs_injection,
        )
        return await self._message_bus.submit(envelope)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def handle_message(
        self,
        key: SessionKey,
        text: str,
        *,
        db: AsyncSession,
        user_id: int,
    ) -> str:
        """Handle a non-streaming message and return the final text."""
        # Ensure session is loaded into memory before routing.
        if self._session_manager is not None and key.topic_id is not None:
            session = self._session_manager.get_session(key)
            if session is None:
                try:
                    await self._session_manager.get_or_create_session(db, key, user_id, cwd=None)
                    logger.info(f"handle_message: pre-loaded session for {key}")
                except Exception as exc:
                    logger.debug(f"handle_message: failed to pre-load session: {exc}")

        routed = self._route_message(key, text)
        return await self._execute_routed(key, routed, db, user_id)

    async def handle_message_streaming(
        self,
        key: SessionKey,
        text: str,
        *,
        db: AsyncSession,
        user_id: int,
        callbacks: StreamingCallbacks,
    ) -> str:
        """Handle a streaming message and return the final text.

        Intermediate state is delivered via *callbacks*.
        """
        # Ensure session is loaded into memory before routing.
        # This is important after bot restarts when sessions exist in DB but not in memory.
        if self._session_manager is not None and key.topic_id is not None:
            # Only pre-load for topic-based keys (potential Codex sessions)
            logger.info(f"handle_message_streaming: checking session for {key}")
            session = self._session_manager.get_session(key)
            logger.info(f"handle_message_streaming: get_session returned {session}")
            if session is None:
                # Try to load from database - AWAIT completion before routing
                logger.info("handle_message_streaming: calling get_or_create_session")
                try:
                    session = await self._session_manager.get_or_create_session(db, key, user_id, cwd=None)
                    logger.info(f"handle_message_streaming: pre-loaded session {session}")
                except Exception as exc:
                    logger.warning(f"handle_message_streaming: failed to pre-load session: {exc}")
            else:
                logger.info("handle_message_streaming: session already in memory")

        routed = self._route_message(key, text)
        return await self._execute_routed_streaming(key, routed, db, user_id, callbacks)

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    def _route_message(self, key: SessionKey, text: str) -> _RoutedAction:
        """Route: CommandRegistry → DirectiveParser → NamedSession → Normal Flow."""
        logger.debug(f"_route_message: key={key}, text='{text[:50]}...'")

        # 1. CommandRegistry
        cmd_name, rest, handler = self.commands.match(text)
        if cmd_name is not None and handler is not None:
            logger.debug(f"_route_message: matched command '{cmd_name}'")
            if cmd_name == "codex":
                return self._route_codex_command(key, rest)
            if cmd_name == "shell":
                return _RoutedAction(action="shell_command", payload={"command": rest})
            return _RoutedAction(
                action="command_response",
                payload={"command": cmd_name, "rest": rest},
            )

        # 2. DirectiveParser
        directive = self.directives.parse(text)
        if directive is not None:
            logger.debug(f"_route_message: matched directive '{directive.name}'")
            if directive.name == "codex":
                return _RoutedAction(
                    action="codex_prompt",
                    payload={"prompt": directive.rest or directive.target or ""},
                )
            if directive.name == "shell":
                return _RoutedAction(
                    action="shell_command",
                    payload={"command": directive.rest or directive.target or ""},
                )
            if directive.name == "ai":
                return _RoutedAction(action="ai_chat", payload={"prompt": directive.rest})

        # 3. NamedSession → Normal Flow
        # Check if this SessionKey belongs to an active Codex session.
        if self._session_manager is not None:
            session = self._session_manager.get_session(key)
            logger.debug(f"_route_message: session_manager.get_session({key}) = {session}")
            if session is not None:
                # Active Codex session exists for this key.
                logger.info("_route_message: routing to codex_prompt (active session found)")
                return _RoutedAction(action="codex_prompt", payload={"prompt": text})

        # Default to normal AI flow.
        logger.info("_route_message: routing to ai_chat (no session found)")
        return _RoutedAction(action="ai_chat", payload={"prompt": text})

    def _route_codex_command(self, key: SessionKey, rest: str) -> _RoutedAction:
        """Route ``/codex`` sub-commands."""
        stripped = rest.strip().lower()

        if stripped == "new":
            return _RoutedAction(action="codex_new", payload={})
        if stripped == "status":
            return _RoutedAction(action="codex_status", payload={})
        if stripped.startswith("cd "):
            return _RoutedAction(action="codex_cd", payload={"path": rest[3:].strip()})
        if stripped == "pwd":
            return _RoutedAction(action="codex_pwd", payload={})
        if stripped == "threads":
            return _RoutedAction(action="codex_threads", payload={})
        if stripped == "archive":
            return _RoutedAction(action="codex_archive", payload={})
        if stripped.startswith("switch "):
            return _RoutedAction(
                action="codex_switch",
                payload={"id": rest[7:].strip().lstrip("#")},
            )

        # Instruction prefixes (/, !, @)
        prefix, instr_rest = parse_instruction_prefix(rest)
        if prefix == "slash":
            return _RoutedAction(action="codex_slash", payload={})
        if prefix == "shell":
            return _RoutedAction(action="shell_command", payload={"command": instr_rest})
        if prefix == "file":
            return _RoutedAction(
                action="codex_file",
                payload={"path": instr_rest or "."},
            )

        # Normal prompt
        return _RoutedAction(action="codex_prompt", payload={"prompt": rest})

    # ------------------------------------------------------------------
    # Execution dispatch
    # ------------------------------------------------------------------

    async def _execute_routed(
        self,
        key: SessionKey,
        routed: _RoutedAction,
        db: AsyncSession,
        user_id: int,
    ) -> str:
        action = routed.action
        payload = routed.payload

        if action == "codex_prompt":
            return await self._run_codex_prompt(key, payload.get("prompt", ""), db, user_id)
        if action == "shell_command":
            result = await self._run_shell_command(payload.get("command", ""), session_id=key.to_string())
            return self._format_shell_result(result)
        if action == "ai_chat":
            return await self._run_ai_chat(key, payload.get("prompt", ""), db, user_id)
        if action == "codex_new":
            info = await self.codex_new_session(key, db, user_id)
            return f"Started a new Codex session.\nThread: `{info['thread_id']}`\nCWD: `{info['cwd']}`"
        if action == "codex_status":
            info = await self.codex_get_status(key)
            if info is None:
                return "No active Codex session."
            lines = [
                f"**Thread:** `{info['thread_id']}`",
                f"**CWD:** `{info['cwd']}`",
                f"**Turn active:** {'yes' if info['turn_active'] else 'no'}",
            ]
            resume = info.get("resume_info")
            if resume:
                lines.append(f"_Resumed session (last active {resume.get('resumed_at', 'unknown')})_")
            return "\n".join(lines)
        if action == "codex_cd":
            info = await self.codex_set_cwd(key, db, payload.get("path", ""))
            return f"Working directory changed.\nNew thread: `{info['thread_id']}`\nCWD: `{info['cwd']}`"
        if action == "codex_pwd":
            cwd = await self.codex_get_pwd(key, db)
            return f"Working directory: `{cwd or 'default'}`"
        if action == "codex_threads":
            threads = await self.codex_list_threads(key, db)
            if not threads:
                return "No sessions found for this chat."
            lines = ["**Sessions:**", ""]
            for t in threads:
                active_marker = " (active)" if t["is_active"] else ""
                lines.append(
                    f"`#{t['id']}` `{t['codex_thread_id'][:16]}...`"
                    f"{active_marker}\n"
                    f"  CWD: `{t['cwd'] or 'default'}` | "
                    f"Updated: {t['updated_at'][:10] if t['updated_at'] else '?'}"
                )
            return "\n".join(lines)
        if action == "codex_archive":
            ok = await self.codex_archive(key, db)
            return "Session archived." if ok else "No active session to archive."
        if action == "codex_switch":
            ok = await self.codex_switch(key, db, payload.get("id", ""))
            return "Switched session." if ok else "Session not found."
        if action == "codex_slash":
            skills = await self.codex_list_skills()
            return format_slash_suggestions(skills)
        if action == "codex_file":
            entries = await self.codex_list_directory(payload.get("path", "."))
            return format_file_suggestions(entries)
        if action == "command_response":
            return f"Command `{payload.get('command')}` received."

        return "Unknown action."

    async def _execute_routed_streaming(
        self,
        key: SessionKey,
        routed: _RoutedAction,
        db: AsyncSession,
        user_id: int,
        callbacks: StreamingCallbacks,
    ) -> str:
        action = routed.action
        payload = routed.payload

        if action == "codex_prompt":
            return await self._stream_codex_prompt(key, payload.get("prompt", ""), db, user_id, callbacks)
        if action == "shell_command":
            result = await self._run_shell_command(payload.get("command", ""), session_id=key.to_string())
            text = self._format_shell_result(result)
            await _maybe_await(callbacks.on_text_delta, text, text)
            return text
        if action == "ai_chat":
            return await self._stream_ai_chat(key, payload.get("prompt", ""), db, user_id, callbacks)

        # Non-streaming actions fall back to text response
        text = await self._execute_routed(key, routed, db, user_id)
        await _maybe_await(callbacks.on_text_delta, text, text)
        return text

    # ------------------------------------------------------------------
    # Codex sub-command helpers
    # ------------------------------------------------------------------

    async def codex_new_session(self, key: SessionKey, db: AsyncSession, user_id: int) -> dict[str, Any]:
        if self._session_manager is None:
            raise RuntimeError("Codex session manager is not available")
        session = await self._session_manager.new_session(db=db, session_key=key, user_id=user_id)
        return {
            "thread_id": session.thread_id,
            "cwd": session.cwd or "default",
        }

    async def codex_get_status(self, key: SessionKey) -> dict[str, Any] | None:
        if self._session_manager is None:
            return None
        session = self._session_manager.get_session(key)
        if session is None:
            return None
        return {
            "thread_id": session.thread_id,
            "cwd": session.cwd or "default",
            "turn_active": self._session_manager.is_turn_active(key),
            "resume_info": self._session_manager.get_resume_info(key),
        }

    async def codex_set_cwd(self, key: SessionKey, db: AsyncSession, path: str) -> dict[str, Any]:
        if self._session_manager is None:
            raise RuntimeError("Codex session manager is not available")
        await self._session_manager.set_cwd(db=db, session_key=key, cwd=path)
        await self._session_manager.archive_thread(db=db, session_key=key)
        session = await self._session_manager.get_or_create_session(db=db, session_key=key, user_id=0, cwd=path)
        return {
            "thread_id": session.thread_id,
            "cwd": session.cwd or path,
        }

    async def codex_get_pwd(self, key: SessionKey, db: AsyncSession) -> str | None:
        if self._session_manager is not None:
            session = self._session_manager.get_session(key)
            if session and session.cwd:
                return session.cwd
        from sqlalchemy import select

        from storage.models import Conversation

        stmt = select(Conversation).where(
            Conversation.chat_id == key.chat_id,
            Conversation.is_active.is_(True),
        )
        result = await db.execute(stmt)
        conv = result.scalars().first()
        return conv.cwd if conv else None

    async def codex_list_threads(self, key: SessionKey, db: AsyncSession) -> list[dict[str, Any]]:
        if self._session_manager is None:
            return []
        return await self._session_manager.list_threads(db=db, session_key=key)

    async def codex_archive(self, key: SessionKey, db: AsyncSession) -> bool:
        if self._session_manager is None:
            return False
        return await self._session_manager.archive_thread(db=db, session_key=key)

    async def codex_switch(self, key: SessionKey, db: AsyncSession, conversation_id: str) -> bool:
        if self._session_manager is None:
            return False
        if not conversation_id.isdigit():
            return False
        return await self._session_manager.activate_thread(db=db, session_key=key, conversation_id=int(conversation_id))

    async def codex_list_skills(self) -> list[dict[str, Any]]:
        if self._codex_daemon is None:
            return []
        transport = self._codex_daemon.transport
        if transport is None:
            return []
        return await list_skills(transport)

    async def codex_list_directory(self, path: str) -> list[dict[str, Any]]:
        if self._codex_daemon is None:
            return []
        transport = self._codex_daemon.transport
        if transport is None:
            return []
        return await list_directory(transport, path)

    # ------------------------------------------------------------------
    # Codex prompt execution
    # ------------------------------------------------------------------

    async def _run_codex_prompt(
        self,
        key: SessionKey,
        prompt: str,
        db: AsyncSession,
        user_id: int,
    ) -> str:
        if self._session_manager is None:
            raise RuntimeError("Codex session manager is not available")
        session = await self._session_manager.get_or_create_session(db=db, session_key=key, user_id=user_id)
        if self._session_manager.is_turn_active(key):
            await self._session_manager.cancel_turn(key)

        await self._session_manager.start_turn(key, prompt)
        callbacks = StreamingCallbacks()
        return await self._consume_turn(key, session, callbacks)

    async def _stream_codex_prompt(
        self,
        key: SessionKey,
        prompt: str,
        db: AsyncSession,
        user_id: int,
        callbacks: StreamingCallbacks,
    ) -> str:
        if self._session_manager is None:
            raise RuntimeError("Codex session manager is not available")
        session = await self._session_manager.get_or_create_session(db=db, session_key=key, user_id=user_id)
        if self._session_manager.is_turn_active(key):
            await self._session_manager.cancel_turn(key)

        await self._session_manager.start_turn(key, prompt)
        return await self._consume_turn(key, session, callbacks)

    # ------------------------------------------------------------------
    # Turn consumer
    # ------------------------------------------------------------------

    async def _consume_turn(
        self,
        key: SessionKey,
        session: Any,
        callbacks: StreamingCallbacks,
    ) -> str:
        if self._session_manager is None:
            return "Codex session manager is not available."

        queue: asyncio.Queue[tuple[str, dict[str, Any]]] = asyncio.Queue()
        _NOTIFICATION_QUEUES[key] = queue

        renderer = _CodexTurnRenderer()
        reasoning_text = ""
        command_output = ""
        last_rendered = ""

        async def _emit_render_update() -> str:
            nonlocal last_rendered
            rendered = renderer.render()
            if rendered and rendered != last_rendered:
                last_rendered = rendered
                await _maybe_await(callbacks.on_render_update, rendered)
            return rendered

        try:
            while True:
                try:
                    method, params = await asyncio.wait_for(queue.get(), timeout=120.0)
                except TimeoutError:
                    renderer.add_error("\n\n_Codex turn timed out._")
                    await _emit_render_update()
                    await _maybe_await(callbacks.on_error, "Turn timed out")
                    session.turn_completed.set()
                    break

                if method == "turn/completed":
                    turn = params.get("turn", {})
                    status = turn.get("status", "")
                    usage = turn.get("usage", {})

                    if status == "failed":
                        error = turn.get("error", {})
                        error_msg, additional_details, _, codex_err = _extract_codex_error_notification({"error": error})
                        block = f"\n\n**Error:** {error_msg}" + (f" (`{codex_err}`)" if codex_err else "")
                        if additional_details and additional_details != error_msg:
                            block += f"\n\n{additional_details}"
                        renderer.add_error(block)
                        await _emit_render_update()
                        if callbacks.on_codex_error is not None:
                            await _maybe_await(callbacks.on_codex_error, error_msg, additional_details, False)
                        else:
                            await _maybe_await(callbacks.on_error, block)

                    elif status == "interrupted":
                        renderer.add_text("\n\n_Interrupted._")
                        await _emit_render_update()

                    if usage:
                        await _maybe_await(callbacks.on_usage, usage)

                    final_text = renderer.render().strip()
                    await _maybe_await(callbacks.on_turn_completed, turn, final_text)
                    session.turn_completed.set()
                    break

                elif method == "item/agentMessage/delta":
                    delta = params.get("delta", "")
                    if delta and not _is_codex_internal_delta(delta):
                        renderer.add_text(delta)
                        accumulated = await _emit_render_update()
                        await _maybe_await(callbacks.on_text_delta, delta, accumulated)

                elif method == "item/reasoning/summaryTextDelta":
                    delta = params.get("delta", "")
                    if delta:
                        reasoning_text += delta
                        await _maybe_await(
                            callbacks.on_reasoning_delta,
                            delta,
                            reasoning_text,
                        )

                elif method == "item/commandExecution/outputDelta":
                    delta = params.get("delta", "")
                    if delta:
                        item_id = params.get("itemId") or params.get("item_id") or params.get("id")
                        command_output += delta
                        renderer.append_command_output(delta, str(item_id) if item_id is not None else None)
                        await _maybe_await(
                            callbacks.on_command_output_delta,
                            delta,
                            command_output,
                        )
                        await _emit_render_update()

                elif method == "item/started":
                    item = params.get("item", {})
                    item_type = item.get("type", "")
                    item_id = item.get("id", "")
                    self._approval_handler.cache_item(item_id, item)
                    if item_type == "commandExecution":
                        renderer.start_command(item)
                        await _emit_render_update()
                    await _maybe_await(
                        callbacks.on_item_started,
                        item_type,
                        item,
                    )

                elif method == "item/completed":
                    item = params.get("item", {})
                    item_type = item.get("type", "")
                    if item_type == "commandExecution":
                        renderer.complete_command(item)
                        await _emit_render_update()

                    await _maybe_await(
                        callbacks.on_item_completed,
                        item_type,
                        item,
                    )

                elif method == "error":
                    error_msg, additional_details, will_retry, _ = _extract_codex_error_notification(params)
                    if callbacks.on_codex_error is not None:
                        await _maybe_await(callbacks.on_codex_error, error_msg, additional_details, will_retry)
                    else:
                        await _maybe_await(callbacks.on_error, error_msg)
                    if not will_retry:
                        block = f"\n\n**Error:** {error_msg}"
                        if additional_details and additional_details != error_msg:
                            block += f"\n\n{additional_details}"
                        renderer.add_error(block)
                        await _emit_render_update()

        finally:
            _NOTIFICATION_QUEUES.pop(key, None)

        final = renderer.render().strip()
        if not final:
            final = "Codex completed with no output."
        return final

    # ------------------------------------------------------------------
    # Shell
    # ------------------------------------------------------------------

    async def _run_shell_command(self, command: str, session_id: str | None = None) -> dict[str, Any]:
        return await self._shell_provider.execute(command, session_id=session_id)

    def shell_is_dangerous(self, command: str) -> bool:
        return self._shell_provider.is_dangerous(command)

    def _format_shell_result(self, result: dict[str, Any]) -> str:
        lines: list[str] = []
        if result.get("stdout"):
            lines.append(result["stdout"])
        if result.get("stderr"):
            lines.append(f"[stderr]\n{result['stderr']}")
        lines.append(f"\nExit code: {result.get('returncode', '?')}")
        return "\n".join(lines).strip()

    # ------------------------------------------------------------------
    # AI Chat (placeholder for future normal-flow expansion)
    # ------------------------------------------------------------------

    async def _run_ai_chat(
        self,
        key: SessionKey,
        prompt: str,
        db: AsyncSession,
        user_id: int,
    ) -> str:
        return f"AI response to: {prompt}"

    async def _stream_ai_chat(
        self,
        key: SessionKey,
        prompt: str,
        db: AsyncSession,
        user_id: int,
        callbacks: StreamingCallbacks,
    ) -> str:
        text = f"AI response to: {prompt}"
        await _maybe_await(callbacks.on_text_delta, text, text)
        return text

    # ------------------------------------------------------------------
    # Default registrations
    # ------------------------------------------------------------------

    def _register_default_commands(self) -> None:
        self.commands.register("codex", self._noop_cmd, description="Codex bridge commands")
        self.commands.register("shell", self._noop_cmd, description="Execute shell commands")

    async def _noop_cmd(self, **kwargs: Any) -> str:
        return ""
