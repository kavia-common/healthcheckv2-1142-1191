import json
import logging
import os
import sys

from healthcheck.healthcheck.logger import get_logger, JsonFormatter


def test_json_formatter_includes_exc_info_and_extras():
    logger = logging.getLogger("hc-test-json")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    fmt = JsonFormatter()
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    try:
        raise ValueError("boom")
    except ValueError:
        # Capture the actual exc_info tuple inside the except block so that
        # formatting outside the block can still include a valid traceback.
        captured = sys.exc_info()
        rec = logger.makeRecord(
            name="hc-test-json",
            level=logging.ERROR,
            fn="x.py",
            lno=1,
            msg="failed",
            args=(),
            exc_info=True,  # maintain normal semantics
            func="f",
            extra={
                "site_id": "S",
                "cluster_id": "C",
                "env": "dev",
                # Provide captured_exc_info for robust formatting later
                "captured_exc_info": captured,
            },
        )
    out = fmt.format(rec)
    data = json.loads(out)
    assert data["level"] == "ERROR"
    assert data["site_id"] == "S"
    assert "exc_info" in data
    assert "ValueError" in data["exc_info"]


def test_get_logger_env_redaction(monkeypatch):
    monkeypatch.setenv("KAFKA_PASSWORD", "secret")
    monkeypatch.setenv("SASL_PASSWORD", "secret2")
    logger = get_logger(name="hc-redact", level="INFO", json_output=True, loki_handler=None)
    # after get_logger, envs should be redacted (set to ***)
    assert os.environ.get("KAFKA_PASSWORD") == "***"
    assert os.environ.get("SASL_PASSWORD") == "***"
    assert any(isinstance(h, logging.Handler) for h in logger.handlers)
