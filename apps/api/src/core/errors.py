from fastapi import HTTPException

from src.core.i18n import t
from src.schemas.common import ErrorCode


def api_error(
    status: int,
    code: ErrorCode,
    message: str,
    *,
    message_key: str | None = None,
    **kwargs: object,
) -> HTTPException:
    """HTTPException with contract body `{ error: { code, message } }`.

    If `message_key` is set, message is translated for the current request language.
    """
    text = t(message_key, **kwargs) if message_key else message
    return HTTPException(status_code=status, detail={"error": {"code": code, "message": text}})
