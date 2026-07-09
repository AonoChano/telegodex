"""Runtime hot reload for ``provider.toml``."""

from __future__ import annotations

import asyncio
from pathlib import Path

from loguru import logger

from ai.router import AIRouter, unavailable_default_provider_error
from config.provider_loader import load_provider_toml


class ProviderTomlReloader:
    """Poll ``provider.toml`` and hot-apply provider/model changes."""

    def __init__(
        self,
        path: str | Path,
        ai_router: AIRouter,
        *,
        interval_seconds: float = 2.0,
    ) -> None:
        self.path = Path(path)
        self.ai_router = ai_router
        self.interval_seconds = interval_seconds
        self._task: asyncio.Task[None] | None = None
        self._last_signature = self._signature()

    async def start(self) -> None:
        """Start the background watcher if it is not already running."""
        if self._task is not None and not self._task.done():
            return
        self._last_signature = self._signature()
        self._task = asyncio.create_task(self._run(), name="provider-toml-reloader")
        logger.info(f"Provider hot reload watcher started for {self.path}")

    async def stop(self) -> None:
        """Stop the background watcher."""
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        finally:
            self._task = None
            logger.info("Provider hot reload watcher stopped")

    async def _run(self) -> None:
        while True:
            await asyncio.sleep(self.interval_seconds)
            signature = self._signature()
            if signature == self._last_signature:
                continue
            self._last_signature = signature
            await self.reload_once()

    async def reload_once(self) -> bool:
        """Reload once. Return ``True`` when the active router was replaced."""
        try:
            provider_configs, global_config = load_provider_toml(self.path)
        except Exception as exc:
            logger.warning(f"Provider hot reload skipped: failed to load {self.path}: {exc}")
            return False

        reloaded = self.ai_router.reload(provider_configs, global_config)
        if not reloaded:
            return False

        if error := unavailable_default_provider_error(self.ai_router):
            # AIRouter.reload already validates this before swapping; keep this
            # check as a guard in case the router contract changes later.
            logger.warning(f"Provider hot reload produced invalid default provider: {error}")
            return False

        return True

    def _signature(self) -> tuple[int, int] | None:
        try:
            stat = self.path.stat()
        except OSError:
            return None
        return (stat.st_mtime_ns, stat.st_size)