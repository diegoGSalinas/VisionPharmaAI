VisionPharmaAI
# VisionPharma 2025 (CNN) - Guía de Uso Rápida

Este proyecto utiliza una Red Neuronal Convolucional (YOLOv8) para la inspección de calidad en blísteres farmacéuticos. Sigue estos pasos para configurar y ejecutar el software.

# Prerrequisitos

Asegúrate de tener instalado lo siguiente antes de comenzar:

Python 3.11+: Descargar Python
MySQL Server: Debe estar instalado y ejecutándose.
Crea una base de datos llamada: visionpharma_db
Usuario por defecto configurado en el código: root (sin contraseña).

# Instalación y Configuración

Sigue estos pasos en tu terminal (PowerShell o CMD) dentro de la carpeta del proyecto:

# 1. Crear el Entorno Virtual (venv)

Crea un entorno aislado para instalar las librerías sin afectar tu sistema.

# Opción A: Usando el comando python
python -m venv venv311

# Opción B: Si tienes múltiples versiones (o Python Launcher)
py -m venv venv311


# 2. Activar el Entorno Virtual

Debes hacer esto cada vez que abras una nueva terminal para trabajar en el proyecto.

# En Windows (PowerShell)
.\venv311\Scripts\activate

# En Windows (CMD)
venv311\Scripts\activate


(Verás (venv311) al inicio de tu línea de comandos cuando esté activo)

# 3. Instalar Dependencias

Instala todas las librerías necesarias (Flask, OpenCV, YOLO, MySQL, etc.) automáticamente.

pip install -r requirements.txt


# 4. Colocar el Modelo de IA

Asegúrate de tener el archivo best.pt (modelo entrenado) en la carpeta raíz del proyecto (junto a app_cnn.py).

# Ejecución del Software

Tienes dos aplicaciones disponibles. Ejecuta solo una a la vez.

# Opción A: Aplicación Principal (Web + BD + Análisis)

Esta es la aplicación completa para producción. Permite subir imágenes para análisis y guarda los reportes en la base de datos MySQL.

python app_cnn.py


Acceso Web: Abre tu navegador en http://127.0.0.1:5000

# Opción B: Aplicación de Prueba en Vivo (Solo Cámara)

Esta aplicación es ligera y sirve exclusivamente para probar la detección en tiempo real con tu cámara web. No guarda datos en la BD.

python app_live.py

Ver Cámara: Abre tu navegador en http://127.0.0.1:5000/live

# Solución de Problemas Comunes

Error: "ModuleNotFoundError": Asegúrate de haber activado tu entorno virtual (activate) antes de ejecutar python.

Error de Conexión a Base de Datos: Verifica que XAMPP o MySQL Server estén corriendo y que la base de datos visionpharma_db exista. Revisa src/core/database.py si tu usuario/contraseña son diferentes.

Error de Cámara: Asegúrate de que ninguna otra aplicación (Zoom, Teams, u otra instancia de Python) esté usando tu cámara web.
