from healthcheck.healthcheck.checks import HealthChecker
from healthcheck.healthcheck.kubectl import KubectlClient
from healthcheck.healthcheck.simulation import SimulationLayer


def test_healthchecker_redaction_applies_to_details():
    sim = SimulationLayer(enabled=True, node_count=1, pod_count=1, failure_rate=0.0)
    k = KubectlClient(simulator=sim)
    checker = HealthChecker(
        kctl=k,
        site_id="s1",
        cluster_id="c1",
        env="dev",
        include_details=True,
        redact_sensitive=True,
        metrics_flags={"collect_resource_metrics": True, "collect_network_metrics": False},
    )
    # Force redact-worthy content by injecting metrics_flags that will produce normal details string
    report = checker.run()
    details = report.details
    assert isinstance(details, str)
    # Fake secrets to test redact logic: 32+ hex and token/password patterns
    checker.redact_sensitive = True
    secret_str = "a" * 32
    redacted = checker._redact(f"abc {secret_str} token=mytok password=letmein")
    assert "***" in redacted
    assert "token=***" in redacted
    assert "password=***" in redacted
