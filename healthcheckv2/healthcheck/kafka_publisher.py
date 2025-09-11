"""
Kafka publisher for health reports.

Implementation uses optional 'kafka-python' if available; otherwise falls back to a
no-op publisher to avoid hard dependency at runtime. For unit tests, we use the
no-op path to ensure deterministic behavior.
"""
from __future__ import annotations

import json
from typing import Any, Optional


class KafkaPublisher:
    """Kafka publisher facade with optional dependency use."""

    def __init__(
        self,
        enabled: bool,
        bootstrap_servers: str,
        topic: str,
        client_id: str = "healthcheckv2",
        security_protocol: str = "PLAINTEXT",
        sasl_mechanism: Optional[str] = None,
        sasl_username: Optional[str] = None,
        sasl_password: Optional[str] = None,
        logger=None,
    ) -> None:
        self.enabled = enabled
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.client_id = client_id
        self.security_protocol = security_protocol
        self.sasl_mechanism = sasl_mechanism
        self.sasl_username = sasl_username
        self.sasl_password = sasl_password
        self.logger = logger
        self._producer = None
        if self.enabled:
            try:
                # Import lazily
                from kafka import KafkaProducer  # type: ignore
                params: dict[str, Any] = {
                    "bootstrap_servers": self.bootstrap_servers,
                    "client_id": self.client_id,
                    "value_serializer": lambda v: json.dumps(v).encode("utf-8"),
                    "security_protocol": self.security_protocol,
                }
                if self.sasl_mechanism:
                    params.update(
                        {
                            "sasl_mechanism": self.sasl_mechanism,
                            "sasl_plain_username": self.sasl_username,
                            "sasl_plain_password": self.sasl_password,
                        }
                    )
                self._producer = KafkaProducer(**params)
            except Exception as exc:  # pragma: no cover - optional dependency
                if self.logger:
                    self.logger.warning("Kafka disabled due to error: %s", str(exc))
                self.enabled = False

    # PUBLIC_INTERFACE
    def publish(self, message: dict[str, Any]) -> bool:
        """Publish a message to the configured topic if enabled.

        Args:
            message: JSON-serializable report.

        Returns:
            bool: True if successfully queued/sent (best-effort), False otherwise.
        """
        if not self.enabled or not self._producer:
            return False
        try:
            fut = self._producer.send(self.topic, message)
            fut.get(timeout=5)
            return True
        except Exception as exc:  # pragma: no cover - network error path
            if self.logger:
                self.logger.error("Kafka publish failed: %s", str(exc))
            return False

    def close(self) -> None:
        """Close producer if open."""
        if self._producer:  # pragma: no cover - trivial
            try:
                self._producer.flush(timeout=3)
                self._producer.close(timeout=3)
            except Exception:
                pass
