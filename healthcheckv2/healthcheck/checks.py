"""
Health checks: node readiness, pod/container health, resource metrics, network metrics,
and report generation.
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .kubectl import KubectlClient


@dataclass
class HealthReport:
    """Aggregated health report."""

    site_id: str
    cluster_id: str
    env: str
    timestamp: float
    summary: Dict[str, Any]
    details: Optional[Dict[str, Any]] = None
    version: str = "1.0.0"


class HealthChecker:
    """Runs health checks using kubectl client and returns HealthReport."""

    def __init__(
        self,
        kctl: KubectlClient,
        site_id: str,
        cluster_id: str,
        env: str,
        include_details: bool = True,
        redact_sensitive: bool = True,
        metrics_flags: Optional[Dict[str, bool]] = None,
        logger=None,
    ) -> None:
        self.kctl = kctl
        self.site_id = site_id
        self.cluster_id = cluster_id
        self.env = env
        self.include_details = include_details
        self.redact_sensitive = redact_sensitive
        self.metrics_flags = metrics_flags or {}
        self.logger = logger

    def _redact(self, value: Any) -> Any:
        if not self.redact_sensitive:
            return value
        if isinstance(value, str):
            # Mask tokens, passwords, and uuid-like patterns
            value = re.sub(r"([A-Fa-f0-9]{32,})", "***", value)
            value = re.sub(r"(password|token)=([^ ]+)", r"\1=***", value, flags=re.IGNORECASE)
        return value

    def _node_readiness(self) -> Dict[str, Any]:
        nodes = self.kctl.get_nodes()
        not_ready = []
        for node in nodes:
            name = node.get("metadata", {}).get("name")
            conds = node.get("status", {}).get("conditions", [])
            ready_state = next((c.get("status") for c in conds if c.get("type") == "Ready"), "Unknown")
            if ready_state != "True":
                not_ready.append(name)
        return {"total": len(nodes), "not_ready": not_ready}

    def _pods_health(self) -> Dict[str, Any]:
        pods = self.kctl.get_pods()
        bad_pods = []
        restarts_total = 0
        for pod in pods:
            name = pod.get("metadata", {}).get("name")
            ns = pod.get("metadata", {}).get("namespace")
            phase = pod.get("status", {}).get("phase")
            statuses = pod.get("status", {}).get("containerStatuses", []) or []
            restarts = sum(int(s.get("restartCount", 0)) for s in statuses)
            restarts_total += restarts
            if phase not in ("Running", "Succeeded"):
                bad_pods.append({"namespace": ns, "name": name, "phase": phase, "restarts": restarts})
        return {"total": len(pods), "restarts_total": restarts_total, "unhealthy": bad_pods}

    def _resource_metrics(self) -> Dict[str, Any]:
        if not self.metrics_flags.get("collect_resource_metrics", True):
            return {"enabled": False}
        top = self.kctl.top_pods()
        # Simple aggregation: count & sample
        return {"enabled": True, "count": len(top), "sample": top[:5]}

    def _network_metrics_for_pod(self, ns: str, name: str) -> Dict[str, Any]:
        results: Dict[str, Any] = {}
        # These commands are placeholders; in real usage they would map to vendor binaries
        probes = {
            "sctp": ["sh", "-c", "echo sctp metrics && echo sctp"],
            "rach": ["sh", "-c", "echo rach metrics && echo rach"],
            "pucch": ["sh", "-c", "echo pucch metrics && echo pucch"],
            "csr": ["sh", "-c", "echo csr metrics && echo csr"],
        }
        for key, cmd in probes.items():
            if not self.metrics_flags.get(key, True):
                continue
            code, out, _ = self.kctl.exec_in_pod(ns, name, None, cmd)
            if code == 0:
                # For simulation we parse 'key=value' pairs if present
                parsed: Dict[str, Any] = {}
                for token in out.split():
                    if "=" in token:
                        k, v = token.split("=", 1)
                        with_val: Any = v
                        if v.isdigit():
                            with_val = int(v)
                        else:
                            try:
                                with_val = float(v)
                            except ValueError:
                                with_val = v
                        parsed[k] = with_val
                results[key] = parsed or {"status": "ok"}
            else:
                results[key] = {"error": f"exec failed: {code}"}
        return results

    def _network_metrics(self) -> Dict[str, Any]:
        if not self.metrics_flags.get("collect_network_metrics", True):
            return {"enabled": False}
        pods = self.kctl.get_pods()
        sampled = pods[:3]  # sample first few for performance
        data = []
        for pod in sampled:
            ns = pod.get("metadata", {}).get("namespace", "default")
            name = pod.get("metadata", {}).get("name", "")
            data.append({"namespace": ns, "name": name, "metrics": self._network_metrics_for_pod(ns, name)})
        return {"enabled": True, "sampled_count": len(sampled), "details": data}

    # PUBLIC_INTERFACE
    def run(self) -> HealthReport:
        """Run all health checks and return a structured report."""
        started = time.time()
        nodes = self._node_readiness()
        pods = self._pods_health()
        res_metrics = self._resource_metrics()
        net_metrics = self._network_metrics()
        summary = {
            "nodes_total": nodes["total"],
            "nodes_not_ready": len(nodes["not_ready"]),
            "pods_total": pods["total"],
            "pods_unhealthy": len(pods["unhealthy"]),
            "restarts_total": pods["restarts_total"],
            "resource_metrics_enabled": bool(res_metrics.get("enabled", True)),
            "network_metrics_enabled": bool(net_metrics.get("enabled", True)),
            "duration_ms": int((time.time() - started) * 1000),
        }
        details = None
        if self.include_details:
            details = {
                "nodes": nodes,
                "pods": pods,
                "resource_metrics": res_metrics,
                "network_metrics": net_metrics,
            }
            if self.redact_sensitive:
                details = self._redact(str(details))  # simple string redaction
        return HealthReport(
            site_id=self.site_id,
            cluster_id=self.cluster_id,
            env=self.env,
            timestamp=time.time(),
            summary=summary,
            details=details,
        )
