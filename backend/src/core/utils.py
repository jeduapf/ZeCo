from fastapi import Request
import json
from src.core.i18n_logger import get_i18n_logger
from config import LANG

logger = get_i18n_logger(__name__)

def log_request_debug(request: Request, body_bytes):
    """
    Logs all relevant information of a FastAPI request for debugging.
    """
    try:
        # Read body safely
        try:
            body_content = json.loads(body_bytes)
        except Exception:
            body_content = body_bytes.decode("utf-8") if body_bytes else None

        # Log structured request info
        logger.debug(
            "utils.request.info",
            language=LANG,
            method=request.method,
            url=str(request.url),
            path=request.url.path,
            query_params=dict(request.query_params),
            headers=dict(request.headers),
            cookies=request.cookies,
            client=request.client.host if request.client else "unknown",
            body=body_content
        )
    except Exception as e:
        # If logging fails, log the error itself
        logger.error(
            "utils.request.logging_failed",
            language=LANG,
            error=str(e)
        )
