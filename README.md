# Construction Materials Cost Planner

**Student:** Ahmed adel.
**Assignment:** Assignment 02 - Construction Materials Cost Planner

## Project description
A Python console application with two connected modules, joined by a menu in `main.py`.

- **Module 1 - Material Quantity Calculator** (`module1_calculator.py`): add, list, search and update concrete elements; calculates net volume, volume including waste, and required cement (kg), sand (m3) and aggregate (m3) per element and per site (rates: 300 kg, 0.5 m3 and 0.8 m3 per m3 including waste); saves results to CSV.
- **Module 2 - Purchase and Cost Analysis** (`module2_analysis.py`): cleans and merges price and purchase data with pandas, calculates cost per site / supplier / month, compares required vs purchased quantities (shortage / surplus), runs a NumPy price-sensitivity simulation (lowest price per material as baseline), and creates four Matplotlib charts.

Validation: dimensions, prices and quantities must be > 0; waste must be 0-100; duplicate IDs and references to unknown IDs are rejected.

## Project structure
```
main.py                  menu
module1_calculator.py    Module 1
module2_analysis.py      Module 2
tests.py                 3 valid + 4 invalid test cases
analysis_notebook.ipynb  short notebook explaining the analysis
requirements.txt
data/                    elements.csv, prices.csv, purchases.csv (sample data)
outputs/                 generated reports (CSV) and charts (PNG)
```

## Required libraries
Python 3.9+, `pandas`, `numpy`, `matplotlib` (and `jupyter` for the notebook).

```
pip install -r requirements.txt
```

## How to run
```
python main.py          # start the menu
python tests.py         # run the tests (writes outputs/test_results.csv)
jupyter notebook analysis_notebook.ipynb
```
Suggested order in the menu: 2 (list) -> 6 (load & clean) -> 7 (compare) -> 8 (price simulation) -> 9 (export charts and reports).

## Sample data
8 elements across 2 sites, 2 suppliers per material, and 38 purchase rows covering August-September 2026 (2 duplicate and 3 incomplete rows are included on purpose to show the cleaning step; 35 valid transactions remain).

## Outputs (in `outputs/`)
`element_quantities.csv`, `site_quantities.csv`, `purchase_summary.csv`, `quantity_comparison.csv`, `rejected_records.csv`, `test_results.csv`, and `chart1_monthly_spend.png`, `chart2_supplier_cost.png`, `chart3_qty_vs_cost.png`, `chart4_cost_distribution.png`.
