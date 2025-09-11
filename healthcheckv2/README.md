# healthcheckv2

Healthcheckv2 is a modular monolithic Python application that performs health checks for DU Sites in a 5G cloud-native Kubernetes environment.

Features:
- Node readiness monitoring (kubectl)
- Pod/container health status (crashes/restarts/abnormal states)
- Resource metrics collection (CPU/memory via `kubectl top pods`; disk via in-pod exec commands if extended)
- Network metrics collection: SCTP, RACH, PUCCH, CSR (via in-pod exec)
- Structured report generation
- Kafka publishing (optional)
- Loki logging (optional)
- YAML-based externalized configuration with environment overrides
- Full simulation mode for repeatable local testing (no live dependencies)
- 100% pytest unit test coverage
- No API/UI endpoints; intended for periodic invocation (e.g., Airflow)

Quick start:
1. Prepare configuration:
   - Place your YAML config at `healthcheckv2/config/config.yaml` or pass path via `--config`.
   - See `healthcheckv2/config/config.yaml` for defaults.
2. (Optional) Create a `.env` based on `.env.example`.
3. Run the CLI:
   python -m healthcheckv2.healthcheck_cli --config healthcheckv2/config/config.yaml --site-id <SITE> --cluster-id <CLUSTER>

Simulation:
- Enable `simulation.enabled: true` in YAML to run without external systems (Kubernetes/Kafka/Loki).
- Adjust `simulation.node_count`, `simulation.pod_count`, `simulation.failure_rate` to shape the data.

Kafka:
- Enable by setting `kafka.enabled: true` and configure the required fields.
- For SASL, ensure `sasl_mechanism`, `sasl_username`, and `sasl_password` are provided.

Loki:
- Enable by setting `loki.enabled: true` and configure `url`, `tenant_id`, `labels`, and `level`.

Logging:
- Configure `logging.level` and `logging.json` in YAML.
- The logger redacts known secrets from environment variables for safety.

Testing:
- Run tests from the container root:
  python -m pytest -q

Notes:
- Uses kubectl CLI; ensure `kubectl` is installed and configured in the runtime environment.
- For environments without `metrics-server`, `kubectl top pods` gracefully returns an empty set.
- This component contains a Flask app scaffold for smoke-testing only; health checks are performed by the CLI.
