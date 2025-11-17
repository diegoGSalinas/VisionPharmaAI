import cv2
from flask import Flask, render_template, Response
import atexit # Manejar cierre de la app
# Módulos CORE necesarios
from src.core.cnn_inspector import CnnInspectionAgent
from src.core.camera import CameraStream

# Configuración de Flask
app = Flask(__name__, 
            template_folder='src/web_interface/templates', 
            static_folder='static')

# Inicialización de Servicios Singleton

# 1. Cargar el "cerebro" de IA (modelo best.pt)
print("Cargando agente de IA...")
agent = CnnInspectionAgent() 

# 2. Inicializar la Cámara (Singleton)
print("Inicializando la cámara...")
cam = CameraStream(camera_index=0) 

# 3. Iniciar el hilo de lectura de la cámara
cam.start()

print("--- APLICACIÓN DE PRUEBA EN VIVO LISTA Y CORRIENDO ---")

# Ruta para la Página de Video en Vivo
@app.route('/live')
def live_page():
    """Página HTML 'live.html' que contendrá el video"""
    return render_template('live.html')

# Generador de Frames para el Video
def generate_frames():
    """
    Obtiene cuadros de la cámara, los procesa con la IA,
    y los codifica como JPEGs para el stream
    """
    while True:
        # 1. Obtener frame (desde la variable, no desde la cámara)
        frame = cam.get_frame()
        if frame is None:
            # Esperar un poco si el hilo de la cámara aún no ha capturado nada
            time.sleep(0.1)
            continue
            
        # 2. Procesar el frame con la IA
        try:
            _, step_images, _ = agent.process_frame_step_by_step(frame)
            final_frame = step_images.get('final_contours', frame)
        except Exception as e:
            print(f"Error en el procesamiento de IA del frame: {e}")
            final_frame = frame 
            
        # 3. Codificar el frame como JPEG
        ret, buffer = cv2.imencode('.jpg', final_frame)
        if not ret:
            print("Error al codificar frame como JPEG")
            continue
            
        frame_bytes = buffer.tobytes()
        
        # 4. entrega el frame al navegador
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# Ruta para el Stream de Video
@app.route('/video_feed')
def video_feed():
    """
    Esta es la ruta que el <img> en 'live.html' llama para obtener el stream de video
    """
    return Response(generate_frames(), 
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# Limpieza al cerrar la app
@atexit.register
def shutdown_app():
    """Asegura que la cámara se libere cuando la app se cierra (Ctrl+C)."""
    print("Cerrando la aplicación...")
    cam.stop()

if __name__ == '__main__':
    app.run(debug=False, port=5000, threaded=True, use_reloader=False)