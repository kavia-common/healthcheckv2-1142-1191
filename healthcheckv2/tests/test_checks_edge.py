from healthcheck.healthcheck.checks import HealthChecker
from healthcheck.healthcheck.kubectl import KubectlClient
from healthcheck.healthcheck.simulation import SimulationLayer


class FailingExecSim(SimulationLayer):
    def exec_in_pod(self, namespace, pod, container, command):  # noqa: ANN001
        # Force a non-zero return code to exercise error branch
        return 2, "", "boom"


def test_network_metrics_for_pod_error_and_parsing():
    # Use normal sim to cover parsing of key=value into ints/floats
    sim = SimulationLayer(enabled=True, node_count=1, pod_count=1, failure_rate=0.0)
    k = KubectlClient(simulator=sim)
    hc = HealthChecker(
        kctl=k,
        site_id="s",
        cluster_id="c",
        env="dev",
        include_details=False,
        redact_sensitive=False,
        metrics_flags={"collect_network_metrics": True, "sctp": True, "rach": True, "pucch": True, "csr": True},
    )
    parsed = hc._network_metrics_for_pod("default", "pod-0")
    # From SimulationLayer, parsing should have converted numeric types when possible
    assert parsed["rach"]["rach_total"] == 100
    assert parsed["csr"]["csr_latency_ms"] == 3
    assert parsed["pucch"]["pucch_errors"] == 1

    # Now use failing sim to hit error branch
    sim_fail = FailingExecSim(enabled=True, node_count=1, pod_count=1, failure_rate=0.0)
    k_fail = KubectlClient(simulator=sim_fail)
    hc_fail = HealthChecker(
        kctl=k_fail,
        site_id="s",
        cluster_id="c",
        env="dev",
        include_details=False,
        redact_sensitive=False,
        metrics_flags={"collect_network_metrics": True, "sctp": True, "rach": True, "pucch": True, "csr": True},
    )
    results = hc_fail._network_metrics_for_pod("default", "pod-0")
    # All enabled probes should record error
    assert all(v.get("error") for v in results.values())
