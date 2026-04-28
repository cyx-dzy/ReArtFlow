import random
import string
from backend.diagram.converter import json_to_mermaid


def generate_random_graph(num_nodes: int, num_edges: int):
    """Generate a random dependency graph with the given number of nodes and edges.
    Each node has an ``id`` and a ``label``. Edges reference node ``id`` values.
    """
    nodes = [{"id": f"node{i}", "label": f"Node {i}"} for i in range(num_nodes)]
    edges = []
    for _ in range(num_edges):
        src = f"node{random.randint(0, num_nodes - 1)}"
        dst = f"node{random.randint(0, num_nodes - 1)}"
        edges.append({"source": src, "target": dst})
    return {"nodes": nodes, "edges": edges}


def test_json_to_mermaid_performance(benchmark):
    """Benchmark json_to_mermaid on a large random graph.

    The test asserts that the conversion completes in under 2 seconds.
    """
    num_nodes = 10_000
    num_edges = 10_000
    data = generate_random_graph(num_nodes, num_edges)

    # Run the benchmark
    result = benchmark(json_to_mermaid, data)
    # Ensure a result is produced (non‑empty string)
    assert isinstance(result, str) and len(result) > 0
    # Verify performance: mean execution time less than 2 seconds
    assert benchmark.stats.mean < 2.0
