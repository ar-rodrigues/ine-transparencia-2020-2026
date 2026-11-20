#!/usr/bin/env python3
"""
Utilidad: Exportador de Archivos Parquet a CSV / JSON
Proyecto: Repositorio de Auditoría y Análisis de Personal — INE

Permite exportar bajo demanda cualquiera o todas las tablas de la capa
03_datos_agregados a formatos abiertos descargables (CSV, JSON) para usuarios
o integración con APIs y herramientas de visualización web.

Uso:
    python3 scripts/utilidades/exportar_agregados.py [--formato csv|json] [--origen ruta]
"""

import argparse
import sys
from pathlib import Path
import duckdb

BASE_DIR = Path(__file__).resolve().parents[2]
AGREGADOS_DIR = BASE_DIR / "datos_b2" / "03_datos_agregados"

def exportar_tablas(formato="csv", origen_dir=None, destino_dir=None):
    origen = Path(origen_dir) if origen_dir else AGREGADOS_DIR
    formato = formato.lower()
    
    if formato not in ["csv", "json"]:
        print(f"Error: Formato '{formato}' no soportado. Usa 'csv' o 'json'.")
        sys.exit(1)

    parquets = list(origen.glob("**/*.parquet"))
    if not parquets:
        print(f"No se encontraron archivos .parquet en {origen}")
        return

    print(f"Exportando {len(parquets)} tablas analíticas a formato .{formato}...")
    conn = duckdb.connect()

    for p in parquets:
        rel_path = p.relative_to(origen)
        if destino_dir:
            out_file = Path(destino_dir) / rel_path.with_suffix(f".{formato}")
        else:
            out_file = p.with_suffix(f".{formato}")
            
        out_file.parent.mkdir(parents=True, exist_ok=True)
        
        if formato == "csv":
            conn.execute(f"COPY (SELECT * FROM '{p}') TO '{out_file}' (HEADER, DELIMITER ',')")
        elif formato == "json":
            conn.execute(f"COPY (SELECT * FROM '{p}') TO '{out_file}' (ARRAY true)")
            
        print(f"  ✓ {p.name} -> {out_file.name}")

    conn.close()
    print("¡Exportación completada exitosamente!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Exporta tablas parquet a CSV o JSON.")
    parser.add_argument("--formato", choices=["csv", "json"], default="csv", help="Formato de salida (csv o json)")
    parser.add_argument("--origen", default=None, help="Directorio origen (por defecto 03_datos_agregados)")
    parser.add_argument("--destino", default=None, help="Directorio destino (opcional)")
    
    args = parser.parse_args()
    exportar_tablas(formato=args.formato, origen_dir=args.origen, destino_dir=args.destino)
