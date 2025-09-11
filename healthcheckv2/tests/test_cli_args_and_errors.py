import json
import textwrap

from healthcheck.healthcheck_cli import main


def test_cli_runs_with_only_config_and_uses_defaults(tmp_path, capsys):
    cfg_content = textwrap.dedent(
        """
        env: dev
        site_id: SDEF
        cluster_id: CDEF
        logging:
          level: INFO
          json: true
        kafka:
          enabled: false
        simulation:
          enabled: true
          node_count: 1
          pod_count: 1
          failure_rate: 0.0
        """
    )
    cfg = tmp_path / "cfg.yaml"
    cfg.write_text(cfg_content, encoding="utf-8")
    code = main(["--config", str(cfg)])
    assert code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["site_id"] == "SDEF"
    assert data["cluster_id"] == "CDEF"
