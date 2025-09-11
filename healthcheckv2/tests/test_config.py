import textwrap
import pytest

from healthcheck.healthcheck.config import load_config


def write_tmp_yaml(tmp_path, content: str) -> str:
    p = tmp_path / "config.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return str(p)


def test_load_config_basic(tmp_path, monkeypatch):
    cfg_path = write_tmp_yaml(
        tmp_path,
        """
        env: dev
        site_id: s1
        cluster_id: c1
        """,
    )
    cfg = load_config(cfg_path)
    assert cfg.env == "dev"
    assert cfg.site_id == "s1"
    assert cfg.cluster_id == "c1"


def test_load_config_cli_override(tmp_path):
    cfg_path = write_tmp_yaml(
        tmp_path,
        """
        env: dev
        site_id: s1
        cluster_id: c1
        """,
    )
    cfg = load_config(cfg_path, site_id="S2", cluster_id="C2")
    assert cfg.site_id == "S2"
    assert cfg.cluster_id == "C2"


def test_load_config_missing_site(tmp_path):
    cfg_path = write_tmp_yaml(
        tmp_path,
        """
        env: dev
        cluster_id: c1
        """,
    )
    with pytest.raises(ValueError):
        load_config(cfg_path)


def test_load_config_missing_cluster(tmp_path):
    cfg_path = write_tmp_yaml(
        tmp_path,
        """
        env: dev
        site_id: s1
        """,
    )
    with pytest.raises(ValueError):
        load_config(cfg_path)


def test_kafka_sasl_validation(tmp_path):
    cfg_path = write_tmp_yaml(
        tmp_path,
        """
        env: dev
        site_id: s1
        cluster_id: c1
        kafka:
          enabled: true
          bootstrap_servers: "localhost:9092"
          sasl_mechanism: PLAIN
          sasl_username: user
          # password missing
        """,
    )
    with pytest.raises(ValueError):
        load_config(cfg_path)
