import subprocess

from healthcheck.healthcheck.kubectl import KubectlClient


def test_kubectl_base_args_used_in_exec(monkeypatch):
    captured = {}

    class P:
        returncode = 0
        stdout = "OK"
        stderr = ""

    def fake_run(cmd, check, capture_output, text, timeout):  # noqa: ANN001, ARG001
        # Capture the command to assert context/ns/extra_args are included
        captured["cmd"] = cmd
        return P()

    k = KubectlClient(
        kubectl_path="kubectl",
        context="ctx1",
        namespace="ns1",
        extra_args="--as=me --request-timeout=5s",
        simulator=None,
    )
    monkeypatch.setattr(subprocess, "run", fake_run)
    code, out, err = k.exec_in_pod("nsX", "podX", "c1", ["echo", "hi"])
    assert code == 0 and out == "OK" and err == ""
    cmd = captured["cmd"]
    # Order: kubectl --context ctx1 -n ns1 --as=me --request-timeout=5s exec -n nsX podX -c c1 -- echo hi
    # Ensure both configured base args and per-call args present
    assert cmd[0] == "kubectl"
    assert "--context" in cmd and "ctx1" in cmd
    # Per-call namespace should be present as part of exec args; base ns can exist as well
    assert "exec" in cmd
    assert "-n" in cmd
    # Extra args split correctly
    assert "--as=me" in cmd and "--request-timeout=5s" in cmd
