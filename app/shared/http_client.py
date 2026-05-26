from typing import Any, Dict, Optional

import httpx

from app.shared.logger import get_logger

logger = get_logger(__name__)


class HttpClient:
    def __init__(self, base_url: str, headers: Optional[Dict[str, str]] = None) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = headers or {}

    def post(
        self, path: str = "", payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{self._base_url}/{path.lstrip('/')}" if path else self._base_url
        logger.debug("HTTP POST %s", url)
        with httpx.Client() as client:
            response = client.post(url, json=payload or {}, headers=self._headers)
            response.raise_for_status()
            return response.json()
