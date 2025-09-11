import logging
from urllib.error import HTTPError, URLError

from healthcheck.healthcheck.loki_handler import LokiHTTPHandler


class DummyResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):  # noqa: ANN001, ARG002
        return False


def test_loki_handler_emit_http_error(monkeypatch):
    handler = LokiHTTPHandler(url="http://localhost:3100", labels={"app": "hc"}, tenant_id="t1", level="INFO")

    def fake_urlopen(req, timeout):  # noqa: ANN001, ARG001
        raise HTTPError(url=req.full_url, code=500, msg="err", hdrs=None, fp=None)

    monkeypatch.setattr("healthcheck.healthcheck.loki_handler.urlopen", fake_urlopen)
    logger = logging.getLogger("loki-http-error")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    # Should swallow errors and not raise
    logger.info("hello")


def test_loki_handler_emit_url_error(monkeypatch):
    handler = LokiHTTPHandler(url="http://localhost:3100", labels={"app": "hc"}, tenant_id=None, level="INFO")

    def fake_urlopen(req, timeout):  # noqa: ANN001, ARG001
        raise URLError("down")

    monkeypatch.setattr("healthcheck.healthcheck.loki_handler.urlopen", fake_urlopen)
    logger = logging.getLogger("loki-url-error")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.warning("warn")


def test_loki_handler_emit_generic_exception(monkeypatch):
    handler = LokiHTTPHandler(url="http://localhost:3100", labels={"app": "hc"}, tenant_id=None, level="INFO")

    def fake_urlopen(req, timeout):  # noqa: ANN001, ARG001
        raise RuntimeError("boom")

    monkeypatch.setattr("healthcheck.healthcheck.loki_handler.urlopen", fake_urlopen)
    logger = logging.getLogger("loki-generic-error")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.error("err")
