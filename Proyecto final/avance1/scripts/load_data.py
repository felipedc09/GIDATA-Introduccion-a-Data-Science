"""
Carga los DataFrames normalizados (extract_transform.build_all) en
MySQL, respetando el orden de dependencias de claves foráneas.

Uso:
    python load_data.py

Requiere que el esquema ya exista (ver sql/schema.sql) y que las
variables de conexión estén configuradas (ver db_config.py / .env).
"""

import sys

import mysql.connector
import pandas as pd
from mysql.connector import Error as MySQLError

from db_config import DB_CONFIG
from extract_transform import build_all

# Orden de carga: cada tabla se inserta después de las tablas de las
# que depende por llave foránea.
LOAD_ORDER = [
    "confederation",
    "region",
    "federation",
    "country",
    "position",
    "award",
    "player",
    "city",
    "team",
    "stadium",
    "tournament",
    "matches",
    "goal",
    "player_appearance",
    "award_winner",
]

# Tablas cuya PK es AUTO_INCREMENT: no enviamos la columna *_id.
AUTOINCREMENT_TABLES = {
    "region", "federation", "country", "position", "city",
    "player_appearance", "award_winner",
}


def _clean_value(value):
    if pd.isna(value):
        return None
    # numpy/pandas Int64 -> int nativo para el conector de MySQL
    if hasattr(value, "item"):
        return value.item()
    return value


def _insert_dataframe(cursor, table: str, df: pd.DataFrame) -> int:
    if table in AUTOINCREMENT_TABLES:
        id_col = f"{table}_id"
        columns = [c for c in df.columns if c != id_col]
    else:
        columns = list(df.columns)

    placeholders = ", ".join(["%s"] * len(columns))
    col_list = ", ".join(f"`{c}`" for c in columns)
    sql = f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})"

    rows = [
        tuple(_clean_value(row[c]) for c in columns)
        for _, row in df.iterrows()
    ]

    cursor.executemany(sql, rows)
    return cursor.rowcount


def load_all(truncate_first: bool = True) -> None:
    print("Extrayendo y transformando los CSV de origen...")
    tables = build_all()

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
    except MySQLError as exc:
        print(f"[ERROR] No fue posible conectar a MySQL: {exc}")
        sys.exit(1)

    cursor = conn.cursor()
    print(f"Conectado a la base de datos '{DB_CONFIG['database']}' en {DB_CONFIG['host']}.")

    if truncate_first:
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0")
        for table in reversed(LOAD_ORDER):
            cursor.execute(f"TRUNCATE TABLE `{table}`")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
        conn.commit()
        print("Tablas vaciadas antes de la carga (TRUNCATE).\n")

    total_ok, total_fail = 0, 0

    for table in LOAD_ORDER:
        df = tables[table]
        try:
            inserted = _insert_dataframe(cursor, table, df)
            conn.commit()
            print(f"[OK]   {table:20s} -> {inserted:6d} filas cargadas exitosamente")
            total_ok += 1
        except MySQLError as exc:
            conn.rollback()
            print(f"[FAIL] {table:20s} -> error al cargar: {exc}")
            total_fail += 1

    cursor.close()
    conn.close()

    print("\nResumen de carga:")
    print(f"  Tablas cargadas con éxito: {total_ok}/{len(LOAD_ORDER)}")
    print(f"  Tablas con error:          {total_fail}/{len(LOAD_ORDER)}")

    if total_fail:
        sys.exit(1)


if __name__ == "__main__":
    load_all()
