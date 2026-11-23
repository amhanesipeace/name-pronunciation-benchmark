"""Unit tests for the cross-engine consensus difficulty analysis.

All synthetic: a few names across a few toy "engines", so the ranking logic is
checked without the committed data.
"""
import hardest_names as hn


def _row(nid, name, language, cer):
    return {"id": nid, "name": name, "language": language, "cer": cer}


def test_percentile_ranks_easiest_is_zero_hardest_is_one():
    rows = [_row("a", "A", "english", 0.0), _row("b", "B", "yoruba", 0.3),
            _row("c", "C", "igbo", 0.9)]
    pr = hn.percentile_ranks(rows)
    assert pr["a"] == 0.0 and pr["c"] == 1.0
    assert 0.0 < pr["b"] < 1.0


def test_percentile_ranks_ties_share_value():
    rows = [_row("a", "A", "english", 0.0), _row("b", "B", "english", 0.0),
            _row("c", "C", "yoruba", 0.5)]
    pr = hn.percentile_ranks(rows)
    assert pr["a"] == pr["b"] == 0.0          # both have nothing lower


def _engine(cers):
    # cers: {id: (name, language, cer)}
    return [_row(nid, nm, lg, c) for nid, (nm, lg, c) in cers.items()]


def test_consensus_ranks_broadly_hard_name_first_and_drops_english():
    # "Hard" is hard everywhere; "Mixed" spikes in one engine only; English easy.
    e1 = _engine({"h": ("Hard", "igbo", 0.9), "m": ("Mixed", "hausa", 0.8),
                  "x": ("Xavier", "english", 0.0), "e": ("Easy", "yoruba", 0.1)})
    e2 = _engine({"h": ("Hard", "igbo", 0.9), "m": ("Mixed", "hausa", 0.0),
                  "x": ("Xavier", "english", 0.0), "e": ("Easy", "yoruba", 0.1)})
    ranked = hn.consensus({"e1": e1, "e2": e2})
    assert all(r["language"] != "english" for r in ranked)   # English dropped
    assert ranked[0]["name"] == "Hard"                       # hard in both -> top
    assert ranked[0]["hard_in"] == 2


def test_summarise_counts_and_group_means():
    e1 = _engine({"h": ("Hard", "igbo", 0.9), "m": ("Mid", "hausa", 0.5),
                  "x": ("Xa", "english", 0.0), "e": ("Ez", "yoruba", 0.1)})
    e2 = _engine({"h": ("Hard", "igbo", 0.9), "m": ("Mid", "hausa", 0.5),
                  "x": ("Xa", "english", 0.0), "e": ("Ez", "yoruba", 0.1)})
    s = hn.summarise({"e1": e1, "e2": e2})
    assert s["n_african"] == 3                       # Hard, Mid, Ez
    assert s["african_mean"] > s["english_mean"]     # African ranks harder
    assert s["hard_in_all"] == 1                      # only Hard clears 0.67 in all
    assert "Hard" in s["ranked"][0]["name"]


def test_report_mentions_consensus_and_table():
    e1 = _engine({"h": ("Hard", "igbo", 0.9), "x": ("Xa", "english", 0.0),
                  "e": ("Ez", "yoruba", 0.1)})
    text = hn.report({"e1": e1, "e2": e1})
    assert "cross-engine consensus" in text
    assert "| Name | Language | Consensus |" in text
    assert "Hard" in text
