import subprocess
import pytest

from healthcheck.healthcheck.kubectl import KubectlClient, KubectlError
from healthcheck.healthcheck.simulation import SimulationLayer


def test_kubectl_simulation_paths():
    sim = SimulationLayer(enabled=True, node_count=2, pod_count=3, failure_rate=0.0)
    k = KubectlClient(simulator=sim)
    nodes = k.get_nodes()
    pods = k.get_pods()
    top = k.top_pods()
    code, out, err = k.exec_in_pod("default", "pod-0", None, ["sh", "-c", "echo sctp"])
    assert len(nodes) == 2
    assert len(pods) == 3
    assert len(top) == 3
    assert code == 0
    assert "ok" in out or out == "ok"


def test_kubectl_real_error(monkeypatch):
    def fake_run(*args, **kwargs):  # noqa: ANN001, ANN002
        class P:
            returncode = 1
            stdout = ""
            stderr = "boom"
        return P()
    k = KubectlClient(simulator=None)
    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(KubectlError):
        k.get_nodes()
