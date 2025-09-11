import subprocess
import pytest

from healthcheck.healthcheck.kubectl import KubectlClient, KubectlError


def test_kubectl_top_pods_parse_success(monkeypatch):
    lines = [
        "default pod-a 5m 20Mi",
        "kube-system pod-b 7m 33Mi",
        "ns pod-c 10m 100Mi",
    ]
    out = "\n".join(lines)

    class P:
        returncode = 0
        stdout = out
        stderr = ""

    def fake_run(cmd, check, capture_output, text, timeout):  # noqa: ANN001, ARG001
        assert "top" in cmd
        return P()

    k = KubectlClient(simulator=None)
    monkeypatch.setattr(subprocess, "run", fake_run)
    metrics = k.top_pods()
    assert len(metrics) == 3
    assert metrics[0]["namespace"] == "default"
    assert metrics[1]["name"] == "pod-b"
    assert metrics[2]["memory"] == "100Mi"


def test_kubectl_timeout(monkeypatch):
    def fake_run(*args, **kwargs):  # noqa: ANN001, ANN002
        raise subprocess.TimeoutExpired(cmd="kubectl", timeout=1)

    k = KubectlClient()
    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(KubectlError) as e:
        k.get_nodes()
    assert "timed out" in str(e.value)


def test_kubectl_exec_args(monkeypatch):
    # verify exec_in_pod builds correct arguments and returns tuple
    class P:
        returncode = 0
        stdout = "OK"
        stderr = ""

    def fake_run(cmd, check, capture_output, text, timeout):  # noqa: ANN001, ARG001
        # Ensure the command includes -n namespace, pod, and --
        assert cmd[:3] == ["kubectl", "exec", "-n"]
        assert "--" in cmd
        return P()

    k = KubectlClient()
    monkeypatch.setattr(subprocess, "run", fake_run)
    code, out, err = k.exec_in_pod("ns1", "pod1", None, ["sh", "-c", "echo hi"])
    assert code == 0 and out == "OK" and err == ""
