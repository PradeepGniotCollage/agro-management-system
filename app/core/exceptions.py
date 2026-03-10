from fastapi import HTTPException, status

class SoilMonitoringError(Exception):
    """Base class for all soil monitoring exceptions."""
    pass

class DatabaseError(SoilMonitoringError):
    """Raised when a database operation fails."""
    pass

class AIModelError(SoilMonitoringError):
    """Raised when the AI model fails to predict."""
    pass

class SensorDataError(SoilMonitoringError):
    """Raised when incoming sensor data is invalid or missing."""
    pass

class CalculationError(SoilMonitoringError):
    """Raised when an internal calculation fails."""
    pass
