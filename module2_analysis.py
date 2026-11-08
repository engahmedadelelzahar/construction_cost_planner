"""Module 2 - Purchase and Cost Analysis (pandas, NumPy, Matplotlib)."""
import os

import matplotlib
matplotlib.use("Agg")  # we only save PNG files, never open windows
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PRICES_PATH = os.path.join(BASE_DIR, "data", "prices.csv")
PURCHASES_PATH = os.path.join(BASE_DIR, "data", "purchases.csv")

# Unit each material must be priced/purchased in (keeps units consistent with Module 1)
EXPECTED_UNITS = {"Cement": "kg", "Sand": "m3", "Aggregate": "m3"}
MATERIALS = tuple(EXPECTED_UNITS)  # ("Cement", "Sand", "Aggregate")


def _norm_text(series):
    return series.astype(str).str.strip()


def load_and_clean_data(prices_path=PRICES_PATH, purchases_path=PURCHASES_PATH,
                        valid_element_ids=None):
    """Read, validate, clean and merge prices and purchases.

    Returns (df_merged, df_prices, df_rejected).
    df_rejected lists every record that was removed and why.
    If valid_element_ids (a set) is given, purchases that reference an
    unknown element ID are rejected.
    """
    rejected_parts = []

    # ---------------- prices ----------------
    prices = pd.read_csv(prices_path)
    prices["supplier_id"] = _norm_text(prices["supplier_id"])
    prices["material"] = _norm_text(prices["material"]).str.title()
    prices["unit"] = _norm_text(prices["unit"]).str.lower()
    prices["unit_price"] = pd.to_numeric(prices["unit_price"], errors="coerce")

    wrong_unit = prices["material"].map(EXPECTED_UNITS) != prices["unit"]
    p_reason = np.select(
        [prices.duplicated(["supplier_id", "material"]),
         prices["unit_price"].isna() | (prices["unit_price"] <= 0),
         wrong_unit],
        ["Duplicate supplier/material price", "Price missing or not > 0",
         "Unit inconsistent with required quantity unit"],
        default="")
    bad = prices[p_reason != ""]
    if len(bad):
        rejected_parts.append(pd.DataFrame({
            "record_type": "price",
            "record_id": bad["supplier_id"] + "/" + bad["material"],
            "reason": p_reason[p_reason != ""]}))
    df_prices = prices[p_reason == ""].reset_index(drop=True)

    # ---------------- purchases ----------------
    p = pd.read_csv(purchases_path)
    for col in ("transaction_id", "element_id", "supplier_id"):
        p[col] = _norm_text(p[col])
    p["material"] = _norm_text(p["material"]).str.title()
    p["quantity"] = pd.to_numeric(p["quantity"], errors="coerce")
    p["date"] = pd.to_datetime(p["date"], errors="coerce")

    valid_pairs = set(zip(df_prices["supplier_id"], df_prices["material"]))
    pair_missing = pd.Series(
        [(s, m) not in valid_pairs for s, m in zip(p["supplier_id"], p["material"])],
        index=p.index)
    if valid_element_ids is None:
        unknown_element = pd.Series(False, index=p.index)
    else:
        unknown_element = ~p["element_id"].isin(set(valid_element_ids))

    reasons = np.select(
        [p.duplicated("transaction_id", keep="first"),
         p["quantity"].isna(),
         p["quantity"] <= 0,
         p["date"].isna(),
         unknown_element,
         pair_missing],
        ["Duplicate transaction_id", "Missing quantity", "Quantity must be > 0",
         "Invalid date", "Unknown element_id", "No price for supplier/material"],
        default="")
    bad = p[reasons != ""]
    if len(bad):
        rejected_parts.append(pd.DataFrame({
            "record_type": "purchase",
            "record_id": bad["transaction_id"],
            "reason": reasons[reasons != ""]}))
    clean = p[reasons == ""]

    # ---------------- merge & derive ----------------
    df_merged = pd.merge(clean, df_prices, on=["supplier_id", "material"], how="inner")
    df_merged["cost"] = df_merged["quantity"] * df_merged["unit_price"]
    df_merged["month"] = df_merged["date"].dt.strftime("%Y-%m")

    df_rejected = (pd.concat(rejected_parts, ignore_index=True) if rejected_parts
                   else pd.DataFrame(columns=["record_type", "record_id", "reason"]))
    return df_merged, df_prices, df_rejected


def calculate_costs_summary(df_merged, df_elements):
    """Purchase cost ($) per site, supplier and month."""
    merged = pd.merge(df_merged, df_elements[["element_id", "site"]],
                      on="element_id", how="left")
    merged["site"] = merged["site"].fillna("Unknown")
    summary = merged.groupby(["site", "supplier_id", "month"])["cost"].sum().reset_index()
    summary["cost"] = summary["cost"].round(2)
    return summary


def compare_required_vs_purchased(df_elements, df_merged):
    """Required (Module 1) vs purchased quantity per element and material."""
    required_cols = {"Cement": "required_cement_kg",
                     "Sand": "required_sand_m3",
                     "Aggregate": "required_aggregate_m3"}
    parts = []
    for material, col in required_cols.items():
        part = df_elements[["element_id", "site", col]].rename(columns={col: "required_qty"})
        part["material"] = material
        part["unit"] = EXPECTED_UNITS[material]
        parts.append(part)
    df_req = pd.concat(parts, ignore_index=True)

    purchased = (df_merged.groupby(["element_id", "material"])["quantity"]
                 .sum().reset_index().rename(columns={"quantity": "purchased_qty"}))
    comp = pd.merge(df_req, purchased, on=["element_id", "material"], how="left")
    comp["purchased_qty"] = comp["purchased_qty"].fillna(0.0)
    comp["variance"] = (comp["purchased_qty"] - comp["required_qty"]).round(2)
    comp["status"] = np.where(comp["variance"] >= 0, "Surplus", "Shortage")
    return comp.sort_values(["element_id", "material"]).reset_index(drop=True)


def numpy_price_sensitivity_analysis(df_elements, df_prices, target_material="Cement",
                                     pct_increase=10.0):
    """Estimated cost of ALL required quantities at the lowest price per material,
    before and after raising one material's price by pct_increase %."""
    if target_material not in MATERIALS:
        raise ValueError(f"Material must be one of {MATERIALS}.")
    if pct_increase < 0:
        raise ValueError("Percentage increase must be 0 or more.")
    if df_elements.empty:
        raise ValueError("No elements available to estimate costs.")

    min_prices = df_prices.groupby("material")["unit_price"].min()
    missing = [m for m in MATERIALS if m not in min_prices.index]
    if missing:
        raise ValueError(f"No valid price available for: {missing}")

    mats = np.array(MATERIALS)
    req_totals = np.array([df_elements["required_cement_kg"].sum(),
                           df_elements["required_sand_m3"].sum(),
                           df_elements["required_aggregate_m3"].sum()])
    baseline_prices = np.array([min_prices[m] for m in MATERIALS])

    inflated_prices = baseline_prices.copy()
    inflated_prices[mats == target_material] *= (1 + pct_increase / 100.0)

    baseline_cost = float(np.dot(req_totals, baseline_prices))
    inflated_cost = float(np.dot(req_totals, inflated_prices))
    return {
        "material": target_material,
        "percentage": pct_increase,
        "baseline_prices": dict(zip(MATERIALS, baseline_prices.tolist())),
        "required_totals": dict(zip(MATERIALS, req_totals.tolist())),
        "baseline_cost": baseline_cost,
        "inflated_cost": inflated_cost,
        "cost_increase": inflated_cost - baseline_cost,
    }


def top_transactions(df_merged, n=3):
    """The n most expensive transactions (uses slicing)."""
    return df_merged.sort_values("cost", ascending=False).iloc[:n][
        ["transaction_id", "element_id", "supplier_id", "material", "quantity", "cost"]]


def generate_matplotlib_charts(df_merged, output_dir="outputs"):
    """Create four PNG charts (line, bar, scatter, histogram). Returns file paths."""
    os.makedirs(output_dir, exist_ok=True)
    plt.style.use("ggplot")
    paths = []

    def save(name):
        path = os.path.join(output_dir, name)
        plt.tight_layout()
        plt.savefig(path, dpi=300)
        plt.close()
        paths.append(path)

    # 1. Line: monthly spend
    monthly = df_merged.groupby("month")["cost"].sum().sort_index()
    plt.figure(figsize=(7, 4.5))
    plt.plot(monthly.index, monthly.values, marker="o", color="#2b5c8f", linewidth=2.5)
    plt.title("Monthly Material Expenditure ($)", fontsize=12, fontweight="bold")
    plt.xlabel("Month (YYYY-MM)")
    plt.ylabel("Total Spend ($)")
    save("chart1_monthly_spend.png")

    # 2. Bar: spend per supplier
    supplier = df_merged.groupby("supplier_id")["cost"].sum()
    colors = ["#1b9e77", "#d95f02", "#7570b3", "#e7298a"]
    plt.figure(figsize=(7, 4.5))
    plt.bar(supplier.index, supplier.values, color=colors[:len(supplier)])
    plt.title("Total Spend per Supplier ($)", fontsize=12, fontweight="bold")
    plt.xlabel("Supplier ID")
    plt.ylabel("Total Spend ($)")
    save("chart2_supplier_cost.png")

    # 3. Scatter: quantity vs cost, one series per material (units differ, so log x-axis)
    plt.figure(figsize=(7, 4.5))
    for material, colour in zip(MATERIALS, ("#7570b3", "#1b9e77", "#d95f02")):
        sub = df_merged[df_merged["material"] == material]
        if not sub.empty:
            plt.scatter(sub["quantity"], sub["cost"], c=colour, alpha=0.75,
                        edgecolors="k", s=60,
                        label=f"{material} ({EXPECTED_UNITS[material].replace('m3', 'm³')})")
    plt.xscale("log")
    plt.title("Transaction Quantity vs Cost", fontsize=12, fontweight="bold")
    plt.xlabel("Quantity (kg for cement, m³ for sand/aggregate; log scale)")
    plt.ylabel("Transaction Cost ($)")
    plt.legend()
    save("chart3_qty_vs_cost.png")

    # 4. Histogram: transaction cost ($) - one consistent unit
    plt.figure(figsize=(7, 4.5))
    plt.hist(df_merged["cost"], bins=10, color="#e7298a", edgecolor="black", alpha=0.75)
    plt.title("Distribution of Transaction Costs ($)", fontsize=12, fontweight="bold")
    plt.xlabel("Transaction Cost ($)")
    plt.ylabel("Number of Transactions")
    save("chart4_cost_distribution.png")
    return paths
