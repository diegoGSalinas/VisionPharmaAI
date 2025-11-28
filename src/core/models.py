from dataclasses import dataclass
from datetime import datetime

@dataclass
class InspectionReportDTO:
    """
    Data Transfer Object para reportes de inspección
    """
    timestamp: datetime
    total_pastillas: int
    total_vacios: int
    estado_final: str
    imagen_resultado: str
    imagen_resultado_clean: str