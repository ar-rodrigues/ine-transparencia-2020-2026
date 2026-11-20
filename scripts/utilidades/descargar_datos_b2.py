#!/usr/bin/env python3
"""
Utilidad: Descargador Oficial de Carpetas de Datos — Observatorio INE (2020–2026)
AGIL Solutions · Inteligencia de Datos

Permite descargar bajo demanda los conjuntos de datos del proyecto desde Backblaze B2:
  - 03_datos_agregados (~160 KB) : 21 tablas analíticas y KPIs precalculados (Parquet/JSON)
  - 02_datos_limpios   (~122 MB) : Bases deduplicadas y normalizadas (125k contratos, nómina, viáticos)
  - 01_datos_crudos    (~1.5 GB) : JSONs y CSVs crudos originales descargados de la PNT

Uso:
  python3 scripts/utilidades/descargar_datos_b2.py --capa agregados
  python3 scripts/utilidades/descargar_datos_b2.py --capa limpios
  python3 scripts/utilidades/descargar_datos_b2.py --capa crudos
  python3 scripts/utilidades/descargar_datos_b2.py --capa todas
"""

import os
import sys
import argparse
from pathlib import Path

try:
    import boto3
    from botocore import UNSIGNED
    from botocore.config import Config
except ImportError:
    print("Error: Se requiere 'boto3'. Instálalo con: pip install boto3")
    sys.exit(1)

BASE_DIR = Path(__file__).resolve().parents[2]
DATOS_DIR = BASE_DIR / "datos_b2"

# Parámetros públicos del bucket (S3 compatible)
DEFAULT_ENDPOINT = "https://s3.us-east-005.backblazeb2.com"
DEFAULT_BUCKET = "ine-data-lake"

PREFIXES = {
    "agregados": "03_datos_agregados/",
    "limpios": "02_datos_limpios/",
    "crudos": "01_datos_crudos/",
    "oro": "03_datos_agregados/",
    "plata": "02_datos_limpios/",
    "bronce": "01_datos_crudos/",
}

def obtener_cliente_s3():
    # 1. Intentar leer credenciales desde variables de entorno o .env.local
    env_file = BASE_DIR / ".env.local"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k, v)

    endpoint = os.getenv("B2_ENDPOINT", DEFAULT_ENDPOINT)
    key_id = os.getenv("B2_APPLICATION_KEY_ID")
    key = os.getenv("B2_APPLICATION_KEY")

    if key_id and key:
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=key_id,
            aws_secret_access_key=key,
        )
    else:
        # Descarga pública sin firma (requiere bucket público)
        return boto3.client(
            "s3",
            endpoint_url=endpoint,
            config=Config(signature_version=UNSIGNED),
        )

def descargar_prefijo(s3, bucket, prefix, destino_dir):
    print(f"\n📦 Descargando prefijo: {prefix}")
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket, Prefix=prefix)

    descargados = 0
    total_bytes = 0

    for page in pages:
        contents = page.get("Contents", [])
        for item in contents:
            key = item["Key"]
            size = item["Size"]
            if key.endswith("/"):
                continue

            rel_path = Path(key)
            out_file = destino_dir / rel_path
            out_file.parent.mkdir(parents=True, exist_ok=True)

            print(f"  ↓ {key} ({size / (1024*1024):.2f} MB)...", end="\r")
            s3.download_file(bucket, key, str(out_file))
            descargados += 1
            total_bytes += size

    print(f"\n  ✓ {descargados} archivos descargados ({total_bytes / (1024*1024):.2f} MB)")

def main():
    parser = argparse.ArgumentParser(description="Descarga capas de datos del INE desde Backblaze B2.")
    parser.add_argument(
        "--capa",
        choices=["agregados", "limpios", "crudos", "todas", "oro", "plata", "bronce"],
        default="agregados",
        help="Conjunto de datos a descargar (agregados: ~160KB, limpios: ~122MB, crudos: ~1.5GB, todas: ~1.6GB)",
    )
    parser.add_argument("--destino", default=str(DATOS_DIR), help="Directorio local de destino")
    parser.add_argument("--bucket", default=os.getenv("B2_BUCKET_NAME", DEFAULT_BUCKET), help="Nombre del bucket B2")

    args = parser.parse_args()
    destino = Path(args.destino)
    destino.mkdir(parents=True, exist_ok=True)

    s3 = obtener_cliente_s3()

    capas = ["agregados", "limpios", "crudos"] if args.capa == "todas" else [args.capa]

    print("=" * 65)
    print("  OBSERVATORIO INE (2020–2026) · DESCARGADOR DE DATOS B2")
    print(f"  Bucket: {args.bucket} | Destino: {destino}")
    print("=" * 65)

    for c in capas:
        descargar_prefijo(s3, args.bucket, PREFIXES[c], destino)

    print("\n🎉 ¡Proceso finalizado con éxito!")

if __name__ == "__main__":
    main()
