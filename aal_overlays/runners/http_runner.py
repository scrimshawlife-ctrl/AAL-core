"""
HTTP-based overlay runner using urllib.request.

Provides deterministic JSON encoding, retries, and timeout handling.
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict, Optional
from urllib.parse import urljoin


def canonical_json_bytes(obj: Any) -> bytes:
    """
    Produce canonical JSON bytes for deterministic HTTP requests.

    Args:
        obj: Any JSON-serializable object

    Returns:
        UTF-8 encoded canonical JSON bytes
    """
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


class HTTPOverlayRunner:
    """
    HTTP overlay runner with retries and deterministic encoding.

    Uses urllib.request for zero external dependencies.
    """

    def __init__(
        self,
        base_url: str,
        timeout: float = 30.0,
        max_retries: int = 2,
        retry_delays: tuple[float, ...] = (0.2, 0.5),
    ):
        """
        Initialize HTTP runner.

        Args:
            base_url: Base URL for the overlay service
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries (default: 2)
            retry_delays: Delay sequence for retries in seconds (default: 0.2s, 0.5s)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delays = retry_delays

    def call(
        self,
        path: str,
        payload: Dict[str, Any],
        method: str = "POST",
    ) -> Dict[str, Any]:
        """
        Execute HTTP request to overlay service.

        Args:
            path: URL path (relative to base_url)
            payload: Request payload dictionary
            method: HTTP method (default: POST)

        Returns:
            Response dictionary with structure:
            {
                "ok": bool,
                "result": Any,  # Present if ok=True
                "error": str,   # Present if ok=False
                "provenance": dict  # Optional provenance data
            }

        Raises:
            Exception: If all retries fail
        """
        url = urljoin(self.base_url + "/", path.lstrip("/"))

        # Prepare deterministic request body
        request_body = canonical_json_bytes(payload)

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        }

        # Retry loop
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                request = urllib.request.Request(
                    url,
                    data=request_body,
                    headers=headers,
                    method=method,
                )

                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    response_body = response.read().decode("utf-8")
                    result = json.loads(response_body)

                    # Wrap in standard response format if not already
                    if "ok" not in result:
                        result = {
                            "ok": True,
                            "result": result,
                        }

                    return result

            except urllib.error.HTTPError as e:
                # HTTP error response
                try:
                    error_body = e.read().decode("utf-8")
                    error_data = json.loads(error_body)
                except Exception:
                    error_data = {"error": f"HTTP {e.code}: {e.reason}"}

                # Don't retry on 4xx errors (client errors)
                if 400 <= e.code < 500:
                    return {
                        "ok": False,
                        "error": error_data.get("error", f"HTTP {e.code}"),
                        "http_status": e.code,
                    }

                last_error = error_data.get("error", str(e))

            except urllib.error.URLError as e:
                # Network error
                last_error = f"Network error: {e.reason}"

            except json.JSONDecodeError as e:
                # Invalid JSON response
                return {
                    "ok": False,
                    "error": f"Invalid JSON response: {e}",
                }

            except Exception as e:
                last_error = f"Unexpected error: {type(e).__name__}: {e}"

            # Wait before retry (if not last attempt)
            if attempt < self.max_retries:
                delay = self.retry_delays[min(attempt, len(self.retry_delays) - 1)]
                time.sleep(delay)

        # All retries failed
        return {
            "ok": False,
            "error": f"All retries failed. Last error: {last_error}",
            "attempts": self.max_retries + 1,
        }
