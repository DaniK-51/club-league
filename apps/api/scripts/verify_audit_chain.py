"""Verify audit_logs hash chain integrity.

Usage:
    uv run python -m scripts.verify_audit_chain
"""

from __future__ import annotations

import asyncio
import sys

from src.core.database import dispose_engine, get_session_factory
from src.services.audit_service import AuditService, ChainBrokenError


async def main() -> int:
    factory = get_session_factory()
    try:
        async with factory() as session:
            service = AuditService(session)
            try:
                await service.verify_chain()
            except ChainBrokenError as exc:
                print(f"CHAIN BROKEN: {exc}")
                return 1
            print("CHAIN OK")
            return 0
    finally:
        await dispose_engine()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
