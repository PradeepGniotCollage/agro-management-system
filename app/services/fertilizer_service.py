import logging
from typing import Dict, Any

class FertilizerService:
    @staticmethod
    def calculate_recommendations(npk_data: Dict[str, float], ph: float, ec: float) -> Dict[str, Any]:
        """
        Calculates Urea, DAP, and MOP recommendations based on soil NPK, pH, and EC.
        Values are typically in kg/acre for a specific crop (generic baseline here).
        """
        n = npk_data.get("nitrogen", 0)
        p = npk_data.get("phosphorus", 0)
        k = npk_data.get("potassium", 0)

        # Baseline logic (Simplified for Smart Dashboard)
        # N:P:K target (Generic example: 120:60:60 kg/ha -> 50:25:25 kg/acre)
        target_n, target_p, target_k = 50, 25, 25
        
        # Calculate requirements based on deficit
        req_n = max(0, target_n - (n * 0.1)) # Assume some conversion factor
        req_p = max(0, target_p - (p * 0.1))
        req_k = max(0, target_k - (k * 0.1))

        # DAP (18% N, 46% P_2O_5)
        dap = req_p / 0.46
        # Urea (46% N) - subtracting N provided by DAP
        n_from_dap = dap * 0.18
        urea = max(0, req_n - n_from_dap) / 0.46
        # MOP (60% K_2O)
        mop = req_k / 0.60

        # Soil Status based on pH and EC
        soil_status = "Healthy"
        if ph < 6.0:
            soil_status = "Acidic"
        elif ph > 7.5:
            soil_status = "Alkaline"
        
        if ec > 1.2:
            soil_status += " & Saline"

        return {
            "urea_kg_per_acre": round(urea, 2),
            "dap_kg_per_acre": round(dap, 2),
            "mop_kg_per_acre": round(mop, 2),
            "soil_status": soil_status
        }
