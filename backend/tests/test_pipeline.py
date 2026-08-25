"""End-to-end tests proving the pipeline runs on a real-schema fixture and that
nothing is hardcoded: outputs are derived from the fixture's actual records."""
import os, json, pandas as pd, pytest
from drishti.mapping import detect_mapping, apply_mapping
from drishti.validation import clean_and_validate
from drishti.engine import run_engine

FIX = os.path.join(os.path.dirname(__file__), "fixtures", "esakshi_sample.csv")

@pytest.fixture(scope="module")
def clean():
    raw = pd.read_csv(FIX, dtype=str)
    m = detect_mapping(list(raw.columns))
    mapped = apply_mapping(raw, m)
    c, q = clean_and_validate(mapped)
    return c, q, m

def test_mapping_finds_required(clean):
    _, _, m = clean
    assert m["work_id"] == "Work Id"
    assert m["sanctioned_amount"] == "Sanctioned Amount (in Rs.)"
    assert m["size"] is None  # fixture has no size -> must NOT be fabricated

def test_validation_report(clean):
    c, q, _ = clean
    assert q["received"] == 452 and q["accepted"] > 400
    assert q["has_size"] is False           # honest: size absent
    assert q["has_status_labels"]["completed"] > 30

def test_engine_outputs_from_real_ids(clean):
    c, q, _ = clean
    res = run_engine(c)
    ids_in = set(c["work_id"])
    ids_out = {w["id"] for w in res["queue"]}
    assert ids_out and ids_out.issubset(ids_in)     # every flagged id is a real fixture id
    assert res["model_runs"]["expected_cost"]["confidence"] == "reduced"  # no size -> reduced
    # delivery-risk either trained on real labels or honestly reported unavailable
    dr = res["model_runs"]["delivery_risk"]
    assert ("auc" in dr) or ("reason" in dr and "Insufficient" in dr["reason"])

def test_duplicate_pair_detected(clean):
    c, _, _ = clean
    res = run_engine(c)
    dup_ids = {w["id"] for w in res["duplicates"]}
    assert "MP-WB-DUPA" in dup_ids and "MP-WB-DUPB" in dup_ids

def test_no_fabricated_metric_without_data():
    # tiny df -> models must decline, not invent numbers
    df = pd.DataFrame({"work_id":[f"W{i}" for i in range(5)],
                       "sanctioned_amount":[100000]*5,"work_type":["road"]*5,"district":["A"]*5,"year":[2023]*5})
    res = run_engine(df)
    assert res["model_runs"]["expected_cost"]["available"] is False
    assert res["model_runs"]["delivery_risk"]["available"] is False
