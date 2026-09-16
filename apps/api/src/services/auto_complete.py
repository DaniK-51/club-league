"""Background auto-timer: APPROVED → COMPLETED after N days (04_ARCHITECTURE)."""

from __future__ import annotations

import asyncio
import logging

from src.core.config import get_settings
from src.core.database import get_session_factory
from src.services.archive_service import complete_approved_if_stale

logger = logging.getLogger(__name__)

_scan_task: asyncio.Task[None] | None = None


async def _loop() -> None:
    settings = get_settings()
    interval = 3600
    while True:
        try:
            factory = get_session_factory()
            async with factory() as session:
                count = await complete_approved_if_stale(
                    session,
                    older_than_days=settings.approved_auto_complete_days,
                )
            if count:
                logger.info("auto-complete APPROVED→COMPLETED count=%s", count)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("auto-complete scan failed")
        await asyncio.sleep(interval)


def start_auto_complete_timer() -> None:
    global _scan_task
    if _scan_task is None or _scan_task.done():
        _scan_task = asyncio.get_running_loop().create_task(_loop())


def stop_auto_complete_timer() -> None:
    global _scan_task
    if _scan_task is not None and not _scan_task.done():
        _scan_task.cancel()
    _scan_task = None
