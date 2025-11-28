# VisionPharma 2025: Sistema de Control de Calidad con IA

VisionPharma 2025 es un sistema de visión artificial diseñado para automatizar la inspección de calidad en líneas de producción farmacéutica. Utilizando redes neuronales convolucionales (CNN), el sistema detecta, cuenta y clasifica pastillas y defectos en tiempo real.

## Características Principales

* Inspección en Tiempo Real: Análisis de video en vivo desde cámaras industriales o webcams.
* Detección con IA: Utiliza el modelo YOLOv8 para identificar pastillas correctas y cavidades vacías con alta precisión.
* Disparador Automático (Auto-Trigger): El sistema captura y guarda la imagen automáticamente cuando detecta un blíster completo y estable.
* Persistencia de Datos: Todos los reportes se guardan automáticamente en una base de datos MySQL.
* Evidencia: Guarda dos imágenes por cada inspección:
* Dashboard Interactivo: Visualización de estadísticas de producción y calidad.
* Historial Completo: Acceso a registros pasados con filtrado y visualización de evidencia.

## Arquitectura Tecnológica

El proyecto sigue una arquitectura modular basada en servicios:

* Core de IA (cnn_inspector.py): Carga el modelo best.pt y ejecuta la inferencia.
* Servidor Web (main.py): Gestionado con Flask, sirve la interfaz de usuario y las APIs.
* Base de Datos (database.py): Singleton que gestiona un pool de conexiones a MySQL.
* Cámara (camera.py): Sistema thread-safe para la captura de video sin bloqueos.

## Prerrequisitos

Antes de iniciar, asegúrate de tener instalado:

* Python 3.11+
* MySQL Server (o XAMPP).
* Una cámara web conectada.

## Instalación y Configuración

Sigue estos pasos para desplegar el proyecto en un entorno local:

### 1. Clonar y Preparar el Entorno

Crear un entorno virtual

```python -m venv venv311```

Activar el entorno

Windows:

```.\venv311\Scripts\activate```

Linux/Mac:

```source venv311/bin/activate```


### 2. Instalar Dependencias

Instala todas las librerías necesarias (YOLO, Flask, OpenCV, etc.):

```pip install -r requirements.txt```


### 3. Configurar la Base de Datos

Asegúrate de que tu servicio MySQL esté corriendo.

Crea la base de datos:

```CREATE DATABASE visionpharma_db;```


(Opcional) Si tu usuario/contraseña de MySQL no es ```root``` / ```""```, edita el archivo ```src/core/database.py``` con tus credenciales.

### 4. Modelo de IA

Asegúrate de que el archivo best.pt (tu modelo entrenado) se encuentre en la carpeta raíz del proyecto.

## Ejecución

Para iniciar el sistema completo:

```python main.py```


Abre tu navegador y ve a: http://127.0.0.1:5000/

Selecciona "Captura en Vivo" para iniciar la inspección.

### Estructura del Proyecto

```
/VisionPharmaAI/
│
├── main.py                 # Aplicación Principal (Flask)
├── best.pt                 # Modelo de IA Entrenado
├── requirements.txt        # Lista de dependencias
│
├── src/
│   ├── core/               # Lógica de Negocio
│   │   ├── cnn_inspector.py
│   │   ├── database.py
│   │   ├── camera.py
│   │   └── models.py
│   │
│   └── web_interface/      # Frontend
│       └── templates/
│           ├── dashboard.html
│           ├── history.html
│           ├── index.html
│           ├── live.html
│           ├── upload.html
│
└── static/                 # Archivos Estáticos
    ├── img/                # Logos y recursos
    └── results/            # Evidencia generada

```
