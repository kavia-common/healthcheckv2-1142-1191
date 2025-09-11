from healthcheck.healthcheck.simulation import SimulationLayer


def test_simulation_generates_expected_counts():
    sim = SimulationLayer(enabled=True, node_count=5, pod_count=7, failure_rate=0.0)
    nodes = sim.get_nodes()
    pods = sim.get_pods()
    top = sim.top_pods()
    assert len(nodes) == 5
    assert len(pods) == 7
    assert len(top) == 7
    # exec behavior default ok
    code, out, err = sim.exec_in_pod("default", "pod-1", None, ["sh", "-c", "df -h"])
    assert code == 0
    assert "50%" in out
