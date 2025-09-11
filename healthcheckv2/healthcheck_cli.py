#!/usr/bin/env python3
"""
healthcheckv2 CLI entrypoint.

Runs health checks for a given site_id and cluster_id using configuration from YAML,
publishes report to Kafka if enabled, and logs to stdout and Loki if configured.

Usage:
    python -m healthcheckv2.healthcheck_cli --config /app/config/config.yaml --site-id SITE --cluster-id CLUSTER
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from healthcheck.healthcheck import (  # type: ignore
    KafkaPublisher,
    KubectlClient,
    LokiHTTPHandler,
    SimulationLayer,
    get_logger,
    load_config,
)
from healthcheck.healthcheck.checks import HealthChecker  # type: ignore


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Healthcheckv2 CLI")
    parser.add_argument("--config", help="Path to YAML config", default=None)
    parser.add_argument("--site-id", help="Site ID", default=None)
    parser.add_argument("--cluster-id", help="Cluster ID", default=None)
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    """CLI main entrypoint."""
    args = _parse_args(argv)
    try:
        cfg = load_config(args.config, site_id=args.site_id, cluster_id=args.cluster_id)
    except Exception as exc:
        print(f"Failed to load config: {exc}", file=sys.stderr)
        return 2

    loki_handler = None
    if cfg.loki.enabled and cfg.loki.url:
        loki_handler = LokiHTTPHandler(
            url=cfg.loki.url, labels=cfg.loki.labels, tenant_id=cfg.loki.tenant_id, level=cfg.loki.level
        )

    logger = get_logger(level=cfg.logging.level, json_output=cfg.logging.json, loki_handler=loki_handler)
    logger.info("healthcheck starting", extra={"site_id": cfg.site_id, "cluster_id": cfg.cluster_id, "env": cfg.env})

    simulator = SimulationLayer(
        enabled=cfg.simulation.enabled,
        node_count=cfg.simulation.node_count,
        pod_count=cfg.simulation.pod_count,
        failure_rate=cfg.simulation.failure_rate,
    )

    kctl = KubectlClient(
        kubectl_path=cfg.kubernetes.kubectl_path,
        context=cfg.kubernetes.context,
        namespace=cfg.kubernetes.namespace,
        extra_args=cfg.kubernetes.extra_args,
        simulator=simulator if cfg.simulation.enabled else None,
    )

    metrics_flags = {
        "collect_resource_metrics": cfg.metrics.collect_resource_metrics,
        "collect_network_metrics": cfg.metrics.collect_network_metrics,
        "sctp": cfg.metrics.sctp,
        "rach": cfg.metrics.rach,
        "pucch": cfg.metrics.pucch,
        "csr": cfg.metrics.csr,
    }

    checker = HealthChecker(
        kctl=kctl,
        site_id=cfg.site_id,
        cluster_id=cfg.cluster_id,
        env=cfg.env,
        include_details=cfg.report.include_details,
        redact_sensitive=cfg.report.redact_sensitive,
        metrics_flags=metrics_flags,
        logger=logger,
    )

    report = checker.run()
    report_dict = {
        "site_id": report.site_id,
        "cluster_id": report.cluster_id,
        "env": report.env,
        "timestamp": report.timestamp,
        "version": cfg.report.version or report.version,
        "summary": report.summary,
        "details": report.details,
    }

    publisher = KafkaPublisher(
        enabled=cfg.kafka.enabled,
        bootstrap_servers=cfg.kafka.bootstrap_servers,
        topic=cfg.kafka.topic,
        client_id=cfg.kafka.client_id,
        security_protocol=cfg.kafka.security_protocol,
        sasl_mechanism=cfg.kafka.sasl_mechanism,
        sasl_username=cfg.kafka.sasl_username,
        sasl_password=cfg.kafka.sasl_password,
        logger=logger,
    )
    published = publisher.publish(report_dict)
    publisher.close()

    logger.info(
        "healthcheck finished",
        extra={
            "site_id": cfg.site_id,
            "cluster_id": cfg.cluster_id,
            "env": cfg.env,
            "published_to_kafka": published,
            "nodes_not_ready": report.summary.get("nodes_not_ready"),
            "pods_unhealthy": report.summary.get("pods_unhealthy"),
        },
    )

    # Print report to stdout for Airflow log capture
    print(json.dumps(report_dict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
