import json

from healthcheck.healthcheck_cli import main


def test_cli_runs_and_outputs_json(tmp_path, monkeypatch, capsys):
    cfg_content = """
env: dev
site_id: s1
cluster_id: c1
logging:
  level: INFO
  json: true
loki:
  enabled: false
kafka:
  enabled: false
simulation:
  enabled: true
  node_count: 2
  pod_count: 3
  failure_rate: 0.0
"""
    cfg = tmp_path / "config.yaml"
    cfg.write_text(cfg_content, encoding="utf-8")

    exit_code = main(["--config", str(cfg), "--site-id", "S1", "--cluster-id", "C1"])
    assert exit_code == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["site_id"] == "S1"
    assert data["cluster_id"] == "C1"
    assert "summary" in data
