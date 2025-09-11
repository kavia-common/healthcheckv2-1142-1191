# healthcheckv2-1142-1191

Healthcheckv2 monolithic script with modular architecture.

How to run:
1. Put your config at healthcheckv2/config/config.yaml or pass via --config
2. Run the CLI:
   python -m healthcheckv2.healthcheck_cli --config healthcheckv2/config/config.yaml --site-id <SITE> --cluster-id <CLUSTER>

Notes:
- Uses kubectl CLI; ensure kubectl is available inside the container and authorized.
- For testing or local runs, enable simulation in the YAML config.
- Kafka and Loki are optional; if disabled in config, the script still runs and prints JSON report to stdout.