"""Construction Materials Cost Planner - menu connecting Module 1 and Module 2."""
import os
import sys

import pandas as pd

from module1_calculator import ConcreteElement, ElementManager
from module2_analysis import (
    MATERIALS,
    load_and_clean_data,
    calculate_costs_summary,
    compare_required_vs_purchased,
    numpy_price_sensitivity_analysis,
    generate_matplotlib_charts,
    top_transactions,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")


def display_menu():
    print("\n==================================================")
    print("  CONSTRUCTION MATERIALS COST PLANNER")
    print("==================================================")
    print("1. [Module 1] Add Concrete Element")
    print("2. [Module 1] List Concrete Elements")
    print("3. [Module 1] Search Concrete Element")
    print("4. [Module 1] Update Concrete Element")
    print("5. [Module 1] Save Calculated Quantities to CSV")
    print("6. [Module 2] Load & Clean Purchase & Price Data")
    print("7. [Module 2] Compare Required vs. Purchased Quantities")
    print("8. [Module 2] Run NumPy Price Sensitivity Simulation")
    print("9. [Module 2] Export Visualizations & Reports")
    print("10. Exit")
    print("==================================================")


def out(name):
    return os.path.join(OUTPUT_DIR, name)


def elements_df(manager):
    """DataFrame of elements, or None (with a message) when there are none."""
    rows = manager.list_elements()
    if not rows:
        print("❌ No elements stored. Add elements first (option 1).")
        return None
    return pd.DataFrame(rows)


def ask_optional_float(label, current):
    """Prompt; blank keeps the current value."""
    raw = input(f"{label} [{current}]: ").strip()
    return float(raw) if raw else current


def load_data(manager):
    return load_and_clean_data(valid_element_ids=set(manager.elements))


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    manager = ElementManager()
    try:
        manager.load_from_csv()
    except Exception as e:
        print(f"❌ Could not load data/elements.csv: {e}")
        sys.exit(1)
    print(f"Loaded {len(manager)} element(s) from data/elements.csv")

    while True:
        display_menu()
        choice = input("Enter choice (1-10): ").strip()

        if choice == "1":
            try:
                eid = input("Element ID (e.g. E09): ").strip()
                name = input("Element Name: ").strip()
                site = input("Site Name: ").strip()
                l = float(input("Length (m): "))
                w = float(input("Width (m): "))
                h = float(input("Height (m): "))
                waste = float(input("Waste % (0-100): "))
                manager.add_element(ConcreteElement(eid, name, site, l, w, h, waste))
                print(f"✅ Element {eid} successfully added.")
            except Exception as e:
                print(f"❌ Error adding element: {e}")

        elif choice == "2":
            df = elements_df(manager)
            if df is not None:
                print("\n--- Current Concrete Elements ---")
                print(df.to_string(index=False))
                print("\n--- Totals per Site ---")
                print(pd.DataFrame(manager.site_summary()).to_string(index=False))

        elif choice == "3":
            eid = input("Enter Element ID to search: ").strip()
            elem = manager.get_element(eid)
            if elem:
                print("\n--- Element Details ---")
                for k, v in elem.to_dict().items():
                    print(f"  {k}: {v}")
            else:
                print(f"❌ Element '{eid}' not found.")

        elif choice == "4":
            eid = input("Enter Element ID to update: ").strip()
            elem = manager.get_element(eid)
            if not elem:
                print(f"❌ Element '{eid}' does not exist.")
                continue
            try:
                print("Press Enter to keep the current value.")
                name = input(f"New Name [{elem.name}]: ").strip() or elem.name
                site = input(f"New Site [{elem.site}]: ").strip() or elem.site
                l = ask_optional_float("New Length (m)", elem.length)
                w = ask_optional_float("New Width (m)", elem.width)
                h = ask_optional_float("New Height (m)", elem.height)
                waste = ask_optional_float("New Waste %", elem.waste_pct)
                manager.update_element(eid, name=name, site=site, length=l,
                                       width=w, height=h, waste_pct=waste)
                print(f"✅ Element '{eid}' updated successfully.")
            except Exception as e:
                print(f"❌ Update failed (nothing was changed): {e}")

        elif choice == "5":
            path = manager.save_to_csv(out("element_quantities.csv"))
            site_path = manager.save_site_summary_csv(out("site_quantities.csv"))
            if path:
                print(f"✅ Saved {path}")
                print(f"✅ Saved {site_path}")

        elif choice == "6":
            try:
                df_merged, df_prices, df_rejected = load_data(manager)
                months = sorted(df_merged["month"].unique())
                print(f"\n✅ {len(df_merged)} valid purchase records merged "
                      f"({len(df_prices)} valid prices).")
                if months:
                    print(f"   Period covered: {months[0]} to {months[-1]} ({len(months)} months)")
                print(df_merged.head().to_string(index=False))
                if df_rejected.empty:
                    print("\nNo records were rejected.")
                else:
                    print(f"\n⚠️  {len(df_rejected)} record(s) rejected:")
                    print(df_rejected.groupby("reason").size().to_string())
                    df_rejected.to_csv(out("rejected_records.csv"), index=False)
                    print("   Details saved to outputs/rejected_records.csv")
            except Exception as e:
                print(f"❌ Error during data cleaning: {e}")

        elif choice == "7":
            df_elements = elements_df(manager)
            if df_elements is None:
                continue
            try:
                df_merged, _, _ = load_data(manager)
                comp_df = compare_required_vs_purchased(df_elements, df_merged)
                print("\n--- Required vs Purchased Comparison ---")
                print(comp_df.to_string(index=False))
                comp_df.to_csv(out("quantity_comparison.csv"), index=False)
                counts = comp_df["status"].value_counts().to_dict()
                print(f"\nShortages: {counts.get('Shortage', 0)} | Surpluses: {counts.get('Surplus', 0)}")
                print("✅ Exported comparison to outputs/quantity_comparison.csv")
            except Exception as e:
                print(f"❌ Error executing comparison: {e}")

        elif choice == "8":
            df_elements = elements_df(manager)
            if df_elements is None:
                continue
            try:
                _, df_prices, _ = load_data(manager)
                mat = input(f"Material to inflate ({'/'.join(MATERIALS)}): ").strip().title()
                pct = float(input("Percentage increase (e.g. 15 for 15%): "))
                res = numpy_price_sensitivity_analysis(df_elements, df_prices, mat, pct)
                print(f"\n--- Price Sensitivity for {mat} (+{pct}%) ---")
                print("Lowest unit prices used as baseline:", res["baseline_prices"])
                print(f"Baseline Estimated Total Cost : ${res['baseline_cost']:,.2f}")
                print(f"Inflated Estimated Total Cost : ${res['inflated_cost']:,.2f}")
                print(f"Projected Cost Increase       : +${res['cost_increase']:,.2f}")
            except Exception as e:
                print(f"❌ Error running simulation: {e}")

        elif choice == "9":
            df_elements = elements_df(manager)
            if df_elements is None:
                continue
            try:
                df_merged, _, df_rejected = load_data(manager)
                calculate_costs_summary(df_merged, df_elements).to_csv(
                    out("purchase_summary.csv"), index=False)
                compare_required_vs_purchased(df_elements, df_merged).to_csv(
                    out("quantity_comparison.csv"), index=False)
                df_rejected.to_csv(out("rejected_records.csv"), index=False)
                manager.save_to_csv(out("element_quantities.csv"))
                manager.save_site_summary_csv(out("site_quantities.csv"))
                generate_matplotlib_charts(df_merged, output_dir=OUTPUT_DIR)
                print("\nTop 3 most expensive transactions:")
                print(top_transactions(df_merged, 3).to_string(index=False))
                print("\n✅ Exported CSV reports and 4 PNG charts to the outputs/ folder.")
            except Exception as e:
                print(f"❌ Error exporting outputs: {e}")

        elif choice == "10":
            print("Exiting application. Goodbye!")
            sys.exit()

        else:
            print("❌ Invalid choice. Please enter a number from 1 to 10.")


if __name__ == "__main__":
    main()
