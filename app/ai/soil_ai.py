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

    def predict(self, sensor_data: Dict[str, Any]) -> Optional[Dict[str, float]]:
        """
        Predicts micronutrients using Joblib ML model.
        """
        self._load_model_safe()

        result_keys = ["zinc", "boron", "iron", "copper", "magnesium", "manganese", "calcium", "sulphur", "organic_carbon"]
        
        if not self.model:
            return None

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
            return None

soil_ai = SoilAIModel()
