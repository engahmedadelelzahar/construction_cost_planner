import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def load_and_clean_data(prices_path="data/prices.csv", purchases_path="data/purchases.csv"):
    """Reads, cleans missing values/duplicates, and merges prices & purchases datasets."""
    df_prices = pd.read_csv(prices_path)
    df_purchases = pd.read_csv(purchases_path)

    # 1. Input Validation: prices & quantities > 0
    df_prices = df_prices[df_prices["unit_price"] > 0]
    
    # 2. Drop duplicate transactions and handle missing quantity values
    df_purchases_clean = df_purchases.drop_duplicates(subset=["transaction_id"]).dropna(subset=["quantity"])
    df_purchases_clean = df_purchases_clean[df_purchases_clean["quantity"] > 0]

    # 3. Merge data using IDs
    df_merged = pd.merge(df_purchases_clean, df_prices, on=["supplier_id", "material"], how="inner")
    
    # 4. Calculate cost per transaction and month column
    df_merged["cost"] = df_merged["quantity"] * df_merged["unit_price"]
    df_merged["date"] = pd.to_datetime(df_merged["date"])
    df_merged["month"] = df_merged["date"].dt.strftime("%Y-%m")

    return df_merged, df_prices

def calculate_costs_summary(df_merged, df_elements):
    """Calculates purchase costs per site, supplier, and month."""
    merged_site = pd.merge(df_merged, df_elements[["element_id", "site"]], on="element_id", how="left")
    summary = merged_site.groupby(["site", "supplier_id", "month"])["cost"].sum().reset_index()
    return summary

def compare_required_vs_purchased(df_elements, df_merged):
    """Compares required and purchased quantities per element and material."""
    # Prepare required quantities from Module 1
    req_cement = df_elements[["element_id", "required_cement_kg"]].rename(columns={"required_cement_kg": "required_qty"})
    req_cement["material"] = "Cement"
    req_cement["unit"] = "kg"

    req_sand = df_elements[["element_id", "required_sand_m3"]].rename(columns={"required_sand_m3": "required_qty"})
    req_sand["material"] = "Sand"
    req_sand["unit"] = "m3"

    req_agg = df_elements[["element_id", "required_aggregate_m3"]].rename(columns={"required_aggregate_m3": "required_qty"})
    req_agg["material"] = "Aggregate"
    req_agg["unit"] = "m3"

    df_req = pd.concat([req_cement, req_sand, req_agg], ignore_index=True)

    # Sum purchased quantities by element and material
    df_purchased_sum = df_merged.groupby(["element_id", "material"])["quantity"].sum().reset_index()
    df_purchased_sum.rename(columns={"quantity": "purchased_qty"}, inplace=True)

    # Merge required and purchased data
    comp_df = pd.merge(df_req, df_purchased_sum, on=["element_id", "material"], how="left").fillna({"purchased_qty": 0})
    comp_df["variance"] = comp_df["purchased_qty"] - comp_df["required_qty"]
    comp_df["status"] = np.where(comp_df["variance"] >= 0, "Surplus", "Shortage")

    return comp_df

def numpy_price_sensitivity_analysis(df_elements, df_prices, target_material="Cement", pct_increase=10.0):
    """Uses NumPy to compute baseline vs price-inflated estimated costs using lowest price baseline."""
    # Baseline lowest prices per material
    min_prices = df_prices.groupby("material")["unit_price"].min().to_dict()

    mats = np.array(["Cement", "Sand", "Aggregate"])
    
    # Required total sums
    req_totals = np.array([
        df_elements["required_cement_kg"].sum(),
        df_elements["required_sand_m3"].sum(),
        df_elements["required_aggregate_m3"].sum()
    ])

    baseline_prices = np.array([min_prices["Cement"], min_prices["Sand"], min_prices["Aggregate"]])

    # Apply price shock
    inflated_prices = baseline_prices.copy()
    idx = np.where(mats == target_material)[0][0]
    inflated_prices[idx] *= (1 + pct_increase / 100.0)

    # Calculate estimated totals using NumPy dot products
    baseline_cost = np.dot(req_totals, baseline_prices)
    inflated_cost = np.dot(req_totals, inflated_prices)
    diff = inflated_cost - baseline_cost

    return {
        "material": target_material,
        "percentage": pct_increase,
        "baseline_cost": float(baseline_cost),
        "inflated_cost": float(inflated_cost),
        "cost_increase": float(diff)
    }

def generate_matplotlib_charts(df_merged, output_dir="outputs"):
    """Generates four Matplotlib charts with explicit titles and units."""
    os.makedirs(output_dir, exist_ok=True)
    plt.style.use("ggplot")

    # 1. Line Chart: Monthly Purchasing Spend
    plt.figure(figsize=(7, 4.5))
    monthly_spend = df_merged.groupby("month")["cost"].sum().reset_index()
    plt.plot(monthly_spend["month"], monthly_spend["cost"], marker="o", color="#2b5c8f", linewidth=2.5)
    plt.title("Monthly Material Expenditure ($)", fontsize=12, fontweight="bold")
    plt.xlabel("Month (YYYY-MM)")
    plt.ylabel("Total Spend ($)")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "chart1_monthly_spend.png"), dpi=300)
    plt.close()

    # 2. Bar Chart: Total Expenditure per Supplier
    plt.figure(figsize=(7, 4.5))
    supplier_spend = df_merged.groupby("supplier_id")["cost"].sum().reset_index()
    plt.bar(supplier_spend["supplier_id"], supplier_spend["cost"], color=["#1b9e77", "#d95f02"])
    plt.title("Total Spend per Supplier ($)", fontsize=12, fontweight="bold")
    plt.xlabel("Supplier ID")
    plt.ylabel("Total Spend ($)")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "chart2_supplier_cost.png"), dpi=300)
    plt.close()

    # 3. Scatter Plot: Quantity vs. Transaction Cost
    plt.figure(figsize=(7, 4.5))
    plt.scatter(df_merged["quantity"], df_merged["cost"], c="#7570b3", alpha=0.7, edgecolors="k", s=60)
    plt.title("Transaction Quantity vs Cost ($)", fontsize=12, fontweight="bold")
    plt.xlabel("Transaction Quantity (Units)")
    plt.ylabel("Transaction Cost ($)")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "chart3_qty_vs_cost.png"), dpi=300)
    plt.close()

    # 4. Histogram: Distribution of Transaction Quantities
    plt.figure(figsize=(7, 4.5))
    plt.hist(df_merged["quantity"], bins=10, color="#e7298a", edgecolor="black", alpha=0.75)
    plt.title("Distribution of Transaction Quantities", fontsize=12, fontweight="bold")
    plt.xlabel("Purchase Quantity Range")
    plt.ylabel("Frequency (Count)")
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "chart4_purchase_dist.png"), dpi=300)
    plt.close()