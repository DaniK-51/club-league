from fastapi import HTTPException

from src.schemas.common import ErrorCode


def api_error(status: int, code: ErrorCode, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error": {"code": code, "message": message}})
