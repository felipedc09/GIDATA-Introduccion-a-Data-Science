"""
Configuración de conexión a MySQL.

Las credenciales se leen de variables de entorno (o de un archivo .env
en la raíz de `scripts/`) para no exponer contraseñas en el código.
Ver `.env.example` para la lista de variables esperadas.
"""

import os

from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "worldcup"),
}
