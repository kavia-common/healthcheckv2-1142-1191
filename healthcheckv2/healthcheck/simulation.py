"""
Simulation layer providing fake Kubernetes objects and metrics for testing.
"""
from __future__ import annotations

import random
import time
from typing import Any, Dict, List, Optional, Tuple


class SimulationLayer:
    """Simple deterministic simulation with configurable failure rate."""

    def __init__(self, enabled: bool, node_count: int, pod_count: int, failure_rate: float) -> None:
        self.enabled = enabled
        self.node_count = node_count
        self.pod_count = pod_count
        self.failure_rate = max(0.0, min(1.0, failure_rate))

    def _maybe_fail(self) -> bool:
        return random.random() < self.failure_rate

    def get_nodes(self) -> List[Dict[str, Any]]:
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        items: List[Dict[str, Any]] = []
        for i in range(self.node_count):
            ready = "True"
            if self._maybe_fail():
                ready = "False"
            items.append(
                {
                    "metadata": {"name": f"node-{i}"},
                    "status": {
                        "conditions": [
                            {
                                "type": "Ready",
                                "status": ready,
                                "lastTransitionTime": now,
                            }
                        ]
                    },
                }
            )
        return items

    def get_pods(self) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for i in range(self.pod_count):
            phase = "Running"
            restarts = 0
            if self._maybe_fail():
                phase = "CrashLoopBackOff"
                restarts = 3
            items.append(
                {
                    "metadata": {"name": f"pod-{i}", "namespace": "default"},
                    "status": {
                        "phase": phase,
                        "containerStatuses": [{"name": "main", "restartCount": restarts, "ready": phase == "Running"}],
                    },
                }
            )
        return items

    def top_pods(self) -> List[Dict[str, Any]]:
        metrics: List[Dict[str, Any]] = []
        for i in range(self.pod_count):
            metrics.append(
                {
                    "namespace": "default",
                    "name": f"pod-{i}",
                    "cpu": f"{5 + i % 3}m",
                    "memory": f"{20 + i % 5}Mi",
                }
            )
        return metrics

    def exec_in_pod(self, namespace: str, pod: str, container: Optional[str], command: List[str]) -> Tuple[int, str, str]:
        # Fake network metrics collection commands and disk usage
        cmd = " ".join(command)
        if "sctp" in cmd:
            return 0, "sctp_assoc=10 sctp_errors=0", ""
        if "rach" in cmd:
            return 0, "rach_success=95 rach_total=100", ""
        if "pucch" in cmd:
            return 0, "pucch_errors=1 pucch_total=1000", ""
        if "csr" in cmd:
            return 0, "csr_latency_ms=3 csr_failures=0", ""
        if "df -h" in cmd:
            return 0, "/dev/root 50% /", ""
        # Default OK
        return 0, "ok", ""
