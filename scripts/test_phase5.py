"""Phase 5 integration test suite"""
import requests, json, sys

BASE = "http://localhost:8000"
PASS, FAIL = 0, 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  PASS  {name}")
    else:
        FAIL += 1
        print(f"  FAIL  {name}  {detail}")

print("\n" + "="*60)
print("Phase 5 — End-to-End Integration Tests")
print("="*60)

# ── Test 1: Health ────────────────────────────────────────────
print("\n[1] GET /health")
r = requests.get(f"{BASE}/health")
d = r.json()
print("   ", d)
check("status=ok", d.get("status") == "ok")
check("real_model_loaded=True", d.get("real_model_loaded") is True)

# ── Test 2: Model info ────────────────────────────────────────
print("\n[2] GET /model-info")
r = requests.get(f"{BASE}/model-info")
info = r.json()
check("HTTP 200", r.status_code == 200)
check("real_model_loaded", info.get("real_model_loaded") is True)
check("n_estimators=100", info.get("n_estimators") == 100)
trained = info.get("training_data", {}).get("regions_trained", [])
check("3 trained regions listed", len(trained) == 3, str(trained))
check("Day-1 only validated", "Day 1" in str(info.get("training_data",{}).get("lead_day_validated","")))
skill = info.get("skill_scores") or {}
bss = skill.get("brier_skill_score", 0)
check("BSS > 0 (beats baseline)", bss > 0, f"BSS={bss}")
check("ROC-AUC > 0.85", skill.get("roc_auc_model", 0) > 0.85)
print(f"    BSS={bss}  ROC-AUC={skill.get('roc_auc_model')}")

# ── Test 3: Real prediction, trained region, Day 1 ────────────
print("\n[3] GET /forecast-confidence?region=coastal-karnataka&date=2023-08-10&lead_day=1")
r = requests.get(f"{BASE}/forecast-confidence",
                 params={"region": "coastal-karnataka", "date": "2023-08-10", "lead_day": 1})
d = r.json()
print("    bust_probability:", d.get("bust_probability"))
print("    is_mock:         ", d.get("is_mock"))
print("    confidence_label:", d.get("confidence_label"))
check("HTTP 200", r.status_code == 200)
check("is_mock=False (trained region+Day1)", d.get("is_mock") is False, str(d.get("is_mock")))
check("bust_probability in [0,1]", 0 <= d.get("bust_probability", -1) <= 1)
check("top_factors present", bool(d.get("top_factors")))

# ── Test 4: Demo region ───────────────────────────────────────
print("\n[4] GET /forecast-confidence?region=konkan-goa&date=2023-08-10&lead_day=1")
r = requests.get(f"{BASE}/forecast-confidence",
                 params={"region": "konkan-goa", "date": "2023-08-10", "lead_day": 1})
d = r.json()
print("    bust_probability:", d.get("bust_probability"))
print("    is_mock:         ", d.get("is_mock"))
check("HTTP 200", r.status_code == 200)
check("bust_probability in [0,1]", 0 <= d.get("bust_probability", -1) <= 1)

# ── Test 5: 10-Day outlook — is_mock flags ────────────────────
print("\n[5] GET /10day-outlook?region=coastal-karnataka&date=2023-08-10")
r = requests.get(f"{BASE}/10day-outlook",
                 params={"region": "coastal-karnataka", "date": "2023-08-10"})
d = r.json()
check("HTTP 200", r.status_code == 200)
outlook = d.get("outlook", [])
check("10 days returned", len(outlook) == 10, f"got {len(outlook)}")
day1 = next((x for x in outlook if x["lead_day"] == 1), None)
day5 = next((x for x in outlook if x["lead_day"] == 5), None)
if day1:
    check("Day 1 is_mock=False", day1.get("is_mock") is False, str(day1.get("is_mock")))
    print(f"    Day 1 bust={day1['bust_probability']}  is_mock={day1['is_mock']}")
if day5:
    check("Day 5 is_mock=True", day5.get("is_mock") is True, str(day5.get("is_mock")))
    print(f"    Day 5 bust={day5['bust_probability']}  is_mock={day5['is_mock']}")

# ── Test 6: Confidence map ────────────────────────────────────
print("\n[6] GET /confidence-map/2023-08-10?lead_day=1")
r = requests.get(f"{BASE}/confidence-map/2023-08-10", params={"lead_day": 1})
d = r.json()
check("HTTP 200", r.status_code == 200)
regions = d.get("regions", [])
check("Multiple regions returned", len(regions) >= 3, f"got {len(regions)}")
for reg in regions:
    trained_flag = "TRAINED" if not reg.get("is_mock") else "demo"
    print(f"    {reg['region']:30s} bust={reg['bust_probability']}  [{trained_flag}]")

# ── Summary ───────────────────────────────────────────────────
print("\n" + "="*60)
print(f"Results: {PASS} passed, {FAIL} failed")
print("="*60)
sys.exit(0 if FAIL == 0 else 1)
