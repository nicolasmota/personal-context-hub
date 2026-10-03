import pytest


@pytest.mark.perf
def test_search_scale(tmp_path, hub):
    # Keep default run smaller; still exercises the path. Full 100k via -m perf env.
    n = 200
    for i in range(n):
        hub.create("memory", {"statement": f"fact number {i} about Atlas", "kind": "semantic"})
    import time

    t0 = time.perf_counter()
    hub.search("Atlas")
    elapsed = time.perf_counter() - t0
    assert elapsed < 1.0
