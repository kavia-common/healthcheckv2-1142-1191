import logging

from healthcheck.healthcheck.logger import get_logger
from healthcheck.healthcheck.loki_handler import LokiHTTPHandler


def test_get_logger_json():
    logger = get_logger(level="DEBUG", json_output=True)
    assert isinstance(logger, logging.Logger)
    assert logger.level == logging.DEBUG
    # ensure stream handler present
    assert any(isinstance(h, logging.Handler) for h in logger.handlers)


def test_get_logger_with_loki(monkeypatch):
    # Create a Loki handler but stub emit to avoid network
    handler = LokiHTTPHandler(url="http://localhost:3100", labels={"app": "x"})
    def fake_emit(record):  # noqa: ANN001
        return None
    handler.emit = fake_emit  # type: ignore
    logger = get_logger(level="INFO", json_output=False, loki_handler=handler)
    assert any(isinstance(h, LokiHTTPHandler) for h in logger.handlers)
    logger.info("hello", extra={"site_id": "s1", "cluster_id": "c1"})
