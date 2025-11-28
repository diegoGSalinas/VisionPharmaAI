import cv2
import threading
import time

class CameraStream:
    """
    Clase Singleton para manejar la cámara en un hilo separado
    
    Para que Flask (múltiples hilos) pueda 
    acceder a la cámara sin conflictos
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls, camera_index=0):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(CameraStream, cls).__new__(cls)
                    cls._instance.cap = None
                    cls._instance.camera_index = camera_index
                    cls._instance.frame = None # frame actual
                    cls._instance.running = False # control hilo
                    cls._instance.read_lock = threading.Lock() # accede al frame
        return cls._instance

    def _initialize_camera(self):
        """Intenta conexión de la cámara"""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                print(f"Error: No se pudo abrir la cámara en el índice {self.camera_index}")
                self.cap = None
            else:
                print(f"Cámara en índice {self.camera_index} abierta exitosamente")
                self.running = True
        except Exception as e:
            print(f"Excepción al abrir la cámara: {e}")
            self.cap = None

    def _read_loop(self):
        """
        Bucle que se ejecuta en un hilo separado
        Su función es leer fotogramas de la cámara
        """
        while self.running:
            if self.cap:
                ret, frame = self.cap.read()
                if ret:
                    # Guardar el frame de forma segura (thread-safe)
                    with self.read_lock:
                        self.frame = frame
                else:
                    # Si falla la lectura, intenta reconectar
                    print("Error leyendo frame, intentando reconectar cámara...")
                    self.cap.release()
                    time.sleep(1)
                    self._initialize_camera()
            else:
                time.sleep(1)

    def start(self):
        """
        Inicia el hilo de lectura de la cámara
        """
        if self.running:
            print("El hilo de la cámara ya está corriendo")
            return

        if self.cap is None:
            self._initialize_camera()
            if self.cap is None:
                return # No pudo iniciar

        # Crear e iniciar el hilo daemon
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
        print("Hilo de lectura de cámara iniciado")

    def get_frame(self):
        """
        Copia el último frame que el hilo guardó
        (rápido y seguro para Flask)
        """
        frame_copy = None
        with self.read_lock:
            if self.frame is not None:
                frame_copy = self.frame.copy()
        return frame_copy

    def stop(self):
        """
        Detiene el hilo y libera la cámara
        """
        print("Deteniendo hilo de cámara...")
        self.running = False
        if self.thread:
            self.thread.join()
        
        if self.cap:
            print("Liberando recurso de la cámara...")
            self.cap.release()
            self.cap = None

    def __del__(self):
        """Asegurarse de liberar la cámara"""
        self.stop()