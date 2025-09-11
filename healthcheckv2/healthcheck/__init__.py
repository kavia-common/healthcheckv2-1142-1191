"""
Healthcheckv2 monolithic application package.

This package organizes the core logic for:
- Configuration management
- Logging (including Loki handler)
- Kubernetes interactions via kubectl (with simulation layer)
- Health checks (nodes, pods/containers, resource & network metrics)
- Report generation
- Kafka publishing
- CLI entrypoint

Note:
- This package is used by the CLI script healthcheck_cli.py to run the checks.
- All public functions/classes are documented and marked with PUBLIC_INTERFACE comments.
"""
from .config import Config, load_config
from .logger import get_logger
from .kubectl import KubectlClient
from .checks import HealthChecker, HealthReport
from .kafka_publisher import KafkaPublisher
from .loki_handler import LokiHTTPHandler
from .simulation import SimulationLayer

__all__ = [
    "Config",
    "load_config",
    "get_logger",
    "KubectlClient",
    "HealthChecker",
    "HealthReport",
    "KafkaPublisher",
    "LokiHTTPHandler",
    "SimulationLayer",
]
