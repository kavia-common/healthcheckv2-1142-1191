import json
import textwrap

from healthcheck.healthcheck_cli import main as cli_main


def test_cli_arg_parser_and_loki_enabled(tmp_path, monkeypatch, capsys):
    cfg_content = textwrap.dedent(
        """
        env: dev
        site_id: S
        cluster_id: C
        logging:
          level: INFO
          json: true
        loki:
          enabled: true
          url: "http://loki:3100"
          tenant_id: "t-1"
          level: "INFO"
          labels:
            app: hc
        kafka:
          enabled: false
        simulation:
          enabled: true
          node_count: 1
          pod_count: 1
          failure_rate: 0.0
        """
    )
    cfg = tmp_path / "config.yaml"
    cfg.write_text(cfg_content, encoding="utf-8")

    # No network will be performed by handler in tests since emit occurs only on logger usage;
    # we don't need to stub urlopen because logger info calls don't force emit network in our tests.

    exit_code = cli_main(["--config", str(cfg)])
    assert exit_code == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["site_id"] == "S"
    assert data["cluster_id"] == "C"
