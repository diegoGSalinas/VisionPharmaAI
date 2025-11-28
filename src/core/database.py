import mysql.connector
from mysql.connector import pooling
import threading
from .models import InspectionReportDTO

class DatabaseConnection:
    _instance = None
    _pool = None
    _lock = threading.Lock()

    DB_NAME = "visionpharma_db"
    DB_USER = "root"            
    DB_PASS = ""           
    DB_HOST = "localhost"
    DB_PORT = 3306

    def __new__(cls):
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
            print(f"Error fatal al inicializar el pool de conexiones MySQL: {error}")
            DatabaseConnection._pool = None

    def get_connection(self):
        if DatabaseConnection._pool is None:
            self._initialize_pool()
        if DatabaseConnection._pool:
            try:
                return DatabaseConnection._pool.get_connection()
            except mysql.connector.Error as e:
                return None
        return None

    def release_connection(self, conn):
        if conn:
            try:
                conn.close() 
            except mysql.connector.Error:
                pass

    def initialize(self):
        create_table_command = """
            CREATE TABLE IF NOT EXISTS inspections (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME NOT NULL,
                total_pastillas INT NOT NULL,
                total_vacios INT NOT NULL,
                estado_final VARCHAR(50) NOT NULL,
                imagen_resultado VARCHAR(255),
                imagen_resultado_clean VARCHAR(255)
            )
        """
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as c:
                    c.execute(create_table_command)
                
                    try:
                        c.execute("ALTER TABLE inspections ADD COLUMN imagen_resultado_clean VARCHAR(255)")
                        print("Columna 'imagen_resultado_clean' añadida exitosamente.")
                    except mysql.connector.Error:
                        pass
                        
                conn.commit()
                print("Tabla 'inspections' inicializada en MySQL si no existía")
            except mysql.connector.Error as error:
                print(f"Error during table initialization: {error}")
            finally:
                self.release_connection(conn)

    def save_inspection(self, inspection: InspectionReportDTO):
        insert_command = """
            INSERT INTO inspections (timestamp, total_pastillas, total_vacios, estado_final, imagen_resultado, imagen_resultado_clean)
            VALUES (%s, %s, %s, %s, %s, %s)
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
                        inspection.imagen_resultado,
                        inspection.imagen_resultado_clean
                    )
                    c.execute(insert_command, data_tuple)
                conn.commit()
                print(f"DTO de Reporte guardado en MySQL: {inspection.timestamp}")
            except mysql.connector.Error as error:
                print(f"Error al guardar DTO en MySQL: {error}")
                conn.rollback()
            finally:
                self.release_connection(conn)

    def get_all_inspections(self):
        select_command = "SELECT * FROM inspections ORDER BY timestamp DESC"
        results = []
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor(dictionary=True) as c:
                    c.execute(select_command)
                    results = c.fetchall()
            except mysql.connector.Error as error:
                print(f"Error get_all: {error}")
            finally:
                self.release_connection(conn)
        return results

    # Dashboard Stats Methods
    def get_stats_pie_chart(self):
        query = "SELECT estado_final, COUNT(*) as count FROM inspections GROUP BY estado_final"
        stats = {'Aprobado': 0, 'Defectuoso': 0}
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as c:
                    c.execute(query)
                    for row in c.fetchall():
                        stats[row[0]] = row[1]
            except mysql.connector.Error: pass
            finally: self.release_connection(conn)
        return stats

    def get_stats_line_chart(self, mode='day'):
        sql_format = '%Y-%m-%d %H:00:00' if mode == 'hour' else '%Y-%m-%d'
        query = f"SELECT DATE_FORMAT(timestamp, '{sql_format}') as fecha, SUM(total_pastillas), SUM(total_vacios) FROM inspections GROUP BY fecha ORDER BY fecha ASC LIMIT 30"
        data = []
        conn = self.get_connection()
        if conn:
            try:
                with conn.cursor() as c:
                    c.execute(query)
                    for row in c.fetchall():
                        pills = int(row[1]) if row[1] else 0
                        empty = int(row[2]) if row[2] else 0
                        data.append({'fecha': row[0], 'pastillas': pills, 'vacios': empty})
            except mysql.connector.Error: pass
            finally: self.release_connection(conn)
        return data
    
    def get_kpis(self):
        conn = self.get_connection()
        kpis = {'total_inspections': 0, 'total_pills': 0, 'total_defects': 0, 'efficiency': 0}
        if conn:
            try:
                with conn.cursor() as c:
                    c.execute("SELECT COUNT(*) FROM inspections")
                    kpis['total_inspections'] = c.fetchone()[0]
                    c.execute("SELECT SUM(total_pastillas) FROM inspections")
                    res = c.fetchone()[0]; kpis['total_pills'] = res if res else 0
                    c.execute("SELECT COUNT(*) FROM inspections WHERE estado_final = 'Defectuoso'")
                    defects = c.fetchone()[0]; kpis['total_defects'] = defects
                    if kpis['total_inspections'] > 0:
                        eff = ((kpis['total_inspections'] - defects) / kpis['total_inspections']) * 100
                        kpis['efficiency'] = round(eff, 1)
                    else: kpis['efficiency'] = 100
            except mysql.connector.Error: pass
            finally: self.release_connection(conn)
        return kpis