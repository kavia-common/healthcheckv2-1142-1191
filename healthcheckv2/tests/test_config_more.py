import textwrap
import pytest

from healthcheck.healthcheck.config import load_config


def test_yaml_malformed_raises(tmp_path):
    bad = tmp_path / "config.yaml"
    # malformed YAML (indentation / missing colon)
    bad.write_text("env: dev\nsite_id s1\ncluster_id: c1\n", encoding="utf-8")
    with pytest.raises(Exception):
        load_config(str(bad))


def test_env_override(tmp_path, monkeypatch):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        textwrap.dedent(
            """
            env: prod
            site_id: s1
            cluster_id: c1
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("HEALTHCHECK_ENV", "stage")
    cfg = load_config(str(cfg_path))
    assert cfg.env == "stage"
