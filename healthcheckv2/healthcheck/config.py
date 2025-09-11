"""
Configuration management for healthcheckv2.

Loads configuration from YAML file with environment overrides and supports
runtime parameter overrides (e.g., site_id, cluster_id). Provides strongly-typed
Config object for downstream modules.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import yaml


DEFAULT_CONFIG_PATH = os.environ.get("HEALTHCHECK_CONFIG", "/app/config/config.yaml")


@dataclass
class KafkaConfig:
    """Kafka configuration."""

    enabled: bool = False
    bootstrap_servers: str = ""
    topic: str = "health_reports"
    security_protocol: str = "PLAINTEXT"
    sasl_mechanism: Optional[str] = None
    sasl_username: Optional[str] = None
    sasl_password: Optional[str] = None
    client_id: str = "healthcheckv2"


@dataclass
class LokiConfig:
    """Loki configuration."""

    enabled: bool = False
    url: str = ""
    tenant_id: Optional[str] = None
    level: str = "INFO"
    labels: Dict[str, str] = field(default_factory=lambda: {"app": "healthcheckv2"})


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    json: bool = True


@dataclass
class SimulationConfig:
    """Simulation layer configuration."""

    enabled: bool = False
    node_count: int = 3
    pod_count: int = 8
    failure_rate: float = 0.0


@dataclass
class KubernetesConfig:
    """Kubernetes interaction config."""

    context: Optional[str] = None
    namespace: Optional[str] = None
    kubectl_path: str = "kubectl"
    extra_args: str = ""


@dataclass
class MetricConfig:
    """Metric selection configuration."""

    collect_resource_metrics: bool = True
    collect_network_metrics: bool = True
    # network metrics toggles
    sctp: bool = True
    rach: bool = True
    pucch: bool = True
    csr: bool = True


@dataclass
class ReportConfig:
    """Health report output configuration."""

    include_details: bool = True
    redact_sensitive: bool = True
    version: str = "1.0.0"


@dataclass
class Config:
    """Root configuration type."""

    env: str
    site_id: str
    cluster_id: str
    kafka: KafkaConfig
    loki: LokiConfig
    logging: LoggingConfig
    simulation: SimulationConfig
    kubernetes: KubernetesConfig
    metrics: MetricConfig
    report: ReportConfig

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Config":
        """Create a Config from raw dict, applying defaults."""
        kafka = KafkaConfig(**data.get("kafka", {}))
        loki = LokiConfig(**data.get("loki", {}))
        logging_cfg = LoggingConfig(**data.get("logging", {}))
        simulation = SimulationConfig(**data.get("simulation", {}))
        k8s = KubernetesConfig(**data.get("kubernetes", {}))
        metrics = MetricConfig(**data.get("metrics", {}))
        report = ReportConfig(**data.get("report", {}))
        return Config(
            env=str(data.get("env", "dev")),
            site_id=str(data.get("site_id", "")),
            cluster_id=str(data.get("cluster_id", "")),
            kafka=kafka,
            loki=loki,
            logging=logging_cfg,
            simulation=simulation,
            kubernetes=k8s,
            metrics=metrics,
            report=report,
        )


# PUBLIC_INTERFACE
def load_config(
    path: Optional[str] = None,
    site_id: Optional[str] = None,
    cluster_id: Optional[str] = None,
) -> Config:
    """Load configuration from YAML file and apply CLI/env overrides.

    Args:
        path: Optional override for config path. If None, uses HEALTHCHECK_CONFIG or default.
        site_id: Optional site id CLI override.
        cluster_id: Optional cluster id CLI override.

    Returns:
        Config: Resolved configuration object.

    Raises:
        FileNotFoundError: If the specified path does not exist.
        yaml.YAMLError: If YAML is malformed.
        ValueError: If required fields are missing.
    """
    cfg_path = path or DEFAULT_CONFIG_PATH
    if not os.path.exists(cfg_path):
        raise FileNotFoundError(f"Config file not found at {cfg_path}")

    with open(cfg_path, "r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    # Apply environment variable overrides for common fields
    raw["env"] = os.environ.get("HEALTHCHECK_ENV", raw.get("env", "dev"))

    # CLI overrides
    if site_id:
        raw["site_id"] = site_id
    if cluster_id:
        raw["cluster_id"] = cluster_id

    cfg = Config.from_dict(raw)

    # Validation
    if not cfg.site_id:
        raise ValueError("site_id is required (config or CLI)")
    if not cfg.cluster_id:
        raise ValueError("cluster_id is required (config or CLI)")

    # Security sanity: if Kafka SASL is configured ensure both username/password present
    if cfg.kafka.enabled and bool(cfg.kafka.sasl_mechanism):
        if not (cfg.kafka.sasl_username and cfg.kafka.sasl_password):
            raise ValueError("Kafka SASL enabled but credentials are incomplete")

    return cfg
