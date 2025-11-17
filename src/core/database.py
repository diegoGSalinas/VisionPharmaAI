import mysql.connector
from mysql.connector import pooling
import threading
from .models import InspectionReportDTO

class DatabaseConnection:
    """
    Clase Singleton para manejar la conexión a la base de datos MySQL
    
    Utiliza un pool de conexiones para ser eficiente en un entorno web (Flask)
    """
    _instance = None
    _pool = None
    _lock = threading.Lock() # Para seguridad en hilos (thread-safety)

    # Configuración de MySQL 
    DB_NAME = "visionpharma_db"
    DB_USER = "root"
    DB_PASS = ""
    DB_HOST = "localhost"
    DB_PORT = 3306

    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseConnection, cls).__new__(cls)
                    cls._instance._initialize_pool()
        return cls._instance

    def _initialize_pool(self):
        try:
            print(f"Creando pool de conexiones para MySQL: {self.DB_NAME} en {self.DB_HOST}...")
            pool_config = {
                "pool_name": "visionpharma_pool",
                "pool_size": 5,
                "database": self.DB_NAME,
                "user": self.DB_USER,
                "password": self.DB_PASS,
                "host": self.DB_HOST,
                "port": self.DB_PORT
            }
            DatabaseConnection._pool = mysql.connector.pooling.MySQLConnectionPool(**pool_config)
            print("Pool de conexiones MySQL creado exitosamente")
        except mysql.connector.Error as error:
            print(f"Error al inicializar el pool de conexiones MySQL: {error}")
            DatabaseConnection._pool = None

    def get_connection(self):
        """Obtiene una conexión del pool"""
        if DatabaseConnection._pool is None:
            print("Pool no inicializado, intentando reconectar...")
            self._initialize_pool()
        
        if DatabaseConnection._pool:
            try:
                return DatabaseConnection._pool.get_connection()
            except mysql.connector.Error as e:
                print(f"Error al obtener conexión del pool MySQL: {e}")
                return None
        return None

    def release_connection(self, conn):
        """Devuelve una conexión al pool"""
        if conn:
            try:
                conn.close()
            except mysql.connector.Error as e:
                print(f"Error al devolver la conexión al pool: {e}")

    def initialize(self):
        """
        Crea la tabla 'inspections' si no existe
        en la base de datos MySQL.
        """
        create_table_command = """
            CREATE TABLE IF NOT EXISTS inspections (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                total_pastillas INT NOT NULL,
                total_vacios INT NOT NULL,
                estado_final VARCHAR(50) NOT NULL,
                imagen_resultado VARCHAR(255)
            )
        """
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as c:
                    c.execute(create_table_command)
                conn.commit()
                print("Tabla 'inspections' inicializada en MySQL")
            except mysql.connector.Error as error:
                print(f"Error: {error}")
            finally:
                self.release_connection(conn)

    def save_inspection(self, inspection: InspectionReportDTO):
        """
        Guarda un DTO de reporte
        """
        insert_command = """
            INSERT INTO inspections (timestamp, total_pastillas, total_vacios, estado_final, imagen_resultado)
            VALUES (%s, %s, %s, %s, %s)
        """
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as c:
                    data_tuple = (
                        inspection.timestamp,
                        inspection.total_pastillas,
                        inspection.total_vacios,
                        inspection.estado_final,
                        inspection.imagen_resultado
                    )
                    c.execute(insert_command, data_tuple)
                conn.commit()
                print(f"DTO de Reporte guardado en MySQL: {inspection.timestamp}, {inspection.estado_final}")
            except mysql.connector.Error as error:
                print(f"Error al guardar DTO en MySQL: {error}")
                conn.rollback()
            finally:
                self.release_connection(conn)