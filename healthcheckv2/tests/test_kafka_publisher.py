import types
import builtins

from healthcheck.healthcheck.kafka_publisher import KafkaPublisher


class DummyFuture:
    def __init__(self, raises: Exception | None = None):
        self._raises = raises

    def get(self, timeout=5):  # noqa: ARG002
        if self._raises:
            raise self._raises
        return True


class DummyProducer:
    def __init__(self):
        self.sent = []

    def send(self, topic, value):
        # value is already serialized by value_serializer within KafkaProducer, but here we mimic facade behavior.
        self.sent.append((topic, value))
        return DummyFuture()

    def flush(self, timeout=3):  # noqa: ARG002
        return None

    def close(self, timeout=3):  # noqa: ARG002
        return None


def test_kafka_publisher_disabled_returns_false_on_publish():
    kp = KafkaPublisher(
        enabled=False,
        bootstrap_servers="k:9092",
        topic="t",
    )
    assert kp.publish({"x": 1}) is False


def test_kafka_publisher_enabled_no_kafka_lib_logs_warning_and_disables(monkeypatch):
    # Simulate ImportError when importing kafka.KafkaProducer
    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: ANN001
        if name == "kafka":
            raise ImportError("no kafka lib")
        return builtins.__import__(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    kp = KafkaPublisher(
        enabled=True,
        bootstrap_servers="k:9092",
        topic="t",
        logger=None,  # no logger so it won't crash on warning
    )
    assert kp.enabled is False
    assert kp.publish({"a": 2}) is False


def test_kafka_publisher_happy_path_publish_success(monkeypatch):
    # Provide a dummy kafka module with KafkaProducer
    dummy_mod = types.SimpleNamespace()
    dummy_mod.KafkaProducer = lambda **kwargs: DummyProducer()  # noqa: E731

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: ANN001
        if name == "kafka":
            return dummy_mod
        return builtins.__import__(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    kp = KafkaPublisher(
        enabled=True,
        bootstrap_servers="k:9092",
        topic="topic1",
    )
    ok = kp.publish({"hello": "world"})
    assert ok is True
    kp.close()  # ensure close path executed without error


def test_kafka_publisher_publish_failure_logs_and_returns_false(monkeypatch):
    class FailingProducer(DummyProducer):
        def send(self, topic, value):
            return DummyFuture(raises=RuntimeError("send failed"))

    dummy_mod = types.SimpleNamespace()
    dummy_mod.KafkaProducer = lambda **kwargs: FailingProducer()  # noqa: E731

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: ANN001
        if name == "kafka":
            return dummy_mod
        return builtins.__import__(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    logs = []

    class DummyLogger:
        def error(self, msg, *args, **kwargs):  # noqa: ANN001, ARG002
            logs.append(msg % args if args else msg)

    kp = KafkaPublisher(
        enabled=True,
        bootstrap_servers="k:9092",
        topic="topic2",
        logger=DummyLogger(),
    )
    ok = kp.publish({"x": 3})
    assert ok is False
    assert any("Kafka publish failed" in l for l in logs)
