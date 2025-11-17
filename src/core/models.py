from dataclasses import dataclass
from datetime import datetime

@dataclass
class InspectionReportDTO:
    """
    Data Transfer Object para reportes de inspección
    desde la Capa de aplicación (app_cnn.py) hasta
    la capa de persistencia (database.py)
    """
    timestamp: datetime
    total_pastillas: int
    total_vacios: int
    estado_final: str
    imagen_resultado: str