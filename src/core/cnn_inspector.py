import cv2
import numpy as np
from ultralytics import YOLO

class CnnInspectionAgent:
    """
    Agente de inspección que utiliza un modelo YOLOv8 entrenado (best.pt)
    para la detección de objetos
    
    Dibuja los bounding boxes
    """
    
    def __init__(self, model_path='best.pt'):
        """
        Carga el modelo YOLOv8 al instanciar el agente
        """
        try:
            self.model = YOLO(model_path)
            self.class_names = self.model.names
            print(f"Modelo '{model_path}' cargado exitosamente")
            
            # Definir colores fijos para las clases (BGR para OpenCV)
            # pastilla (ID 0) para Verde (0, 255, 0)
            # vacio (ID 1) para Rojo/Azul (255, 0, 0)
            self.colors = {
                0: (0, 255, 0),   # Verde pastillas
                1: (255, 0, 0)    # Azul vacíos
            }
            
        except Exception as e:
            print(f"Error al cargar el modelo YOLO '{model_path}': {e}")
            self.model = None

    def process_frame_step_by_step(self, frame_original: np.ndarray) -> tuple[np.ndarray, dict, list]:
        """
        Ejecuta la inferencia y dibuja recuadros en el frame
        """
        if self.model is None:
            return frame_original, {'final_contours': frame_original}, []

        # Inferencia
        # verbose=False para no llenar la consola de logs
        results = self.model.predict(frame_original, conf=0.5, verbose=False)
        
        # Copia limpia del frame para dibujar
        frame_final = frame_original.copy()
        formatted_results = []
        
        if not results:
            return frame_final, {'final_contours': frame_final}, formatted_results

        # Procesar resultados
        result = results[0]
        
        for box in result.boxes:
            # Extracción de Datos
            # Coordenadas del recuadro
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            
            conf = float(box.conf[0])
            cls_id = int(box.cls[0])
            class_name = self.class_names.get(cls_id, 'Desconocido')
            
            # Dibujo de recuadros
            color = self.colors.get(cls_id, (255, 255, 255))
            
            cv2.rectangle(frame_final, (x1, y1), (x2, y2), color, 2)
            
            # Datos para el Reporte
            formatted_results.append({
                'id': len(formatted_results) + 1,
                'area': int((x2 - x1) * (y2 - y1)),
                'circularity': round(conf, 2),
                'status': class_name.capitalize()
            })

        # Preparar salida
        # Reutilizamos imagen final para todas vistas
        step_images = {
            'original': frame_original,
            'grayscale': cv2.cvtColor(frame_original, cv2.COLOR_BGR2GRAY),
            'thresholded': frame_final, # Mostrar la imagen limpia con cajas
            'final_contours': frame_final
        }

        # Ordenar tabla por estado
        formatted_results.sort(key=lambda x: x['status'])
        
        return frame_final, step_images, formatted_results