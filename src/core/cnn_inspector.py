import cv2
import numpy as np
from ultralytics import YOLO

class CnnInspectionAgent:
    """
    Agente de inspección que utiliza un modelo YOLOv8 entrenado (best.pt)
    para la detección de objetos (pastillas y cavidades vacías)
    """
    
    def __init__(self, model_path='best.pt'):
        """
        Carga el modelo YOLOv8 al instanciar el agente
        
        Args:
            model_path (str): Ruta al archivo .pt (el cerebro de IA)
        """
        try:
            self.model = YOLO(model_path)
            # Obtiene los nombres de las clases del modelo ('pastilla', 'vacio')
            self.class_names = self.model.names
            print(f"Modelo '{model_path}' cargado exitosamente.")
            print(f"Clases detectadas: {self.class_names}")
        except Exception as e:
            print(f"Error fatal al cargar el modelo YOLO '{model_path}': {e}")
            self.model = None

    def process_frame_step_by_step(self, frame_original: np.ndarray) -> tuple[np.ndarray, dict, list]:
        """
        Ejecuta el pipeline de inferencia de IA en un solo frame.
        """
        if self.model is None:
            print("Error: El modelo no está cargado. No se puede procesar el frame")
            # Devolver imágenes vacías para evitar que la app web se rompa
            h, w = frame_original.shape[:2]
            dummy_img = np.zeros((h, w, 3), dtype=np.uint8)
            return dummy_img, {'original': dummy_img, 'grayscale': dummy_img, 'thresholded': dummy_img, 'final_contours': dummy_img}, []

        step_images = {'original': frame_original.copy()}
        
        # 1. Predicción
        
        # La IA ejecuta la detección en el frame original
        results = self.model.predict(frame_original, conf=0.5) # Confianza mínima del 50%
        
        frame_final = frame_original.copy()
        formatted_results = []
        
        if not results:
            print("No se encontraron resultados en la predicción")
            return frame_final, step_images, formatted_results

        # 2. Procesar y Dibujar Resultados
        for r in results:
            boxes = r.boxes
            
            # Dibujar los recuadros en la imagen
            # (Se usa la función 'plot' de ultralytics para mayor velocidad)
            frame_final = r.plot(show=False) # 'show=False' devuelve la imagen

            # 3. Formatear para la Tabla de Reportes
            for box in boxes:
                # Obtener coordenadas, confianza y ID de clase
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                class_name = self.class_names.get(cls_id, 'Desconocido') # Obtener nombre de la clase
                
                # Formatear los datos para la tabla del frontend
                # Nota: 'confianza' en el lugar de 'circularidad'
                formatted_results.append({
                    'id': len(formatted_results) + 1,
                    'area': int((x2 - x1) * (y2 - y1)), # Área del recuadro
                    'circularity': round(conf, 2), # Mostrar confianza en esta columna
                    'status': class_name.capitalize() # 'Pastilla' o 'Vacio'
                })

        # 4. Preparar Imágenes de Pasos
        # El HTML espera 'grayscale' y 'thresholded'
        step_images['grayscale'] = cv2.cvtColor(frame_original, cv2.COLOR_BGR2GRAY)
        
        # Se usa la imagen con los recuadros dibujados como "thresholded"
        step_images['thresholded'] = cv2.cvtColor(frame_final, cv2.COLOR_BGR2GRAY)
        
        step_images['final_contours'] = frame_final # La imagen final con colores

        # Ordenar por estado para que se vea bien en la tabla
        formatted_results.sort(key=lambda x: x['status'])
        
        return frame_final, step_images, formatted_results

