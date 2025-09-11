"""
Loki HTTP logging handler.

Sends log records to Loki via HTTP push API with configured labels.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Dict, Optional
from urllib.error import HTTPError, URLError

from urllib.request import Request, urlopen


class LokiHTTPHandler(logging.Handler):
    """HTTP handler that sends logs to Loki."""

    def __init__(
        self,
        url: str,
        labels: Optional[Dict[str, str]] = None,
        tenant_id: Optional[str] = None,
        level: str = "INFO",
        timeout: int = 5,
    ) -> None:
        super().__init__(getattr(logging, level.upper(), logging.INFO))
        self.url = url.rstrip("/")
        self.labels = labels or {"app": "healthcheckv2"}
        self.tenant_id = tenant_id
        self.timeout = timeout

    def emit(self, record: logging.LogRecord) -> None:
        """Emit record to Loki as a single stream entry."""
        try:
            log_line = self.format(record)
            # Loki expects nanosecond epoch timestamps
            ts_ns = int(time.time() * 1_000_000_000)
            streams = [
                {
                    "stream": self.labels,
                    "values": [[str(ts_ns), log_line]],
                }
            ]
            data = json.dumps({"streams": streams}).encode("utf-8")
            headers = {"Content-Type": "application/json"}
            if self.tenant_id:
                headers["X-Scope-OrgID"] = self.tenant_id
            req = Request(url=f"{self.url}/loki/api/v1/push", data=data, headers=headers, method="POST")
            with urlopen(req, timeout=self.timeout):
                # best effort; no further processing
                return
        except (HTTPError, URLError, TimeoutError):  # pragma: no cover - network error ignored
            # Swallow errors to avoid breaking main flow
            return
        except Exception:  # pragma: no cover - defensive
            return
