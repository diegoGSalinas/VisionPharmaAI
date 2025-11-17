import os
import cv2
import time
import numpy as np
from flask import Flask, render_template, request, url_for, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
# Importar Módulos de IA y Base de Datos
from src.core.cnn_inspector import CnnInspectionAgent
from src.core.database import DatabaseConnection
from src.core.models import InspectionReportDTO

# Configuración de Flask
app = Flask(__name__, 
            template_folder='src/web_interface/templates', 
            static_folder='static')

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'static', 'uploads')
RESULTS_FOLDER = os.path.join(PROJECT_ROOT, 'static', 'results')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['RESULTS_FOLDER'] = RESULTS_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Inicialización de Servicios Singleton

# 1. Cargar el "cerebro" de IA (modelo best.pt) una sola vez
# El modelo se carga automáticamente dentro del constructor (__init__)
agent = CnnInspectionAgent() 

# 2. Conectarse a la Base de Datos y preparar la tabla
db_conn = DatabaseConnection()
db_conn.initialize() # Crea la tabla 'inspections' si no existe

# Ruta Principal de la App
@app.route('/', methods=['GET', 'POST'])
def upload_file():
    step_image_urls = None
    results_data = None
    
    if request.method == 'POST':
        if 'file' not in request.files:
             return render_template('upload.html', error="No se encontró el archivo")
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
             return render_template('upload.html', error="Formato de archivo no permitido")
        
        # Generar nombre seguro y único
        filename_base = secure_filename(file.filename)
        timestamp = int(time.time() * 1000)
        filename = f"input_{timestamp}_{filename_base}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(input_path)

        # 1. Leer la imagen con OpenCV (para procesamiento)
        original_frame = cv2.imread(input_path)

        if original_frame is not None:
            # 2. Ejecutar el Pipeline de Visión IA
            # 'results_list' contiene los datos ('Pastilla', 'Vacio')
            # 'step_images' contiene las imágenes del pipeline para mostrar
            _, step_images, results_list = agent.process_frame_step_by_step(original_frame)
            
            # 3. Guardar las imágenes de resultado y generar URLs
            step_image_urls = {}
            final_image_path_for_db = None
            
            for step_name, img_data in step_images.items():
                if img_data.ndim == 2:
                    img_data = cv2.cvtColor(img_data, cv2.COLOR_GRAY2BGR)

                output_filename = f"{step_name}_{timestamp}.jpg"
                output_path = os.path.join(app.config['RESULTS_FOLDER'], output_filename)
                
                # Guardar la imagen en el disco
                cv2.imwrite(output_path, img_data)
                
                # Generar la URL estática para el HTML
                relative_path = f'results/{output_filename}'
                step_image_urls[step_name] = url_for('serve_static', filename=relative_path)
                
                # Guardar la ruta de la imagen final para la base de datos
                if step_name == 'final_contours':
                    final_image_path_for_db = relative_path

            results_data = results_list
            
            # 4. Reporte y Persistencia (Base de Datos)
            try:
                # Contar los resultados de la IA
                total_pastillas = sum(1 for r in results_list if r['status'] == 'Pastilla')
                total_vacios = sum(1 for r in results_list if r['status'] == 'Vacio')
                
                # Determinar el estado final
                estado_final = "Aprobado"
                if total_vacios > 0:
                    estado_final = "Defectuoso"
                # (Se podría añadir lógica para 'Deforme' u otro estado si el modelo lo soporta)

                # Crear el DTO
                reporte_dto = InspectionReportDTO(
                    timestamp=datetime.now(),
                    total_pastillas=total_pastillas,
                    total_vacios=total_vacios,
                    estado_final=estado_final,
                    imagen_resultado=final_image_path_for_db
                )
                
                # Guardar el DTO en la base de datos
                db_conn.save_inspection(reporte_dto)

            except Exception as e:
                print(f"Error al guardar en la base de datos: {e}")
            
            # 5. Limpieza de archivo subido
            os.remove(input_path)

    return render_template('upload.html', step_image_urls=step_image_urls, results_data=results_data)

@app.route('/static/<path:filename>')
def serve_static(filename):
    """imágenes de resultados"""
    return send_from_directory(os.path.join(PROJECT_ROOT, 'static'), filename)

if __name__ == '__main__':
    app.run(debug=True, port=5000)