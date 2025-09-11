from healthcheck.healthcheck.checks import HealthChecker
from healthcheck.healthcheck.kubectl import KubectlClient
from healthcheck.healthcheck.simulation import SimulationLayer


def make_checker(sim_failure_rate=0.0, include_details=True, redact=True, metrics_flags=None):  # noqa: ANN001
    sim = SimulationLayer(enabled=True, node_count=3, pod_count=4, failure_rate=sim_failure_rate)
    k = KubectlClient(simulator=sim)
    flags = metrics_flags or {
        "collect_resource_metrics": True,
        "collect_network_metrics": True,
        "sctp": True,
        "rach": True,
        "pucch": True,
        "csr": True,
    }
    return HealthChecker(
        kctl=k,
        site_id="s1",
        cluster_id="c1",
        env="dev",
        include_details=include_details,
        redact_sensitive=redact,
        metrics_flags=flags,
        logger=None,
    )


def test_health_report_success_default():
    checker = make_checker(0.0)
    report = checker.run()
    assert report.site_id == "s1"
    assert report.summary["nodes_total"] == 3
    assert "resource_metrics_enabled" in report.summary
    assert "network_metrics_enabled" in report.summary
    assert report.details is not None


def test_health_report_with_failures():
    checker = make_checker(1.0)  # force failures
    report = checker.run()
    assert report.summary["nodes_not_ready"] >= 1
    assert report.summary["pods_unhealthy"] >= 1


def test_health_report_no_details_no_metrics():
    checker = make_checker(0.0, include_details=False, metrics_flags={"collect_resource_metrics": False, "collect_network_metrics": False})
    report = checker.run()
    assert report.details is None
    assert report.summary["resource_metrics_enabled"] is False
    assert report.summary["network_metrics_enabled"] is False
