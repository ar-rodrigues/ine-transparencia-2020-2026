#!/usr/bin/env python3
"""
Pipeline de Limpieza y Estandarización: Viáticos y Gastos de Representación (2022-2025)
Fuente: 01_datos_crudos/**/PA-07_viaticos/buscador_solicitudes_43316_parte1.json
Destino: 02_datos_limpios/viaticos/
"""

import os
import glob
import json
import re
import pandas as pd
import numpy as np

def limpiar_fecha(val):
    if not val or pd.isna(val) or str(val).strip() == "":
        return None
    val_str = str(val).strip()
    match = re.match(r"^(\d{4}-\d{2}-\d{2})", val_str)
    if match:
        return match.group(1)
    match_dmy = re.match(r"^(\d{2})/(\d{2})/(\d{4})", val_str)
    if match_dmy:
        d, m, y = match_dmy.groups()
        return f"{y}-{m}-{d}"
    return val_str

def limpiar_monto(val):
    if val is None or pd.isna(val):
        return 0.0
    val_str = str(val).strip().replace("$", "").replace(",", "")
    if val_str == "" or val_str in ["-", "N/A", "ND", "None"]:
        return 0.0
    try:
        return float(val_str)
    except ValueError:
        return 0.0

def procesar_viaticos():
    print("=" * 70)
    print("INICIANDO LIMPIEZA: Viáticos y Gastos de Representación del INE")
    print("=" * 70)
    
    patron = "datos_b2/01_datos_crudos/**/PA-07_viaticos/*.json"
    archivos = sorted(glob.glob(patron, recursive=True))
    
    all_filas = []
    for f in archivos:
        print(f"-> Leyendo: {f}")
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
            all_filas.extend(d.get("filas", []))
            
    print(f"Total comisiones cargadas: {len(all_filas):,}")
    
    cols = [
        "ejercicio", "fecha_inicio_periodo", "fecha_fin_periodo", "tipo_integrante",
        "clave_puesto", "denominacion_puesto", "cargo", "area_adscripcion",
        "nombres", "primer_apellido", "segundo_apellido", "sexo",
        "tipo_gasto", "encargo_comision", "tipo_viaje", "numero_acompanantes",
        "importe_acompanantes", "pais_origen", "estado_origen", "ciudad_origen",
        "pais_destino", "estado_destino", "ciudad_destino", "motivo_comision",
        "fecha_salida", "fecha_regreso", "importe_ejercido_partida",
        "importe_total_erogado", "gastos_no_erogados", "fecha_entrega_informe",
        "hipervinculo_informe", "hipervinculo_facturas", "hipervinculo_normativa",
        "area_responsable", "fecha_validacion", "fecha_actualizacion", "nota"
    ]
    
    df = pd.DataFrame(all_filas, columns=cols)
    
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
        
    df["ejercicio"] = pd.to_numeric(df["ejercicio"], errors="coerce").fillna(0).astype(int)
    
    # Nombre comisionado
    partes = zip(df["nombres"], df["primer_apellido"], df["segundo_apellido"])
    df["comisionado_nombre"] = [" ".join([p for p in pt if p and p != "None"]).strip() for pt in partes]
    
    # Fechas
    for dcol in ["fecha_salida", "fecha_regreso", "fecha_inicio_periodo", "fecha_fin_periodo", "fecha_entrega_informe", "fecha_validacion", "fecha_actualizacion"]:
        df[dcol] = df[dcol].apply(limpiar_fecha)
        
    # Montos
    for mcol in ["importe_total_erogado", "importe_ejercido_partida", "gastos_no_erogados", "importe_acompanantes"]:
        df[mcol] = df[mcol].apply(limpiar_monto)
        
    df["numero_acompanantes"] = pd.to_numeric(df["numero_acompanantes"], errors="coerce").fillna(0).astype(int)
    
    # Deduplicar
    antes = len(df)
    df = df.drop_duplicates()
    print(f"Deduplicación: de {antes:,} a {len(df):,} filas ({antes - len(df):,} duplicados descartados).")
    
    cols_orden = [
        "ejercicio", "fecha_salida", "fecha_regreso", "comisionado_nombre", "cargo",
        "denominacion_puesto", "area_adscripcion", "estado_destino", "ciudad_destino",
        "pais_destino", "motivo_comision", "importe_total_erogado", "tipo_viaje",
        "tipo_gasto", "nombres", "primer_apellido", "segundo_apellido", "sexo",
        "clave_puesto", "tipo_integrante", "estado_origen", "ciudad_origen",
        "importe_ejercido_partida", "gastos_no_erogados", "numero_acompanantes",
        "importe_acompanantes", "hipervinculo_informe", "hipervinculo_facturas",
        "area_responsable", "fecha_entrega_informe", "fecha_validacion", "nota"
    ]
    df = df[cols_orden].sort_values(by=["ejercicio", "fecha_salida", "importe_total_erogado"], ascending=[True, True, False]).reset_index(drop=True)
    
    salida_dir = "datos_b2/02_datos_limpios/viaticos"
    os.makedirs(salida_dir, exist_ok=True)
    
    ruta_parquet = os.path.join(salida_dir, "gastos_viaticos_comisiones_2022_2025.parquet")
    df.to_parquet(ruta_parquet, index=False, engine="pyarrow", compression="snappy")
    print(f"-> Guardado: {ruta_parquet} ({os.path.getsize(ruta_parquet) / (1024*1024):.2f} MB)")
    
    # CSV con comisiones relevantes para visualización directa en Excel
    ruta_csv_top = os.path.join(salida_dir, "top_gastos_viaticos_mayores.csv")
    df_top = df[df["importe_total_erogado"] >= 10_000].sort_values(by="importe_total_erogado", ascending=False)
    df_top.to_csv(ruta_csv_top, index=False, encoding="utf-8")
    print(f"-> Guardado CSV con viáticos >= $10k MXN: {ruta_csv_top} ({len(df_top):,} comisiones)")
    
    print("\n" + "=" * 70)
    print("RESUMEN DE VIÁTICOS Y COMISIONES POR EJERCICIO")
    print("=" * 70)
    resumen = df.groupby("ejercicio").agg(
        comisiones=("importe_total_erogado", "count"),
        gasto_total=("importe_total_erogado", "sum")
    )
    resumen["gasto_total_formato"] = resumen["gasto_total"].apply(lambda x: f"${x:,.2f}")
    print(resumen[["comisiones", "gasto_total_formato"]])

if __name__ == "__main__":
    procesar_viaticos()
