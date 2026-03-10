from typing import Dict, Any, List

# Example Mapping for UI
UNIT_MAP = {
    "moisture": "%",
    "temperature": "°C",
    "ph": "",
    "ec": "dS/m",
    "nitrogen": "ppm",
    "phosphorus": "ppm",
    "potassium": "ppm",
    "zinc": "mg/kg",
    "boron": "mg/kg",
    "iron": "mg/kg",
    "copper": "mg/kg",
    "magnesium": "mg/kg",
    "manganese": "mg/kg",
    "calcium": "mg/kg",
    "sulphur": "mg/kg",
    "organic_carbon": "%"
}

# Ideal ranges (min, max) for crop as per provided UI image
IDEAL_RANGES = {
    "nitrogen": (40.0, 60.0),
    "phosphorus": (8.0, 12.0),
    "potassium": (40.0, 60.0),
    "zinc": (0.5, 1.0),
    "boron": (0.5, 0.8),
    "iron": (2.5, 4.0),
    "copper": (1.0, 2.0),
    "manganese": (2.0, 4.0),
    "calcium": (1500.0, 2500.0),
    "sulphur": (5.0, 10.0),
    "organic_carbon": (0.5, 0.75),
    "temperature": (20.0, 30.0),
    "ph": (6.0, 7.5),
    "ec": (0.8, 1.5),
    "moisture": (20.0, 35.0)
}

def get_ideal_range(nutrient: str) -> str:
    """Returns formatted ideal range for a given nutrient."""
    if nutrient in IDEAL_RANGES:
        return f"{IDEAL_RANGES[nutrient][0]} - {IDEAL_RANGES[nutrient][1]}"
    return ""

def evaluate_status(value: float, nutrient: str) -> str:
    """Evaluates nutrient status against ideal ranges."""
    if nutrient not in IDEAL_RANGES:
        return "IDEAL" # Default fallback
    
    min_val, max_val = IDEAL_RANGES[nutrient]
    if value < min_val:
        return "LOW"
    elif value > max_val:
        return "HIGH"
    return "IDEAL"

def calculate_fertilizers(nitrogen: float, phosphorus: float, potassium: float) -> List[Dict[str, Any]]:
    """Calculates fertilizer requirements to meet the max ideal range."""
    # Deficit = Max Ideal - Current Value
    n_deficit = max(0, IDEAL_RANGES["nitrogen"][1] - nitrogen)
    p_deficit = max(0, IDEAL_RANGES["phosphorus"][1] - phosphorus)
    k_deficit = max(0, IDEAL_RANGES["potassium"][1] - potassium)

    recommendations = []
    
    if n_deficit > 0:
        urea_req = round(n_deficit / 0.46, 2)
        recommendations.append({"name": "Urea", "requirement": urea_req, "unit": "kg/hectare"})
        
    if p_deficit > 0:
        dap_req = round(p_deficit / 0.46, 2)
        recommendations.append({"name": "DAP", "requirement": dap_req, "unit": "kg/hectare"})
        
    if k_deficit > 0:
        mop_req = round(k_deficit / 0.60, 2)
        recommendations.append({"name": "MOP", "requirement": mop_req, "unit": "kg/hectare"})

    return recommendations

def calculate_soil_score(status_dict: Dict[str, str]) -> int:
    """
    Start score = 100
    If LOW -> deduct 7
    If HIGH -> deduct 4
    """
    score = 100
    for status in status_dict.values():
        if status == "LOW":
            score -= 7
        elif status == "HIGH":
            score -= 4
            
    return max(0, score) # Score minimum = 0

def get_median(values: List[float]) -> float:
    """Calculates the median of a list of values."""
    if not values:
        return 0.0
    sorted_values = sorted([v for v in values if v is not None])
    if not sorted_values:
        return 0.0
    n = len(sorted_values)
    mid = n // 2
    if n % 2 == 0:
        return round((sorted_values[mid - 1] + sorted_values[mid]) / 2, 2)
    return round(sorted_values[mid], 2)

def validate_reading(value: float, nutrient: str) -> float:
    """
    Filters out impossible sensor values to prevent spikes from ruining the report.
    Returns the value restricted to physical limits.
    """
    limits = {
        "ph": (0.0, 14.0),
        "temperature": (-50.0, 100.0),
        "moisture": (0.0, 100.0),
        "ec": (0.0, 20000.0),
        "nitrogen": (0.0, 5000.0),
        "phosphorus": (0.0, 5000.0),
        "potassium": (0.0, 5000.0)
    }
    
    if nutrient in limits:
        min_v, max_v = limits[nutrient]
        return max(min_v, min(value, max_v))
    
    return max(0.0, value) # Default: no negative values allowed

