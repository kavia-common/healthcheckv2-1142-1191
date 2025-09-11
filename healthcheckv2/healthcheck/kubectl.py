"""
kubectl CLI interaction wrapper.

Executes kubectl commands and returns parsed outputs. Supports a simulation
layer for testing without accessing a cluster.
"""
from __future__ import annotations

import json
import shlex
import subprocess
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - only for typing
    from .simulation import SimulationLayer


class KubectlError(RuntimeError):
    """Raised when kubectl command fails."""


class KubectlClient:
    """Thin wrapper around kubectl CLI with simulation overlay."""

    def __init__(
        self,
        kubectl_path: str = "kubectl",
        context: Optional[str] = None,
        namespace: Optional[str] = None,
        extra_args: str = "",
        simulator: Optional["SimulationLayer"] = None,
    ) -> None:
        self.kubectl_path = kubectl_path
        self.context = context
        self.namespace = namespace
        self.extra_args = extra_args
        self.simulator = simulator

    def _base_cmd(self) -> List[str]:
        cmd = [self.kubectl_path]
        if self.context:
            cmd.extend(["--context", self.context])
        if self.namespace:
            cmd.extend(["-n", self.namespace])
        if self.extra_args:
            cmd.extend(shlex.split(self.extra_args))
        return cmd

    def _exec(self, args: List[str]) -> Tuple[int, str, str]:
        """Execute real kubectl command securely."""
        full_cmd = self._base_cmd() + args
        try:
            proc = subprocess.run(
                full_cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
        except subprocess.TimeoutExpired as exc:
            raise KubectlError(f"kubectl timed out: {exc}") from exc

    # PUBLIC_INTERFACE
    def get_nodes(self) -> List[Dict[str, Any]]:
        """Return node list via 'kubectl get nodes -o json'."""
        if self.simulator and self.simulator.enabled:
            return self.simulator.get_nodes()
        code, out, err = self._exec(["get", "nodes", "-o", "json"])
        if code != 0:
            raise KubectlError(f"kubectl get nodes failed: {err}")
        data = json.loads(out or "{}")
        return data.get("items", [])

    # PUBLIC_INTERFACE
    def get_pods(self) -> List[Dict[str, Any]]:
        """Return pods via 'kubectl get pods -A -o json'."""
        if self.simulator and self.simulator.enabled:
            return self.simulator.get_pods()
        code, out, err = self._exec(["get", "pods", "-A", "-o", "json"])
        if code != 0:
            raise KubectlError(f"kubectl get pods failed: {err}")
        data = json.loads(out or "{}")
        return data.get("items", [])

    # PUBLIC_INTERFACE
    def top_pods(self) -> List[Dict[str, Any]]:
        """Return top pods resource metrics if metrics-server present.

        Uses `kubectl top pods --no-headers -A` and parses table output.
        """
        if self.simulator and self.simulator.enabled:
            return self.simulator.top_pods()
        code, out, err = self._exec(["top", "pods", "--no-headers", "-A"])
        if code != 0:
            # If top not available, return empty for graceful degradation
            return []
        metrics: List[Dict[str, Any]] = []
        for line in out.splitlines():
            # NAMESPACE NAME CPU(m) MEM(Mi)
            parts = line.split()
            if len(parts) >= 4:
                metrics.append(
                    {
                        "namespace": parts[0],
                        "name": parts[1],
                        "cpu": parts[2],  # e.g., 5m
                        "memory": parts[3],  # e.g., 20Mi
                    }
                )
        return metrics

    # PUBLIC_INTERFACE
    def exec_in_pod(self, namespace: str, pod: str, container: Optional[str], command: List[str]) -> Tuple[int, str, str]:
        """Execute a command inside a pod using kubectl exec.

        Args:
            namespace: Pod namespace.
            pod: Pod name.
            container: Optional container name.
            command: Command list to run inside the pod.

        Returns:
            Tuple of (return code, stdout, stderr).
        """
        if self.simulator and self.simulator.enabled:
            return self.simulator.exec_in_pod(namespace, pod, container, command)

        args = ["exec", "-n", namespace, pod]
        if container:
            args.extend(["-c", container])
        args.extend(["--"] + command)
        return self._exec(args)
