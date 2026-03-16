import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import joblib
import numpy as np

logger = logging.getLogger(__name__)

class SoilAIModel:
    def __init__(self, model_filename: str = "model.joblib"):
        self.model_filename = model_filename
        self.model: Any = None
        self._load_attempted = False
        self._resolved_model_path: Optional[Path] = None

    def _candidate_paths(self) -> list[Path]:
        env_path = os.getenv("MODEL_PATH") or os.getenv("AI_MODEL_PATH")
        candidates: list[Path] = []

        if env_path:
            candidates.append(Path(env_path))

        project_root = Path(__file__).resolve().parents[2]
        candidates.extend([
            project_root / self.model_filename,
            project_root / "models" / self.model_filename,
            project_root / "app" / "ai" / "models" / self.model_filename,
            Path.cwd() / self.model_filename,
        ])

        unique: list[Path] = []
        seen: set[str] = set()
        for p in candidates:
            key = str(p.resolve()) if p.exists() else str(p)
            if key not in seen:
                unique.append(p)
                seen.add(key)
        return unique

    def _load_model_safe(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True

        for candidate in self._candidate_paths():
            try:
                if not candidate.exists():
                    continue
                self.model = joblib.load(candidate)
                self._resolved_model_path = candidate
                logger.info(f"Loaded AI model from {candidate}")
                return
            except Exception as e:
                logger.exception(f"Failed to load AI model from {candidate}: {e}")
                self.model = None
                self._resolved_model_path = None

        logger.warning(
            "Model file model.joblib not found. AI-based micronutrient prediction will be unavailable. "
            f"Searched: {[str(p) for p in self._candidate_paths()]}"
        )

    def is_available(self) -> bool:
        self._load_model_safe()
        return self.model is not None

    def _fallback_predict(self, sensor_data: Dict[str, Any]) -> Dict[str, float]:
        ph = float(sensor_data.get("ph", 7.0) or 7.0)
        n = float(sensor_data.get("nitrogen", 0.0) or 0.0)
        p = float(sensor_data.get("phosphorus", 0.0) or 0.0)
        k = float(sensor_data.get("potassium", 0.0) or 0.0)
        moisture = float(sensor_data.get("moisture", 0.0) or 0.0)
        temperature = float(sensor_data.get("temperature", 0.0) or 0.0)

        zinc = 0.3 + (n * 0.004) + (moisture * 0.002)
        boron = 0.25 + (p * 0.002) + (temperature * 0.003)
        iron = 2.2 + (n * 0.01) + (k * 0.002)
        copper = 0.9 + (k * 0.001) + (n * 0.002)
        magnesium = 0.4 + (p * 0.002) + (moisture * 0.001)
        manganese = 1.4 + (n * 0.008) - (abs(ph - 6.8) * 0.15)
        calcium = 1200.0 + (k * 1.5) + (p * 3.0)
        sulphur = 3.5 + (n * 0.02) + (p * 0.01)
        organic_carbon = 0.35 + (n * 0.001) + (p * 0.0005) + (k * 0.0002)

        return {
            "zinc": round(max(zinc, 0.05), 2),
            "boron": round(max(boron, 0.05), 2),
            "iron": round(max(iron, 0.05), 2),
            "copper": round(max(copper, 0.05), 2),
            "magnesium": round(max(magnesium, 0.05), 2),
            "manganese": round(max(manganese, 0.05), 2),
            "calcium": round(max(calcium, 200.0), 2),
            "sulphur": round(max(sulphur, 0.1), 2),
            "organic_carbon": round(max(organic_carbon, 0.05), 2),
        }

    def predict(self, sensor_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Predicts micronutrients using Joblib ML model.
        """
        self._load_model_safe()

        result_keys = ["zinc", "boron", "iron", "copper", "magnesium", "manganese", "calcium", "sulphur", "organic_carbon"]
        
        if not self.model:
            logger.warning("AI model not available. Using fallback estimation for micronutrients.")
            return self._fallback_predict(sensor_data)

        # Feature vector
        features = np.array([
            sensor_data.get("moisture", 0),
            sensor_data.get("temperature", 0),
            sensor_data.get("ph", 0),
            sensor_data.get("ec", 0),
            sensor_data.get("nitrogen", 0),
            sensor_data.get("phosphorus", 0),
            sensor_data.get("potassium", 0)
        ]).reshape(1, -1)

        try:
            prediction = self.model.predict(features)[0]
            return {key: round(float(val), 2) for key, val in zip(result_keys, prediction)}
        except Exception as e:
            logger.exception(f"Error during AI prediction: {e}")
            return self._fallback_predict(sensor_data)

soil_ai = SoilAIModel()
