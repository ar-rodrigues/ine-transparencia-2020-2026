#!/usr/bin/env python3
"""
Pipeline de Limpieza y Estandarización: Financiamiento a Partidos Políticos (2020-2026)
Fuente: 01_datos_crudos/**/43496_Montos_de_financiamiento_publico_y_privado_otorgado_a_p/
Destino: 02_datos_limpios/financiamiento_partidos/
"""

import os
import glob
import json
import re
import pandas as pd
import numpy as np

import unicodedata

def normalizar_siglas_partido(nombre: str) -> str:
    """Estandariza los nombres de partidos políticos a siglas oficiales y claras."""
    if not isinstance(nombre, str) or not nombre.strip():
        return "SIN_ESPECIFICAR"
    
    # Quitar acentos para coincidencias robustas
    n = unicodedata.normalize("NFKD", nombre).encode("ascii", "ignore").decode("utf-8").upper().strip()
    
    if "ACCION NACIONAL" in n or n == "PAN":
        return "PAN"
    if "REVOLUCIONARIO INSTITUCIONAL" in n or n == "PRI":
        return "PRI"
    if "REVOLUCION DEMOCRATICA" in n or n == "PRD":
        return "PRD"
    if "VERDE ECOLOGISTA" in n or n == "PVEM":
        return "PVEM"
    if "DEL TRABAJO" in n or n == "PT":
        return "PT"
    if "MOVIMIENTO CIUDADANO" in n or n == "MC":
        return "MC"
    if "MORENA" in n:
        return "MORENA"
    if "ENCUENTRO SOLIDARIO" in n or n == "PES":
        return "PES"
    if "REDES SOCIALES PROGRESISTAS" in n or n == "RSP":
        return "RSP"
    if "FUERZA POR MEXICO" in n or "FUERZA SOCIAL POR MEXICO" in n or n == "FXM":
        return "FXM"
    if "CANDIDATO INDEPENDIENTE" in n:
        return "CANDIDATO_INDEPENDIENTE"
    return "AGRUPACION_CIUDADANA"

MES_A_NUM = {
    "ENERO": 1, "FEBRERO": 2, "MARZO": 3, "ABRIL": 4,
    "MAYO": 5, "JUNIO": 6, "JULIO": 7, "AGOSTO": 8,
    "SEPTIEMBRE": 9, "OCTUBRE": 10, "NOVIEMBRE": 11, "DICIEMBRE": 12
}

def limpiar_fecha(val):
    if not val or pd.isna(val) or str(val).strip() == "":
        return None
    val_str = str(val).strip()
    # Tomar la parte de fecha YYYY-MM-DD
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", val_str)
    if match:
        return match.group(1)
    return val_str

def limpiar_monto(val):
    if val is None or pd.isna(val):
        return np.nan
    val_str = str(val).strip().replace("$", "").replace(",", "")
    if val_str == "" or val_str in ["-", "N/A", "ND", "None"]:
        return np.nan
    try:
        return float(val_str)
    except ValueError:
        return np.nan

def ejecutar_limpieza():
    print("=" * 70)
    print("INICIANDO LIMPIEZA: Financiamiento a Partidos Políticos (2020-2026)")
    print("=" * 70)

    patron = "datos_b2/01_datos_crudos/**/43496_Montos_de_financiamiento_publico_y_privado_otorgado_a_p/buscador_solicitudes_43496_parte1.json"
    archivos = sorted(glob.glob(patron, recursive=True))

    if not archivos:
        raise FileNotFoundError(f"No se encontraron archivos crudos en: {patron}")

    registros = []
    columnas_estandar = [
        "ejercicio",
        "fecha_inicio_periodo",
        "fecha_fin_periodo",
        "proceso_electoral",
        "mes",
        "tipo_sujeto_obligado",
        "denominacion_partido_agrupacion",
        "candidato_nombre",
        "candidato_primer_apellido",
        "candidato_segundo_apellido",
        "tipo_financiamiento",
        "monto_mensual",
        "monto_anual",
        "area_responsable",
        "fecha_validacion",
        "fecha_actualizacion",
        "nota"
    ]

    for ruta in archivos:
        ejercicio_dir = ruta.split("/")[1].replace("FED_INE_", "")
        print(f"-> Procesando ejercicio {ejercicio_dir} desde: {ruta}")
        with open(ruta, "r", encoding="utf-8") as fp:
            data = json.load(fp)

        cols = [c.strip() for c in data.get("columnas", [])]
        filas = data.get("filas", [])

        # Corregir anomalía de 2020 donde existe una columna duplicada en índice 6
        if len(cols) == 18 and cols[5] == cols[6]:
            filas = [r[:6] + r[7:] for r in filas]

        for fila in filas:
            if len(fila) < 17:
                # Rellenar si faltan columnas
                fila = fila + [""] * (17 - len(fila))
            elif len(fila) > 17:
                fila = fila[:17]
            registros.append(fila)

    df = pd.DataFrame(registros, columns=columnas_estandar)
    print(f"\nTotal registros brutos combinados: {len(df)}")

    # 1. Limpieza de texto básica (quitar espacios en blanco superfluos)
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    # 2. Tipado de ejercicio
    df["ejercicio"] = pd.to_numeric(df["ejercicio"], errors="coerce").fillna(0).astype(int)

    # 3. Mes y número de mes
    df["mes_nombre"] = df["mes"].str.capitalize()
    df["mes_numero"] = df["mes"].str.upper().map(MES_A_NUM).fillna(0).astype(int)

    # 4. Siglas normalizadas de partidos
    df["partido_siglas"] = df["denominacion_partido_agrupacion"].apply(normalizar_siglas_partido)

    # 5. Limpieza de montos monetarios
    df["monto_mensual"] = df["monto_mensual"].apply(limpiar_monto)
    df["monto_anual"] = df["monto_anual"].apply(limpiar_monto)

    # 6. Limpieza de fechas
    for fcol in ["fecha_inicio_periodo", "fecha_fin_periodo", "fecha_validacion", "fecha_actualizacion"]:
        df[fcol] = df[fcol].apply(limpiar_fecha)

    # 7. Deduplicación estricta
    filas_antes = len(df)
    df = df.drop_duplicates()
    duplicados_eliminados = filas_antes - len(df)
    if duplicados_eliminados > 0:
        print(f"Se eliminaron {duplicados_eliminados} registros duplicados exactos.")

    # 8. Ordenamiento cronológico y por partido
    df = df.sort_values(by=["ejercicio", "mes_numero", "partido_siglas"]).reset_index(drop=True)

    # Reordenar columnas para máxima legibilidad humana
    columnas_ordenadas = [
        "ejercicio",
        "mes_numero",
        "mes_nombre",
        "partido_siglas",
        "denominacion_partido_agrupacion",
        "monto_mensual",
        "monto_anual",
        "tipo_financiamiento",
        "proceso_electoral",
        "tipo_sujeto_obligado",
        "candidato_nombre",
        "candidato_primer_apellido",
        "candidato_segundo_apellido",
        "fecha_inicio_periodo",
        "fecha_fin_periodo",
        "area_responsable",
        "fecha_validacion",
        "fecha_actualizacion",
        "nota"
    ]
    df = df[columnas_ordenadas]

    # Carpeta de salida
    salida_dir = "datos_b2/02_datos_limpios/financiamiento_partidos"
    os.makedirs(salida_dir, exist_ok=True)

    ruta_parquet = os.path.join(salida_dir, "financiamiento_partidos_2020_2026.parquet")
    ruta_csv = os.path.join(salida_dir, "financiamiento_partidos_2020_2026.csv")

    df.to_parquet(ruta_parquet, index=False, engine="pyarrow", compression="snappy")
    df.to_csv(ruta_csv, index=False, encoding="utf-8")

    peso_parquet = os.path.getsize(ruta_parquet) / 1024
    peso_csv = os.path.getsize(ruta_csv) / 1024

    print("\n" + "=" * 70)
    print("PROCESO COMPLETADO EXITOSAMENTE")
    print("=" * 70)
    print(f"Total registros limpios generados: {len(df):,}")
    print(f"Archivo Parquet (optimizado): {ruta_parquet} ({peso_parquet:.1f} KB)")
    print(f"Archivo CSV (apto para Excel): {ruta_csv} ({peso_csv:.1f} KB)")

    # Estadísticas ejecutivas resumidas
    print("\n--- Desglose por Ejercicio Fiscal ---")
    resumen_ejercicio = df.groupby("ejercicio").agg(
        registros=("monto_mensual", "count"),
        monto_mensual_total=("monto_mensual", "sum")
    )
    resumen_ejercicio["monto_mensual_total_formato"] = resumen_ejercicio["monto_mensual_total"].apply(lambda x: f"${x:,.2f}")
    print(resumen_ejercicio[["registros", "monto_mensual_total_formato"]])

    print("\n--- Top Fuerzas Políticas por Financiamiento Acumulado ---")
    resumen_partidos = df[df["partido_siglas"].ne("SIN_ESPECIFICAR")].groupby("partido_siglas").agg(
        total_mensual=("monto_mensual", "sum"),
        meses_registrados=("mes_numero", "count")
    ).sort_values(by="total_mensual", ascending=False)
    resumen_partidos["total_mensual_formato"] = resumen_partidos["total_mensual"].apply(lambda x: f"${x:,.2f}")
    print(resumen_partidos[["meses_registrados", "total_mensual_formato"]])

if __name__ == "__main__":
    ejecutar_limpieza()
