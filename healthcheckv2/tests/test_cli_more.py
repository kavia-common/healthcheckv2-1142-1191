import json
import textwrap
import builtins
import types

from healthcheck.healthcheck_cli import main


def test_cli_fails_with_bad_config_path(capsys):
    code = main(["--config", "/non/existent/path.yaml", "--site-id", "S", "--cluster-id", "C"])
    assert code == 2
    err = capsys.readouterr().err
    assert "Failed to load config" in err


def test_cli_with_kafka_enabled_publish_failure(tmp_path, monkeypatch, capsys):
    cfg_content = textwrap.dedent(
        """
        env: dev
        site_id: s1
        cluster_id: c1
        logging:
          level: INFO
          json: true
        loki:
          enabled: false
        kafka:
          enabled: true
          bootstrap_servers: "k:9092"
          topic: "t1"
        simulation:
          enabled: true
          node_count: 1
          pod_count: 1
          failure_rate: 0.0
        """
    )
    cfg = tmp_path / "config.yaml"
    cfg.write_text(cfg_content, encoding="utf-8")

    # Provide dummy kafka that "succeeds" send but we won't assert side effects; we just want code path covered.
    class DummyFuture:
        def get(self, timeout=5):  # noqa: ARG002
            raise RuntimeError("fail")  # force publish fail path

    class DummyProducer:
        def __init__(self, **kwargs):  # noqa: ANN001
            self.kwargs = kwargs

        def send(self, topic, value):
            return DummyFuture()

        def flush(self, timeout=3):  # noqa: ARG002
            return None

        def close(self, timeout=3):  # noqa: ARG002
            return None

    dummy_mod = types.SimpleNamespace(KafkaProducer=lambda **kwargs: DummyProducer(**kwargs))  # noqa: E731

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: ANN001
        if name == "kafka":
            return dummy_mod
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    code = main(["--config", str(cfg)])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["site_id"] == "s1"
    assert data["cluster_id"] == "c1"
