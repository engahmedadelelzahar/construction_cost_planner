"""3 valid + 4 invalid test cases. Run:  python tests.py
Results (expected vs actual) are printed and saved to outputs/test_results.csv."""
import csv
import os
import tempfile

import pandas as pd

from module1_calculator import ConcreteElement, ElementManager
from module2_analysis import load_and_clean_data, numpy_price_sensitivity_analysis

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
results = []


def record(case, kind, expected, actual, passed):
    results.append({"case": case, "type": kind, "expected": expected,
                    "actual": actual, "result": "PASS" if passed else "FAIL"})


def expect_error(case, description, func, exc=ValueError):
    try:
        func()
        record(case, "invalid", f"{exc.__name__} raised", "No error raised", False)
    except exc as e:
        record(case, "invalid", f"{exc.__name__} raised", f"{exc.__name__}: {e}", True)


manager = ElementManager()
manager.load_from_csv()
df_elements = pd.DataFrame(manager.list_elements())

# ---------------- VALID CASES ----------------
# V1: E01 = 2.5 x 2.5 x 0.6 m, 5 % waste (hand-calculated)
d = manager.get_element("E01").to_dict()
actual = (d["net_volume_m3"], d["gross_volume_m3"], d["required_cement_kg"],
          d["required_sand_m3"], d["required_aggregate_m3"])
expected = (3.75, 3.9375, 1181.25, 1.97, 3.15)
record("V1 Quantities for element E01", "valid", str(expected), str(actual), actual == expected)

# V2: cleaning removes 2 duplicate transactions + 3 missing quantities -> 35 clean, 5 rejected
merged, prices, rejected = load_and_clean_data(valid_element_ids=set(manager.elements))
record("V2 Cleaning sample purchases", "valid", "35 clean rows, 5 rejected",
       f"{len(merged)} clean rows, {len(rejected)} rejected",
       len(merged) == 35 and len(rejected) == 5)

# V3: +15 % cement; expected computed independently from the raw CSV with plain Python
with open(os.path.join(BASE_DIR, "data", "elements.csv")) as f:
    total_cement = sum(float(r["length_m"]) * float(r["width_m"]) * float(r["height_m"])
                       * (1 + float(r["waste_pct"]) / 100) * 300 for r in csv.DictReader(f))
with open(os.path.join(BASE_DIR, "data", "prices.csv")) as f:
    min_cement = min(float(r["unit_price"]) for r in csv.DictReader(f) if r["material"] == "Cement")
exp_inc = total_cement * min_cement * 0.15
res = numpy_price_sensitivity_analysis(df_elements, prices, "Cement", 15)
record("V3 Cement +15% price sensitivity", "valid", f"increase = {exp_inc:.2f} (+/-0.50)",
       f"increase = {res['cost_increase']:.2f}", abs(res["cost_increase"] - exp_inc) < 0.5)

# ---------------- INVALID CASES ----------------
expect_error("I1 Length = 0", "zero dimension",
             lambda: ConcreteElement("E50", "Test", "Site A", 0, 2, 2, 5))
expect_error("I2 Waste = 150 %", "waste out of range",
             lambda: ConcreteElement("E51", "Test", "Site A", 1, 2, 2, 150))
expect_error("I3 Duplicate element ID E01", "duplicate ID",
             lambda: manager.add_element(ConcreteElement("E01", "Copy", "Site A", 1, 1, 1, 5)))

# I4: purchase referencing unknown element E99 must be rejected
tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="")
tmp.write("transaction_id,element_id,supplier_id,material,date,quantity\n"
          "TX1,E99,S01,Cement,2026-08-01,100\n"
          "TX2,E01,S01,Cement,2026-08-01,100\n")
tmp.close()
m2, _, rej2 = load_and_clean_data(purchases_path=tmp.name, valid_element_ids=set(manager.elements))
os.unlink(tmp.name)
ok = len(m2) == 1 and list(rej2["reason"]) == ["Unknown element_id"]
record("I4 Purchase for unknown element E99", "invalid",
       "Rejected: Unknown element_id (1 valid row kept)",
       f"{len(m2)} valid row, rejected reasons: {list(rej2['reason'])}", ok)

df = pd.DataFrame(results)
os.makedirs(os.path.join(BASE_DIR, "outputs"), exist_ok=True)
df.to_csv(os.path.join(BASE_DIR, "outputs", "test_results.csv"), index=False)
pd.set_option("display.width", 200, "display.max_colwidth", 70)
print(df.to_string(index=False))
print(f"\n{(df['result'] == 'PASS').sum()}/{len(df)} tests passed")
