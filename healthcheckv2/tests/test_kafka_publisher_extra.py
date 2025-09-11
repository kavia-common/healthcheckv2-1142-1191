import builtins
import types

from healthcheck.healthcheck.kafka_publisher import KafkaPublisher


class DummyFuture:
    def get(self, timeout=5):  # noqa: ARG002
        return True


class DummyProducer:
    def __init__(self, **kwargs):  # noqa: ANN001
        # Capture params to assert SASL wiring
        self.params = kwargs
        self.closed = False

    def send(self, topic, value):
        return DummyFuture()

    def flush(self, timeout=3):  # noqa: ARG002
        return None

    def close(self, timeout=3):  # noqa: ARG002
        self.closed = True


def test_kafka_sasl_params_and_close(monkeypatch):
    dummy_mod = types.SimpleNamespace(KafkaProducer=lambda **kwargs: DummyProducer(**kwargs))  # noqa: E731

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: ANN001
        if name == "kafka":
            return dummy_mod
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    kp = KafkaPublisher(
        enabled=True,
        bootstrap_servers="k:9092",
        topic="t",
        client_id="cid",
        security_protocol="SASL_SSL",
        sasl_mechanism="PLAIN",
        sasl_username="u",
        sasl_password="p",
    )
    # Publish something and then close
    ok = kp.publish({"k": "v"})
    assert ok is True
    prod = kp._producer  # type: ignore[attr-defined]
    # Assert SASL params were forwarded
    assert prod.params["security_protocol"] == "SASL_SSL"
    assert prod.params["sasl_mechanism"] == "PLAIN"
    assert prod.params["sasl_plain_username"] == "u"
    assert prod.params["sasl_plain_password"] == "p"
    kp.close()
    assert prod.closed is True
