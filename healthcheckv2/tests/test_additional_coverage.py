import json
import logging
import subprocess

from healthcheck.healthcheck.checks import HealthChecker
from healthcheck.healthcheck.kubectl import KubectlClient
from healthcheck.healthcheck.logger import JsonFormatter
from healthcheck.healthcheck.simulation import SimulationLayer


def test_json_formatter_handles_missing_exc_info_safely():
    # Create a record without exc_info or extras to hit safe paths
    fmt = JsonFormatter()
    logger = logging.getLogger("fmt-missing-exc")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    rec = logger.makeRecord(
        name="fmt-missing-exc",
        level=logging.INFO,
        fn="test.py",
        lno=10,
        msg="hello",
        args=(),
        exc_info=None,
        func="f",
        extra={},  # no extras
    )
    out = fmt.format(rec)
    data = json.loads(out)
    assert data["message"] == "hello"
    assert "exc_info" not in data


def test_json_formatter_handles_true_exc_info_outside_except_block():
    # exc_info=True outside of an except: sys.exc_info() likely (None,None,None), but ensure no crash
    fmt = JsonFormatter()
    logger = logging.getLogger("fmt-true-exc")
    logger.handlers.clear()
    logger.setLevel(logging.INFO)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    # Create a record with exc_info=True outside except; formatter should handle gracefully
    rec = logger.makeRecord(
        name="fmt-true-exc",
        level=logging.ERROR,
        fn="x.py",
        lno=1,
        msg="boom-outside",
        args=(),
        exc_info=True,
        func="f",
        extra={},
    )
    # Should not raise and may or may not include exc_info depending on runtime, but must be valid JSON
    out = fmt.format(rec)
    data = json.loads(out)
    assert data["level"] == "ERROR"
    assert data["message"] == "boom-outside"


def test_kubectl_top_pods_nonzero_return_code_graceful_empty(monkeypatch):
    # Ensure when top pods returns non-zero, method returns []
    class P:
        returncode = 1
        stdout = ""
        stderr = "no metrics"

    def fake_run(cmd, check, capture_output, text, timeout):  # noqa: ANN001, ARG001
        assert "top" in cmd
        return P()

    k = KubectlClient(simulator=None)
    monkeypatch.setattr(subprocess, "run", fake_run)
    top = k.top_pods()
    assert top == []


def test_kubectl_exec_in_pod_with_container_arg(monkeypatch):
    # Ensure container argument is correctly wired (-c container)
    class P:
        returncode = 0
        stdout = "OK"
        stderr = ""

    captured = {}

    def fake_run(cmd, check, capture_output, text, timeout):  # noqa: ANN001, ARG001
        captured["cmd"] = cmd
        return P()

    k = KubectlClient()
    monkeypatch.setattr(subprocess, "run", fake_run)
    code, out, err = k.exec_in_pod("ns", "podx", "cont1", ["echo", "hello"])
    assert code == 0 and out == "OK" and err == ""
    cmd = captured["cmd"]
    # expect: kubectl exec -n ns podx -c cont1 -- echo hello
    assert cmd[:3] == ["kubectl", "exec", "-n"]
    assert "-c" in cmd and "cont1" in cmd
    assert "--" in cmd


def test_simulation_failure_rate_bounds_and_maybe_fail(monkeypatch):
    # failure_rate must be clamped to [0,1]
    sim = SimulationLayer(enabled=True, node_count=1, pod_count=1, failure_rate=-5.0)
    assert sim.failure_rate == 0.0
    sim2 = SimulationLayer(enabled=True, node_count=1, pod_count=1, failure_rate=5.0)
    assert sim2.failure_rate == 1.0

    # Make random deterministic to cover both True/False outcomes
    seq = iter([0.2, 0.8])  # first < 0.5 True, then > 0.5 False

    def fake_random():
        return next(seq)

    monkeypatch.setattr("healthcheck.healthcheck.simulation.random.random", fake_random)
    sim_mid = SimulationLayer(enabled=True, node_count=1, pod_count=1, failure_rate=0.5)
    assert sim_mid._maybe_fail() is True
    assert sim_mid._maybe_fail() is False


def test_healthchecker_selective_network_metrics_flags():
    # Disable some of the network metric keys to ensure skipping logic
    sim = SimulationLayer(enabled=True, node_count=1, pod_count=1, failure_rate=0.0)
    k = KubectlClient(simulator=sim)
    flags = {
        "collect_resource_metrics": True,
        "collect_network_metrics": True,
        "sctp": False,
        "rach": True,
        "pucch": False,
        "csr": True,
    }
    hc = HealthChecker(
        kctl=k,
        site_id="S",
        cluster_id="C",
        env="dev",
        include_details=True,
        redact_sensitive=False,
        metrics_flags=flags,
    )
    # trigger only rach and csr, not sctp/pucch
    nm = hc._network_metrics()
    assert nm["enabled"] is True
    # Only two metrics should appear in details for the single sampled pod
    details = nm["details"][0]["metrics"]
    assert "rach" in details and "csr" in details
    assert "sctp" not in details and "pucch" not in details


def test_healthchecker_resource_metrics_disabled_returns_flagged():
    sim = SimulationLayer(enabled=True, node_count=0, pod_count=0, failure_rate=0.0)
    k = KubectlClient(simulator=sim)
    hc = HealthChecker(
        kctl=k,
        site_id="S",
        cluster_id="C",
        env="dev",
        include_details=True,
        redact_sensitive=False,
        metrics_flags={"collect_resource_metrics": False, "collect_network_metrics": False},
    )
    report = hc.run()
    assert report.summary["resource_metrics_enabled"] is False
    assert report.summary["network_metrics_enabled"] is False
    # With include_details True and redaction disabled, details remains a dict
    assert isinstance(report.details, dict)
