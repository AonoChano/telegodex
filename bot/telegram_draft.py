"""
Draft stream with three-level graceful degradation.

- Process-level: global flag permanently disables draft API after the first
  ``METHOD_NOT_FOUND``.
- Peer-level: per-(chat_id, thread_id) cache for peers that do not support
  draft messages.
- In-flight: auto-downgrade to legacy ``send_message`` + ``edit_message_text``
  after 2 consecutive draft failures, preserving already-sent content as a
  real message.

Log throttling prevents spam after a downgrade decision has been made.
"""

from __future__ import annotations

import time
from typing import Any

from loguru import logger

from bot.utils.rich_messages import _post_bot_method, new_draft_id

# Process-level: permanently disabled after first "method not found"
_DRAFT_UNAVAILABLE: bool = False

# Peer-level: set of (chat_id, thread_id) that don't support draft
_UNSUPPORTED_PEERS: set[tuple[int | str, int | None]] = set()

# Log throttling state
_last_log_time: dict[str, float] = {}
_LOG_THROTTLE_SEC = 60


def log_throttled(key: str, message: str, level: str = "warning") -> None:
    """Emit a log message at most once per ``_LOG_THROTTLE_SEC`` for each key."""
    now = time.monotonic()
    last = _last_log_time.get(key)
    if last is not None and now - last < _LOG_THROTTLE_SEC:
        return
    _last_log_time[key] = now
    getattr(logger, level)(message)


def _is_draft_unavailable(chat_id: int | str, thread_id: int | None) -> bool:
    return _DRAFT_UNAVAILABLE or (chat_id, thread_id) in _UNSUPPORTED_PEERS


def _classify_draft_error(desc: str) -> tuple[bool, bool]:
    """Return ``(is_process_fatal, is_peer_fatal)`` from error description."""
    d = desc.lower()
    is_process = "method not found" in d
    is_peer = "not supported" in d or "unsupported" in d
    return is_process, is_peer


class DraftStream:
    """Manages streaming output via draft API with graceful degradation."""

    def __init__(
        self,
        bot_token: str,
        chat_id: int | str,
        *,
        message_thread_id: int | None = None,
        direct_messages_topic_id: int | None = None,
        business_connection_id: str | None = None,
        use_rich: bool = True,
        max_draft_calls: int = 0,
    ):
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._message_thread_id = message_thread_id
        self._direct_messages_topic_id = direct_messages_topic_id
        self._business_connection_id = business_connection_id
        self._use_rich = use_rich
        self._max_draft_calls = max_draft_calls

        self._draft_id = 0
        self._state = "DRAFT"  # DRAFT | LEGACY | GIVE_UP
        self._legacy_message_id: int | None = None
        self._consecutive_failures = 0
        self._draft_calls = 0
        self._last_text = ""
        self._finalized = False

        if not _is_draft_unavailable(chat_id, message_thread_id):
            self._draft_id = new_draft_id()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _log_downgrade(self, reason: str) -> None:
        key = f"draft_downgrade:{self._chat_id}:{self._message_thread_id}"
        log_throttled(
            key,
            f"Draft degraded to legacy for chat={self._chat_id} "
            f"thread={self._message_thread_id}: {reason}",
        )

    async def _send_draft(
        self, text: str, *, force_plain: bool = False
    ) -> tuple[bool, str]:
        """Try to send/update a draft. Returns ``(ok, description)``."""
        use_rich = self._use_rich and not force_plain

        if use_rich:
            rich_message: dict[str, Any] = {"markdown": text}
            payload: dict[str, Any] = {
                "chat_id": self._chat_id,
                "draft_id": self._draft_id,
                "rich_message": rich_message,
            }
            if self._message_thread_id is not None:
                payload["message_thread_id"] = self._message_thread_id

            ok, desc, _ = await _post_bot_method(
                self._bot_token, "sendRichMessageDraft", payload
            )
            if ok:
                return True, ""

            is_process, is_peer = _classify_draft_error(desc)
            if not is_process and not is_peer:
                # Rich failed for a non-fatal reason: try plain draft once
                plain_payload: dict[str, Any] = {
                    "chat_id": self._chat_id,
                    "draft_id": self._draft_id,
                    "text": text,
                }
                if self._message_thread_id is not None:
                    plain_payload["message_thread_id"] = self._message_thread_id
                ok2, desc2, _ = await _post_bot_method(
                    self._bot_token, "sendMessageDraft", plain_payload
                )
                if ok2:
                    return True, ""
                return False, desc2
            return False, desc

        # Plain draft only
        payload = {
            "chat_id": self._chat_id,
            "draft_id": self._draft_id,
            "text": text,
        }
        if self._message_thread_id is not None:
            payload["message_thread_id"] = self._message_thread_id
        ok, desc, _ = await _post_bot_method(
            self._bot_token, "sendMessageDraft", payload
        )
        return ok, desc

    async def _send_legacy(self, text: str) -> bool:
        """Send a real message (legacy fallback). Returns True on success."""
        # If rich is desired, try sendRichMessage first
        if self._use_rich:
            rich_payload: dict[str, Any] = {
                "chat_id": self._chat_id,
                "rich_message": {"markdown": text},
            }
            if self._message_thread_id is not None:
                rich_payload["message_thread_id"] = self._message_thread_id
            if self._direct_messages_topic_id is not None:
                rich_payload["direct_messages_topic_id"] = self._direct_messages_topic_id
            if self._business_connection_id is not None:
                rich_payload["business_connection_id"] = self._business_connection_id

            ok, desc, result = await _post_bot_method(
                self._bot_token, "sendRichMessage", rich_payload
            )
            if ok:
                if isinstance(result, dict) and result.get("message_id") is not None:
                    self._legacy_message_id = result.get("message_id")
                else:
                    # The request may have been processed but the response body
                    # was lost. Do not fall back to sendMessage, or each push can
                    # create another real message.
                    self._state = "GIVE_UP"
                    log_throttled(
                        f"draft_legacy_no_message_id:{self._chat_id}:{self._message_thread_id}",
                        "sendRichMessage legacy fallback returned no message_id; "
                        "stopping preview edits to avoid duplicate messages",
                    )
                return True
            logger.debug(f"sendRichMessage legacy fallback: {desc}")

        payload: dict[str, Any] = {
            "chat_id": self._chat_id,
            "text": text,
        }
        if self._message_thread_id is not None:
            payload["message_thread_id"] = self._message_thread_id
        if self._business_connection_id is not None:
            payload["business_connection_id"] = self._business_connection_id

        ok, desc, result = await _post_bot_method(
            self._bot_token, "sendMessage", payload
        )
        if ok:
            if isinstance(result, dict) and result.get("message_id") is not None:
                self._legacy_message_id = result.get("message_id")
            else:
                self._state = "GIVE_UP"
                log_throttled(
                    f"draft_legacy_plain_no_message_id:{self._chat_id}:{self._message_thread_id}",
                    "sendMessage legacy fallback returned no message_id; "
                    "stopping preview edits to avoid duplicate messages",
                )
            return True
        logger.warning(f"Legacy sendMessage failed: {desc}")
        return False

    async def _edit_legacy(self, text: str) -> bool:
        """Edit the previously sent legacy message."""
        if self._legacy_message_id is None:
            return await self._send_legacy(text)

        payload: dict[str, Any] = {
            "chat_id": self._chat_id,
            "message_id": self._legacy_message_id,
        }
        if self._use_rich:
            payload["rich_message"] = {"markdown": text}
        else:
            payload["text"] = text
        if self._business_connection_id is not None:
            payload["business_connection_id"] = self._business_connection_id

        ok, desc, _ = await _post_bot_method(
            self._bot_token, "editMessageText", payload
        )
        if ok:
            return True

        if "message is not modified" in desc.lower():
            return True

        if self._use_rich:
            plain_payload: dict[str, Any] = {
                "chat_id": self._chat_id,
                "message_id": self._legacy_message_id,
                "text": text,
            }
            if self._business_connection_id is not None:
                plain_payload["business_connection_id"] = self._business_connection_id
            ok2, desc2, _ = await _post_bot_method(
                self._bot_token, "editMessageText", plain_payload
            )
            if ok2 or "message is not modified" in desc2.lower():
                return True
            desc = desc2

        # Re-sending on every edit failure is what creates repeated transcript
        # messages. Stop preview updates; finalize() will make one final send if
        # it cannot edit the existing preview.
        self._state = "GIVE_UP"
        log_throttled(
            f"draft_legacy_edit_failed:{self._chat_id}:{self._message_thread_id}",
            f"Legacy preview edit failed; stopping preview edits: {desc}",
        )
        return False

    async def _send_final_message(self, text: str) -> bool:
        """Send the final persistent message without mutating preview state."""
        if self._use_rich:
            rich_payload: dict[str, Any] = {
                "chat_id": self._chat_id,
                "rich_message": {"markdown": text},
            }
            if self._message_thread_id is not None:
                rich_payload["message_thread_id"] = self._message_thread_id
            if self._direct_messages_topic_id is not None:
                rich_payload["direct_messages_topic_id"] = self._direct_messages_topic_id
            if self._business_connection_id is not None:
                rich_payload["business_connection_id"] = self._business_connection_id

            ok, desc, _ = await _post_bot_method(
                self._bot_token, "sendRichMessage", rich_payload
            )
            if ok:
                return True
            logger.debug(f"final sendRichMessage failed: {desc}")

        payload: dict[str, Any] = {
            "chat_id": self._chat_id,
            "text": text,
        }
        if self._message_thread_id is not None:
            payload["message_thread_id"] = self._message_thread_id
        if self._business_connection_id is not None:
            payload["business_connection_id"] = self._business_connection_id
        ok, desc, _ = await _post_bot_method(self._bot_token, "sendMessage", payload)
        if not ok:
            logger.warning(f"Final sendMessage failed: {desc}")
        return ok

    async def _delete_legacy_preview(self) -> None:
        """Best-effort removal of a legacy preview after final send succeeds."""
        if self._legacy_message_id is None:
            return
        payload: dict[str, Any] = {
            "chat_id": self._chat_id,
            "message_id": self._legacy_message_id,
        }
        ok, desc, _ = await _post_bot_method(self._bot_token, "deleteMessage", payload)
        if ok:
            self._legacy_message_id = None
        else:
            logger.debug(f"Legacy preview delete failed: {desc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def state(self) -> str:
        return self._state

    async def push(self, text: str, *, force_plain: bool = False) -> bool:
        """Push current text to the user.

        Returns ``True`` if the user should see the update.
        """
        if self._finalized:
            return False
        if not text or text == self._last_text:
            return True
        self._last_text = text

        if self._state == "GIVE_UP":
            return False

        # Already known unavailable at process/peer level -> legacy immediately
        if _is_draft_unavailable(self._chat_id, self._message_thread_id):
            if self._state == "DRAFT":
                self._state = "LEGACY"
                self._log_downgrade("process or peer unavailable")
            return await self._edit_legacy(text)

        if self._state == "DRAFT":
            if self._max_draft_calls > 0 and self._draft_calls >= self._max_draft_calls:
                self._state = "LEGACY"
                self._log_downgrade("max draft calls reached")
                return await self._edit_legacy(text)

            self._draft_calls += 1
            ok, desc = await self._send_draft(text, force_plain=force_plain)
            if ok:
                self._consecutive_failures = 0
                return True

            self._consecutive_failures += 1
            is_process, is_peer = _classify_draft_error(desc)

            if is_process:
                global _DRAFT_UNAVAILABLE
                _DRAFT_UNAVAILABLE = True
                log_throttled(
                    "draft_downgrade:global",
                    f"Draft API permanently disabled: {desc}",
                )
                self._state = "LEGACY"
                return await self._edit_legacy(text)

            if is_peer:
                _UNSUPPORTED_PEERS.add((self._chat_id, self._message_thread_id))
                self._state = "LEGACY"
                self._log_downgrade(f"peer unsupported: {desc}")
                return await self._edit_legacy(text)

            if self._consecutive_failures >= 2:
                self._state = "LEGACY"
                self._log_downgrade(f"2 consecutive failures: {desc}")
                return await self._edit_legacy(text)

            return False

        if self._state == "LEGACY":
            return await self._edit_legacy(text)

        return False

    async def finalize(self, text: str) -> bool:
        """Finalize the stream, ensuring the final text is persisted.

        Returns ``True`` if the user should see the final message.
        """
        if self._finalized:
            return True
        self._finalized = True
        self._last_text = text

        if self._state == "DRAFT":
            return await self._send_final_message(text)

        if self._state == "LEGACY":
            if await self._edit_legacy(text):
                return True
            ok = await self._send_final_message(text)
            if ok:
                await self._delete_legacy_preview()
            return ok

        if self._state == "GIVE_UP":
            ok = await self._send_final_message(text)
            if ok:
                await self._delete_legacy_preview()
            return ok

        # Unknown state: make exactly one final send.
        return await self._send_final_message(text)
