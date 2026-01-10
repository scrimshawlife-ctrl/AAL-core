def test_vectors_have_expected_fields():
    import json
    from pathlib import Path

    path = Path("aal_core/runes/game_theory/vectors/prison_dilemma.v1.jsonl")
    assert path.exists()
    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert row["expected"]["equilibria"][0]["profile"] == ["D", "D"]
    assert row["schema_version"] == "aal.gametheory.vector.v1"
