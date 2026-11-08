"""Module 1 - Material Quantity Calculator.

Defines ConcreteElement (one concrete element) and ElementManager
(add / list / search / update elements, per-site totals, CSV persistence).
"""
import csv
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Tuple of fields written to the element CSV (order matters).
ELEMENT_FIELDS = (
    "element_id", "element_name", "site", "length_m", "width_m", "height_m",
    "waste_pct", "net_volume_m3", "gross_volume_m3",
    "required_cement_kg", "required_sand_m3", "required_aggregate_m3",
)
# Set of attributes that update_element is allowed to change.
UPDATABLE_FIELDS = {"name", "site", "length", "width", "height", "waste_pct"}


class ConcreteElement:
    """A concrete element and the material quantities it needs."""

    # Training rates per cubic metre of concrete INCLUDING waste
    CEMENT_RATE = 300.0   # kg per m3
    SAND_RATE = 0.5       # m3 per m3
    AGGREGATE_RATE = 0.8  # m3 per m3

    def __init__(self, element_id, name, site, length, width, height, waste_pct):
        element_id, name, site = str(element_id).strip(), str(name).strip(), str(site).strip()
        if not element_id:
            raise ValueError("Element ID cannot be empty.")
        if not site:
            raise ValueError("Site name cannot be empty.")
        length, width, height, waste_pct = float(length), float(width), float(height), float(waste_pct)
        # 'not (x > 0)' also rejects NaN
        if not (length > 0 and width > 0 and height > 0):
            raise ValueError("Dimensions (length, width, height) must be greater than zero.")
        if not (0 <= waste_pct <= 100):
            raise ValueError("Waste percentage must be between 0 and 100.")

        self.element_id = element_id
        self.name = name
        self.site = site
        self.length = length
        self.width = width
        self.height = height
        self.waste_pct = waste_pct

    def calculate_net_volume(self) -> float:
        """Net volume (m3) = length x width x height."""
        return self.length * self.width * self.height

    def calculate_gross_volume(self) -> float:
        """Volume incl. waste = net volume x (1 + waste% / 100)."""
        return self.calculate_net_volume() * (1 + self.waste_pct / 100.0)

    def calculate_materials(self) -> dict:
        """Cement (kg), sand (m3) and aggregate (m3) for this element."""
        gross = self.calculate_gross_volume()
        return {
            "cement_kg": gross * self.CEMENT_RATE,
            "sand_m3": gross * self.SAND_RATE,
            "aggregate_m3": gross * self.AGGREGATE_RATE,
        }

    def to_dict(self) -> dict:
        mats = self.calculate_materials()
        return {
            "element_id": self.element_id,
            "element_name": self.name,
            "site": self.site,
            "length_m": self.length,
            "width_m": self.width,
            "height_m": self.height,
            "waste_pct": self.waste_pct,
            "net_volume_m3": round(self.calculate_net_volume(), 4),
            "gross_volume_m3": round(self.calculate_gross_volume(), 4),
            "required_cement_kg": round(mats["cement_kg"], 2),
            "required_sand_m3": round(mats["sand_m3"], 2),
            "required_aggregate_m3": round(mats["aggregate_m3"], 2),
        }


class ElementManager:
    """Stores elements in a dict keyed by element ID and handles CSV I/O."""

    def __init__(self, filepath: str = os.path.join(BASE_DIR, "data", "elements.csv")):
        self.filepath = filepath
        self.elements = {}  # element_id -> ConcreteElement

    def __len__(self):
        return len(self.elements)

    def add_element(self, element: ConcreteElement):
        if not isinstance(element, ConcreteElement):
            raise TypeError("add_element expects a ConcreteElement.")
        if element.element_id in self.elements:
            raise ValueError(f"Duplicate record ID '{element.element_id}' is not allowed.")
        self.elements[element.element_id] = element

    def update_element(self, element_id: str, **kwargs):
        """Update any of name, site, length, width, height, waste_pct.
        The new element is validated first, so a bad update changes nothing."""
        if element_id not in self.elements:
            raise KeyError(f"Element ID '{element_id}' not found.")
        unknown = set(kwargs) - UPDATABLE_FIELDS
        if unknown:
            raise ValueError(f"Cannot update unknown field(s): {sorted(unknown)}")

        e = self.elements[element_id]
        updated = ConcreteElement(
            element_id,
            kwargs.get("name", e.name),
            kwargs.get("site", e.site),
            kwargs.get("length", e.length),
            kwargs.get("width", e.width),
            kwargs.get("height", e.height),
            kwargs.get("waste_pct", e.waste_pct),
        )
        self.elements[element_id] = updated

    def get_element(self, element_id: str):
        return self.elements.get(str(element_id).strip())

    def list_elements(self, limit=None):
        """All elements as dicts (optionally only the first `limit`, via slicing)."""
        rows = [e.to_dict() for e in self.elements.values()]
        return rows[:limit] if limit is not None else rows

    def search_by_site(self, site: str):
        site = str(site).strip().lower()
        return [e.to_dict() for e in self.elements.values() if e.site.lower() == site]

    def site_summary(self):
        """Total volumes and material quantities per site (list of dicts)."""
        totals = {}
        for e in self.elements.values():
            m = e.calculate_materials()
            t = totals.setdefault(e.site, {
                "site": e.site, "element_count": 0, "net_volume_m3": 0.0,
                "gross_volume_m3": 0.0, "required_cement_kg": 0.0,
                "required_sand_m3": 0.0, "required_aggregate_m3": 0.0})
            t["element_count"] += 1
            t["net_volume_m3"] += e.calculate_net_volume()
            t["gross_volume_m3"] += e.calculate_gross_volume()
            t["required_cement_kg"] += m["cement_kg"]
            t["required_sand_m3"] += m["sand_m3"]
            t["required_aggregate_m3"] += m["aggregate_m3"]
        result = []
        for site in sorted(totals):
            row = totals[site]
            for k, v in row.items():
                if isinstance(v, float):
                    row[k] = round(v, 2)
            result.append(row)
        return result

    @staticmethod
    def _ensure_dir(path):
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)

    def save_to_csv(self, output_path: str = None):
        """Save elements + calculated quantities. Returns the path, or None if empty."""
        target = output_path or self.filepath
        if not self.elements:
            print("No elements to save.")
            return None
        self._ensure_dir(target)
        with open(target, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(ELEMENT_FIELDS))
            writer.writeheader()
            for e in self.elements.values():
                writer.writerow(e.to_dict())
        return target

    def save_site_summary_csv(self, output_path: str):
        rows = self.site_summary()
        if not rows:
            print("No elements to summarise.")
            return None
        self._ensure_dir(output_path)
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        return output_path

    def load_from_csv(self):
        """Load elements from CSV. Duplicate IDs / invalid rows raise an error
        that names the offending row."""
        if not os.path.exists(self.filepath):
            return
        with open(self.filepath, "r", encoding="utf-8") as f:
            for line_no, row in enumerate(csv.DictReader(f), start=2):
                try:
                    self.add_element(ConcreteElement(
                        row["element_id"], row["element_name"], row["site"],
                        row["length_m"], row["width_m"], row["height_m"], row["waste_pct"]))
                except (ValueError, KeyError) as err:
                    raise ValueError(f"{self.filepath} line {line_no}: {err}") from err
