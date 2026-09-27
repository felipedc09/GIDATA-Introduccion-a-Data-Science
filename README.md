# Avance 1 — Base de datos histórica de los Mundiales FIFA

## Integrantes
- Felipe (@felipedc09) — completar con el resto del equipo

## Descripción del proyecto
Este avance construye la base del proyecto final del curso: una base de
datos relacional en MySQL que almacena el histórico de los Mundiales
FIFA (masculino y femenino) y un conjunto de scripts en Python que
cargan esa información de forma automatizada desde archivos CSV.

En esta etapa **no** se evalúan dashboards, Machine Learning ni
desarrollo web; el foco es la organización de los datos y la
automatización de la carga con Python.

Los datos crudos provienen del dataset público
[`jfjelstul/worldcup`](https://github.com/jfjelstul/worldcup) (Jason
Fjelstul), que cubre todos los Mundiales masculinos (1930–2022) y
femeninos (1991–2023). A partir de esos CSV "anchos" se construyó un
modelo relacional normalizado con las 15 tablas pedidas en el
enunciado.

## Tecnologías utilizadas
- **MySQL 8.0+** — motor de base de datos relacional.
- **Python 3.10+**
  - `pandas` — lectura, limpieza y transformación de los CSV.
  - `mysql-connector-python` — conexión y carga a MySQL.
  - `python-dotenv` — manejo de credenciales por variables de entorno.

## Estructura del repositorio

```
Proyecto final/avance1/
├── README.md                  <- este archivo
├── sql/
│   └── schema.sql              <- DDL: crea la BD y las 15 tablas con PK/FK
├── data/                        <- CSV de origen (dataset jfjelstul/worldcup)
│   ├── awards.csv
│   ├── award_winners.csv
│   ├── confederations.csv
│   ├── goals.csv
│   ├── matches.csv
│   ├── player_appearances.csv
│   ├── players.csv
│   ├── stadiums.csv
│   ├── teams.csv
│   └── tournaments.csv
└── scripts/
    ├── requirements.txt
    ├── .env.example            <- plantilla de variables de conexión
    ├── db_config.py            <- lee la configuración de conexión
    ├── extract_transform.py    <- E+T: arma los 15 DataFrames normalizados
    └── load_data.py            <- carga los DataFrames a MySQL en orden de FK
```

## Modelo de datos

15 tablas, con llaves primarias, llaves foráneas e integridad
referencial:

- **Catálogos base:** `confederation`, `region`, `federation`,
  `country`, `position`, `award`, `player`
- **Nivel 2:** `city` (→ `country`), `team` (→ `federation`, `region`,
  `confederation`)
- **Nivel 3:** `stadium` (→ `city`), `tournament` (→ `country`, `team`)
- **Nivel 4:** `matches` (→ `tournament`, `stadium`, `team`), `goal`
  (→ `matches`, `team`, `player`), `player_appearance` (→ `matches`,
  `team`, `player`, `position`), `award_winner` (→ `tournament`,
  `award`, `player`, `team`)

El diagrama entidad-relación completo puede regenerarse desde
`sql/schema.sql` con cualquier herramienta de modelado (MySQL
Workbench, dbdiagram.io, etc.).

## Instrucciones para ejecutar la base de datos

1. Tener un servidor MySQL 8.0+ corriendo (local o en contenedor).
2. Ejecutar el script de esquema, que crea la base de datos `worldcup`
   y las 15 tablas:

   ```bash
   mysql -u root -p < sql/schema.sql
   ```

   Esto elimina y vuelve a crear la base `worldcup` desde cero
   (`DROP DATABASE IF EXISTS` + `CREATE DATABASE`).

## Instrucciones para ejecutar los scripts de carga

1. Crear un entorno virtual e instalar dependencias:

   ```bash
   cd scripts
   python3 -m venv venv
   source venv/bin/activate      # En Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Copiar `.env.example` a `.env` y completar las credenciales de tu
   MySQL local:

   ```bash
   cp .env.example .env
   ```

3. Ejecutar la carga completa:

   ```bash
   python load_data.py
   ```

   El script:
   - Lee los CSV de `data/` con Pandas y los limpia (tipos de dato,
     valores `"not applicable"` → `NULL`, espacios en blanco,
     duplicados).
   - Construye en memoria los 15 DataFrames normalizados
     (`extract_transform.py`).
   - Vacía las tablas (`TRUNCATE`) y las vuelve a poblar en el orden
     correcto según las llaves foráneas.
   - Imprime en consola, tabla por tabla, si la carga fue exitosa
     (`[OK]`) o si falló (`[FAIL]`) junto con el número de filas
     insertadas, y un resumen final.

   Para verificar rápidamente la extracción/transformación sin tocar
   la base de datos:

   ```bash
   python extract_transform.py
   ```

## Solución de problemas

**`mysql.connector.errors.OperationalError: 1153 (08S01): Got a packet
bigger than 'max_allowed_packet' bytes`** (suele aparecer al cargar
`player_appearance`, la tabla más grande con ~27 000 filas):

`executemany` envía todas las filas de una tabla en un único paquete
`INSERT ... VALUES (...),(...),...`, y el límite por defecto de
`max_allowed_packet` en MySQL/MariaDB (a veces 1M–16M según la
instalación) puede quedarse corto para eso. Para solucionarlo, aumenta
el límite en el servidor:

- **XAMPP (Windows):** edita `C:\xampp\mysql\bin\my.ini`, en la
  sección `[mysqld]` agrega o actualiza:

  ```ini
  max_allowed_packet=64M
  ```

  y reinicia MySQL desde el panel de control de XAMPP.

- **MySQL/MariaDB en Linux/contenedor:** el equivalente es editar
  `my.cnf` (sección `[mysqld]`) con la misma línea y reiniciar el
  servicio, o pasar `--max_allowed_packet=64M` al arrancarlo.

