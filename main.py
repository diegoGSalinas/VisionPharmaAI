import os
import cv2
import time
import numpy as np
from flask import Flask, render_template, request, url_for, send_from_directory, Response, jsonify
from werkzeug.utils import secure_filename
from datetime import datetime
import atexit 

from src.core.cnn_inspector import CnnInspectionAgent
from src.core.database import DatabaseConnection
from src.core.models import InspectionReportDTO
from src.core.camera import CameraStream

# Configuración Flask
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

# Servicios Singleton

print("Cargando agente de IA...")
agent = CnnInspectionAgent() 

print("Conectando a la base de datos...")
db_conn = DatabaseConnection()
db_conn.initialize() 

print("Inicializando la cámara...")
try:
    cam = CameraStream(camera_index=0) 
    cam.start()
except Exception as e:
    print(f"ADVERTENCIA: No se pudo iniciar la cámara: {e}")

print("--- APLICACIÓN PRINCIPAL LISTA Y CORRIENDO ---")

# Variables Globales para Auto-Trigger
last_capture_time = 0       
stability_counter = 0       
REQUIRED_FRAMES = 3         
COOLDOWN_SECONDS = 3.0
frames_to_show_message = 0
MESSAGE_DURATION = 40  

# RUTAS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/live')
def live_page():
    return render_template('live.html', 
                           current_frames=REQUIRED_FRAMES, 
                           current_cooldown=COOLDOWN_SECONDS)

# API para actualizar configuración
@app.route('/api/update_settings', methods=['POST'])
def update_settings():
    global REQUIRED_FRAMES, COOLDOWN_SECONDS
    try:
        data = request.json
        # Validar y actualizar
        new_frames = int(data.get('frames', REQUIRED_FRAMES))
        new_cooldown = float(data.get('cooldown', COOLDOWN_SECONDS))
        
        # Límites de seguridad
        REQUIRED_FRAMES = max(1, min(new_frames, 30))
        COOLDOWN_SECONDS = max(0.5, min(new_cooldown, 60.0))
        
        print(f"[CONFIG] Actualizado: Frames={REQUIRED_FRAMES}, Cooldown={COOLDOWN_SECONDS}s")
        
        return jsonify({
            "status": "success", 
            "message": "Configuración actualizada",
            "frames": REQUIRED_FRAMES,
            "cooldown": COOLDOWN_SECONDS
        })
    except Exception as e:
        print(f"Error actualizando configuración: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400


@app.route('/upload', methods=['GET', 'POST'])
def upload_page():
    step_image_urls = None
    results_data = None
    
    if request.method == 'POST':
        if 'file' not in request.files:
             return render_template('upload.html', error="No se encontró el archivo")
        
        file = request.files['file']
        
        if file.filename == '' or not allowed_file(file.filename):
             return render_template('upload.html', error="Formato de archivo no permitido")
        
        filename_base = secure_filename(file.filename)
        timestamp = int(time.time() * 1000)
        filename = f"manual_{timestamp}_{filename_base}"
        input_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(input_path)
        original_frame = cv2.imread(input_path)

        if original_frame is not None:
            _, step_images, results_list = agent.process_frame_step_by_step(original_frame)
            
            step_image_urls = {}
            
            for step_name, img_data in step_images.items():
                if img_data.ndim == 2:
                    img_data = cv2.cvtColor(img_data, cv2.COLOR_GRAY2BGR)
                output_filename = f"{step_name}_{timestamp}.jpg"
                output_path = os.path.join(app.config['RESULTS_FOLDER'], output_filename)
                cv2.imwrite(output_path, img_data)
                relative_path = f'results/{output_filename}'
                step_image_urls[step_name] = url_for('serve_static', filename=relative_path)

            results_data = results_list
            os.remove(input_path)

    return render_template('upload.html', step_image_urls=step_image_urls, results_data=results_data)

@app.route('/history')
def history_page():
    try:
        history_data = db_conn.get_all_inspections()
    except Exception as e:
        print(f"Error al leer historial: {e}")
        history_data = []
    return render_template('history.html', history=history_data)

@app.route('/dashboard')
def dashboard_page():
    time_filter = request.args.get('filter', 'day')
    try:
        pie_data = db_conn.get_stats_pie_chart()
        line_data = db_conn.get_stats_line_chart(mode=time_filter)
        kpis = db_conn.get_kpis()
    except Exception as e:
        print(f"Error al leer dashboard: {e}")
        pie_data, line_data, kpis = {}, [], {}

    return render_template('dashboard.html', 
                           pie_data=pie_data, 
                           line_data=line_data, 
                           kpis=kpis,
                           current_filter=time_filter)


# STREAMING Y AUTO-TRIGGER

def generate_frames():
    global last_capture_time, stability_counter, frames_to_show_message, REQUIRED_FRAMES, COOLDOWN_SECONDS
    
    while True:
        frame = cam.get_frame()
        if frame is None:
            time.sleep(0.1)
            continue
            
        try:
            _, step_images, results_list = agent.process_frame_step_by_step(frame)
            final_frame = step_images.get('final_contours', frame)
            
            frame_with_boxes_no_text = final_frame.copy()
            
            # Auto-Trigger
            current_time = time.time()
            time_since_last = current_time - last_capture_time
            
            count_pills = sum(1 for r in results_list if r['status'] == 'Pastilla')
            count_empty = sum(1 for r in results_list if r['status'] == 'Vacio')
            total_objects = count_pills + count_empty
            
            if time_since_last > COOLDOWN_SECONDS:
                if total_objects == 10:
                    stability_counter += 1
                    
                    cv2.putText(final_frame, f"ESTABILIZANDO: {stability_counter}/{REQUIRED_FRAMES}", 
                               (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                    
                    if stability_counter >= REQUIRED_FRAMES:
                        # DISPARO
                        last_capture_time = current_time
                        stability_counter = 0
                        
                        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                        filename_boxes = f"auto_{timestamp_str}_boxes.jpg"
                        filename_clean = f"auto_{timestamp_str}_clean.jpg"
                        
                        filepath_boxes = os.path.join(app.config['RESULTS_FOLDER'], filename_boxes)
                        filepath_clean = os.path.join(app.config['RESULTS_FOLDER'], filename_clean)
                        
                        # Guardar dos versiones
                        cv2.imwrite(filepath_boxes, frame_with_boxes_no_text)
                        cv2.imwrite(filepath_clean, frame)
                        
                        estado = "Aprobado" if count_empty == 0 else "Defectuoso"
                        dto = InspectionReportDTO(
                            timestamp=datetime.now(),
                            total_pastillas=count_pills,
                            total_vacios=count_empty,
                            estado_final=estado,
                            imagen_resultado=f"results/{filename_boxes}",
                            imagen_resultado_clean=f"results/{filename_clean}"
                        )
                        try:
                            db_conn.save_inspection(dto)
                            print(f"[AUTO] Guardado: {filename_boxes}")
                        except Exception as e:
                            print(f"[ERROR BD] {e}")
                            
                        frames_to_show_message = MESSAGE_DURATION
                else:
                    stability_counter = 0
            else:
                remaining = int(COOLDOWN_SECONDS - time_since_last) + 1
                cv2.putText(final_frame, f"ESPERANDO... {remaining}s", (20, 50), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

            if frames_to_show_message > 0:
                cv2.putText(final_frame, "GUARDADO!", (20, 100), 
                           cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 255, 0), 3)
                frames_to_show_message -= 1

        except Exception as e:
            print(f"Error IA Loop: {e}")
            final_frame = frame 
            
        ret, buffer = cv2.imencode('.jpg', final_frame)
        if not ret: continue
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(os.path.join(PROJECT_ROOT, 'static'), filename)

@atexit.register
def shutdown_app():
    print("Cerrando aplicación...")
    cam.stop()

if __name__ == '__main__':
    app.run(debug=False, port=5000, threaded=True, use_reloader=False)