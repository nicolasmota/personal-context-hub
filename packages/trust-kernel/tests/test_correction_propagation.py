from pathlib import Path

from pch_core.retrieval.search import fts5_match_expr
from pch_core.service import Hub


def test_fts5_match_expr_quotes_tokens():
    assert fts5_match_expr("Atlas briefs!") == '"Atlas" AND "briefs"'
    assert fts5_match_expr("???") is None


def test_correction_propagates(hub):
    mem = hub.create("memory", {"statement": "old", "kind": "semantic", "project_id": None})
    hub.patch(mem["id"], {"statement": "new"}, if_match=1)
    results = hub.search("new")["results"]
    assert any(r["statement"] == "new" for r in results)


def test_sqlcipher_search_atlas(tmp_path: Path):
    h = Hub(tmp_path / "cipher-search", plain=False)
    h.setup("Nick")
    h.create("memory", {"statement": "Atlas prefers cited briefs", "kind": "semantic"})
    found = h.search("Atlas")["results"]
    h.close()
    assert any("Atlas" in (r.get("statement") or "") for r in found)
