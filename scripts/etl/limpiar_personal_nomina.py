#!/usr/bin/env python3
"""
Pipeline de Limpieza y Estandarización: Personal, Nómina y Honorarios del INE (2020-2026)
Fuentes:
  - 01_datos_crudos/FED_INE_2025/datos/crudos/PA-04_sueldos/*43315*.json (Remuneraciones)
  - 01_datos_crudos/lista_personal_honorarios_ine_completa.csv (Honorarios)
  - 02_datos_procesados/rfcs_por_ejercicio/*.csv (Padrón histórico)
Destino: 02_datos_limpios/personal_y_nomina/
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
    # Si viene en formato DD/MM/YYYY
    match_dmy = re.match(r"^(\d{2})/(\d{2})/(\d{4})", val_str)
    if match_dmy:
        d, m, y = match_dmy.groups()
        return f"{y}-{m}-{d}"
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

def determinar_trimestre(fecha_inicio):
    f = str(fecha_inicio).strip()
    if "01/01" in f or "-01-01" in f:
        return "Q1"
    if "01/04" in f or "-04-01" in f:
        return "Q2"
    if "01/07" in f or "-07-01" in f:
        return "Q3"
    if "01/10" in f or "-10-01" in f:
        return "Q4"
    return "OTRO"

def procesar_remuneraciones_2025(salida_dir: str):
    print("\n--- 1. Procesando Formato 43315: Remuneraciones y Sueldos 2025 (Q1-Q4) ---")
    patron = "datos_b2/01_datos_crudos/FED_INE_2025/datos/crudos/PA-04_sueldos/*43315*.json"
    archivos = sorted(glob.glob(patron))
    
    all_filas = []
    for f in archivos:
        print(f"-> Leyendo: {f}")
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
            all_filas.extend(d.get("filas", []))
            
    print(f"Total registros brutos cargados: {len(all_filas):,}")
    
    cols = [
        "ejercicio", "fecha_inicio_periodo", "fecha_fin_periodo", "tipo_integrante",
        "clave_puesto", "denominacion_puesto", "cargo", "area_adscripcion",
        "nombres", "primer_apellido", "segundo_apellido", "sexo",
        "sueldo_mensual_bruto", "tipo_moneda_bruto", "sueldo_mensual_neto", "tipo_moneda_neto",
        "percepciones_adicionales_efectivo", "percepciones_adicionales_especie",
        "ingresos_adicionales", "sistemas_compensacion", "gratificaciones",
        "primas", "comisiones", "dietas", "bonos", "estimulos", "apoyos_economicos",
        "prestaciones_economicas", "prestaciones_especie", "area_responsable",
        "fecha_validacion", "fecha_actualizacion", "nota"
    ]
    
    df = pd.DataFrame(all_filas, columns=cols)
    
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
        
    df["ejercicio"] = pd.to_numeric(df["ejercicio"], errors="coerce").fillna(2025).astype(int)
    df["periodo_trimestre"] = df["fecha_inicio_periodo"].apply(determinar_trimestre)
    
    # Nombre completo
    partes = zip(df["nombres"], df["primer_apellido"], df["segundo_apellido"])
    df["nombre_completo"] = [" ".join([p for p in pt if p and p != "None"]).strip() for pt in partes]
    
    # Fechas
    for dcol in ["fecha_inicio_periodo", "fecha_fin_periodo", "fecha_validacion", "fecha_actualizacion"]:
        df[dcol] = df[dcol].apply(limpiar_fecha)
        
    # Montos
    df["sueldo_mensual_bruto"] = df["sueldo_mensual_bruto"].apply(limpiar_monto)
    df["sueldo_mensual_neto"] = df["sueldo_mensual_neto"].apply(limpiar_monto)
    
    # Deduplicar
    antes = len(df)
    df = df.drop_duplicates()
    print(f"Deduplicación: de {antes:,} a {len(df):,} filas ({antes - len(df):,} duplicados descartados).")
    
    cols_ordenadas = [
        "ejercicio", "periodo_trimestre", "nombre_completo", "cargo", "denominacion_puesto",
        "clave_puesto", "tipo_integrante", "area_adscripcion", "sexo",
        "sueldo_mensual_bruto", "sueldo_mensual_neto",
        "nombres", "primer_apellido", "segundo_apellido",
        "fecha_inicio_periodo", "fecha_fin_periodo", "area_responsable",
        "fecha_validacion", "fecha_actualizacion", "nota"
    ]
    df = df[cols_ordenadas].sort_values(by=["ejercicio", "periodo_trimestre", "sueldo_mensual_bruto"], ascending=[True, True, False]).reset_index(drop=True)
    
    ruta_parquet = os.path.join(salida_dir, "remuneraciones_personal_2025.parquet")
    df.to_parquet(ruta_parquet, index=False, engine="pyarrow", compression="snappy")
    print(f"-> Guardado: {ruta_parquet} ({os.path.getsize(ruta_parquet) / (1024*1024):.2f} MB)")
    
    # Resumen por cargo para Excel
    ruta_csv_cargos = os.path.join(salida_dir, "resumen_sueldos_por_cargo_2025.csv")
    resumen_cargos = df.groupby(["cargo", "periodo_trimestre"]).agg(
        empleados=("sueldo_mensual_bruto", "count"),
        sueldo_bruto_promedio=("sueldo_mensual_bruto", "mean"),
        sueldo_neto_promedio=("sueldo_mensual_neto", "mean"),
        sueldo_maximo=("sueldo_mensual_bruto", "max")
    ).round(2).reset_index()
    resumen_cargos.to_csv(ruta_csv_cargos, index=False, encoding="utf-8")
    print(f"-> Guardado resumen de sueldos por cargo en CSV: {ruta_csv_cargos}")
    
    return df

def procesar_honorarios_2025(salida_dir: str):
    print("\n--- 2. Procesando Padrón de Contrataciones por Honorarios 2025 ---")
    ruta_csv_origen = "datos_b2/01_datos_crudos/lista_personal_honorarios_ine_completa.csv"
    df = pd.read_csv(ruta_csv_origen)
    print(f"Total contratos por honorarios cargados: {len(df):,}")
    
    for c in df.select_dtypes(include="object").columns:
        df[c] = df[c].astype(str).str.strip()
        
    df["ejercicio"] = pd.to_numeric(df["ejercicio"], errors="coerce").fillna(2025).astype(int)
    
    # Fechas
    df["fecha_inicio"] = df["fecha_inicio"].apply(limpiar_fecha)
    df["fecha_fin"] = df["fecha_fin"].apply(limpiar_fecha)
    
    # Montos
    for m in ["remuneracion_mensual_bruta", "remuneracion_mensual_neta", "monto_total_bruto", "monto_total_neto"]:
        df[m] = pd.to_numeric(df[m], errors="coerce")
        
    df = df.drop_duplicates().sort_values(by=["ejercicio", "fecha_inicio", "nombre_completo"]).reset_index(drop=True)
    
    ruta_parquet = os.path.join(salida_dir, "contrataciones_honorarios_2025.parquet")
    df.to_parquet(ruta_parquet, index=False, engine="pyarrow", compression="snappy")
    print(f"-> Guardado: {ruta_parquet} ({os.path.getsize(ruta_parquet) / (1024*1024):.2f} MB)")
    
    return df

def procesar_padron_historico_empleados(salida_dir: str):
    print("\n--- 3. Procesando Padrón Histórico Consolidado de Empleados (2020-2026) ---")
    archivos = sorted(glob.glob("02_datos_procesados/rfcs_por_ejercicio/lista_empleados_rfcs_*.csv"))
    
    dfs = []
    for f in archivos:
        print(f"-> Leyendo: {f}")
        df_sub = pd.read_csv(f)
        if len(df_sub) > 0:
            dfs.append(df_sub)
            
    df_all = pd.concat(dfs, ignore_index=True)
    print(f"Total registros históricos combinados: {len(df_all):,}")
    
    for c in df_all.select_dtypes(include="object").columns:
        df_all[c] = df_all[c].astype(str).str.strip()
        
    df_all["ejercicio"] = pd.to_numeric(df_all["ejercicio"], errors="coerce").fillna(0).astype(int)
    df_all["remuneracion_o_monto"] = pd.to_numeric(df_all["remuneracion_o_monto"], errors="coerce")
    
    df_all = df_all.drop_duplicates().sort_values(by=["ejercicio", "nombre_completo"]).reset_index(drop=True)
    
    ruta_parquet = os.path.join(salida_dir, "padron_historico_empleados_2020_2026.parquet")
    df_all.to_parquet(ruta_parquet, index=False, engine="pyarrow", compression="snappy")
    print(f"-> Guardado: {ruta_parquet} ({os.path.getsize(ruta_parquet) / (1024*1024):.2f} MB)")
    
    print("\n" + "=" * 70)
    print("RESUMEN DE PERSONAL DEL INE POR EJERCICIO")
    print("=" * 70)
    resumen = df_all.groupby(["ejercicio", "tipo_personal"]).agg(
        total_empleados=("nombre_completo", "count")
    )
    print(resumen)

if __name__ == "__main__":
    salida = "datos_b2/02_datos_limpios/personal_y_nomina"
    os.makedirs(salida, exist_ok=True)
    
    procesar_remuneraciones_2025(salida)
    procesar_honorarios_2025(salida)
    procesar_padron_historico_empleados(salida)
