import csv
import os

class ConcreteElement:
    """Class representing a concrete element and calculating material quantities."""
    
    # Assumed rates per cubic meter including waste
    CEMENT_RATE = 300.0  # kg per m3
    SAND_RATE = 0.5      # m3 per m3
    AGGREGATE_RATE = 0.8 # m3 per m3

    def __init__(self, element_id: str, name: str, site: str, length: float, width: float, height: float, waste_pct: float):
        if length <= 0 or width <= 0 or height <= 0:
            raise ValueError("Dimensions (length, width, height) must be strictly greater than zero.")
        if not (0 <= waste_pct <= 100):
            raise ValueError("Waste percentage must be between 0 and 100.")
        
        self.element_id = str(element_id).strip()
        self.name = str(name).strip()
        self.site = str(site).strip()
        self.length = float(length)
        self.width = float(width)
        self.height = float(height)
        self.waste_pct = float(waste_pct)

    def calculate_net_volume((self) -> float:
        """Net volume (m³) = length × width × height."""
        return self.length * self.width * self.height

    def calculate_gross_volume(self) -> float:
        """Volume including waste = net volume × (1 + waste percentage ÷ 100)."""
        return self.calculate_net_volume() * (1 + self.waste_pct / 100.0)

    def calculate_materials(self) -> dict:
        """Calculates cement (kg), sand (m³), and aggregate (m³) quantities."""
        gross_vol = self.calculate_gross_volume()
        return {
            "cement_kg": gross_vol * self.CEMENT_RATE,
            "sand_m3": gross_vol * self.SAND_RATE,
            "aggregate_m3": gross_vol * self.AGGREGATE_RATE
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
            "required_aggregate_m3": round(mats["aggregate_m3"], 2)
        }


class ElementManager:
    """Manages concrete element inventory and persistence."""

    def __init__(self, filepath: str = "data/elements.csv"):
        self.filepath = filepath
        self.elements = {}

    def add_element(self, element: ConcreteElement):
        if element.element_id in self.elements:
            raise ValueError(f"Duplicate Record ID '{element.element_id}' is not allowed.")
        self.elements[element.element_id] = element

    def update_element(self, element_id: str, **kwargs):
        if element_id not in self.elements:
            raise KeyError(f"Element ID '{element_id}' not found.")
        
        elem = self.elements[element_id]
        new_name = kwargs.get("name", elem.name)
        new_site = kwargs.get("site", elem.site)
        new_l = kwargs.get("length", elem.length)
        new_w = kwargs.get("width", elem.width)
        new_h = kwargs.get("height", elem.height)
        new_waste = kwargs.get("waste_pct", elem.waste_pct)

        updated_elem = ConcreteElement(element_id, new_name, new_site, new_l, new_w, new_h, new_waste)
        self.elements[element_id] = updated_elem

    def get_element(self, element_id: str):
        return self.elements.get(element_id, None)

    def list_elements(self):
        return [elem.to_dict() for elem in self.elements.values()]

    def save_to_csv(self, output_path: str = None):
        target_path = output_path or self.filepath
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        
        if not self.elements:
            print("No elements to save.")
            return

        fieldnames = list(next(iter(self.elements.values())).to_dict().keys())
        with open(target_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for elem in self.elements.values():
                writer.writerow(elem.to_dict())
        print(f"✅ Saved element data to {target_path}")

    def load_from_csv(self):
        if not os.path.exists(self.filepath):
            return
        with open(self.filepath, mode="r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                elem = ConcreteElement(
                    element_id=row["element_id"],
                    name=row.get("element_name", row.get("name", "")),
                    site=row["site"],
                    length=float(row["length_m"] if "length_m" in row else row["length"]),
                    width=float(row["width_m"] if "width_m" in row else row["width"]),
                    height=float(row["height_m"] if "height_m" in row else row["height"]),
                    waste_pct=float(row["waste_pct"])
                )
                self.elements[elem.element_id] = elem