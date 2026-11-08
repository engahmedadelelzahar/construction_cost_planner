import sys
import pandas as pd
from module1_calculator import ConcreteElement, ElementManager
from module2_analysis import (
    load_and_clean_data,
    calculate_costs_summary,
    compare_required_vs_purchased,
    numpy_price_sensitivity_analysis,
    generate_matplotlib_charts
)

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

def main():
    manager = ElementManager()
    manager.load_from_csv()

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
                elem = ConcreteElement(eid, name, site, l, w, h, waste)
                manager.add_element(elem)
                print(f"✅ Element {eid} successfully added.")
            except Exception as e:
                print(f"❌ Error adding element: {e}")

        elif choice == "2":
            elements = manager.list_elements()
            if not elements:
                print("No elements currently stored.")
            else:
                df = pd.DataFrame(elements)
                print("\n--- Current Concrete Elements ---")
                print(df.to_string(index=False))

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
            if not manager.get_element(eid):
                print(f"❌ Element '{eid}' does not exist.")
                continue
            try:
                l = float(input("New Length (m): "))
                w = float(input("New Width (m): "))
                h = float(input("New Height (m): "))
                waste = float(input("New Waste %: "))
                manager.update_element(eid, length=l, width=w, height=h, waste_pct=waste)
                print(f"✅ Element '{eid}' updated successfully.")
            except Exception as e:
                print(f"❌ Update failed: {e}")

        elif choice == "5":
            manager.save_to_csv("outputs/element_quantities.csv")

        elif choice == "6":
            try:
                df_merged, df_prices = load_and_clean_data()
                print("\n✅ Purchases Data Cleaned and Merged Successfully.")
                print(df_merged.head())
            except Exception as e:
                print(f"❌ Error during data cleaning: {e}")

        elif choice == "7":
            try:
                df_elements = pd.DataFrame(manager.list_elements())
                df_merged, _ = load_and_clean_data()
                comp_df = compare_required_vs_purchased(df_elements, df_merged)
                print("\n--- Required vs Purchased Comparison ---")
                print(comp_df.to_string(index=False))
                comp_df.to_csv("outputs/quantity_comparison.csv", index=False)
                print("✅ Exported comparison to outputs/quantity_comparison.csv")
            except Exception as e:
                print(f"❌ Error executing comparison: {e}")

        elif choice == "8":
            try:
                df_elements = pd.DataFrame(manager.list_elements())
                _, df_prices = load_and_clean_data()
                mat = input("Enter Material to inflate (Cement/Sand/Aggregate): ").strip().capitalize()
                pct = float(input("Enter percentage increase (e.g. 15 for 15%): "))
                res = numpy_price_sensitivity_analysis(df_elements, df_prices, mat, pct)
                print(f"\n--- Price Sensitivity Simulation for {mat} (+{pct}%) ---")
                print(f"Baseline Estimated Total Cost : ${res['baseline_cost']:,.2f}")
                print(f"Inflated Estimated Total Cost : ${res['inflated_cost']:,.2f}")
                print(f"Projected Cost Variance      : +${res['cost_increase']:,.2f}")
            except Exception as e:
                print(f"❌ Error running simulation: {e}")

        elif choice == "9":
            try:
                df_elements = pd.DataFrame(manager.list_elements())
                df_merged, _ = load_and_clean_data()
                summary = calculate_costs_summary(df_merged, df_elements)
                summary.to_csv("outputs/purchase_summary.csv", index=False)
                generate_matplotlib_charts(df_merged, output_dir="outputs")
                print("✅ Exported summary CSVs and PNG charts to outputs/ directory.")
            except Exception as e:
                print(f"❌ Error exporting outputs: {e}")

        elif choice == "10":
            print("Exiting application. Goodbye!")
            sys.exit()

if __name__ == "__main__":
    main()