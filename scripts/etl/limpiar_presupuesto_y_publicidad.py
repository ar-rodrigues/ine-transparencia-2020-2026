#!/usr/bin/env python3
"""
Pipeline de Limpieza y Estandarización:
1. Presupuesto por Capítulos y Partidas (2020 y 2025) - Formato 43338
2. Publicidad Oficial y Comunicación (2025) - Formato 43320
3. Acuerdos Normativos del Consejo General del INE (2022-2026) - Formato 43495
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

def procesar_presupuesto_partidas():
    print("\n--- 1. Procesando Presupuesto por Capítulos y Partidas (Formato 43338) ---")
    patron = "datos_b2/01_datos_crudos/**/PA-08_presupuesto_partidas/*43338*.json"
    archivos = sorted(glob.glob(patron, recursive=True))
    
    registros = []
    for f in archivos:
        print(f"-> Leyendo: {f}")
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
            filas = d.get("filas", [])
            for r in filas:
                ejercicio = int(r[0]) if r[0] and str(r[0]).isdigit() else 0
                inicio = limpiar_fecha(r[1])
                fin = limpiar_fecha(r[2])
                
                # Unificar columnas económicas vs objeto del gasto
                clave_capitulo = str(r[3]).strip() if str(r[3]).strip() else str(r[4]).strip()
                clave_concepto = str(r[5]).strip() if str(r[5]).strip() else str(r[6]).strip()
                clave_partida = str(r[7]).strip() if str(r[7]).strip() else str(r[8]).strip()
                denominacion_partida = str(r[9]).strip() if str(r[9]).strip() else str(r[10]).strip()
                
                # Montos (tomar el no nulo entre cols 11/12, 13/14, etc.)
                m_aprobado = limpiar_monto(r[11]) if limpiar_monto(r[11]) > 0 else limpiar_monto(r[12])
                m_modificado = limpiar_monto(r[13]) if limpiar_monto(r[13]) > 0 else limpiar_monto(r[14])
                m_comprometido = limpiar_monto(r[15]) if limpiar_monto(r[15]) > 0 else limpiar_monto(r[16])
                m_devengado = limpiar_monto(r[17]) if limpiar_monto(r[17]) > 0 else limpiar_monto(r[18])
                m_ejercido = limpiar_monto(r[19]) if limpiar_monto(r[19]) > 0 else limpiar_monto(r[20])
                m_pagado = limpiar_monto(r[21]) if limpiar_monto(r[21]) > 0 else limpiar_monto(r[22])
                
                justificacion = str(r[23]).strip() if len(r) > 23 else ""
                area = str(r[25]).strip() if len(r) > 25 else ""
                
                registros.append({
                    "ejercicio": ejercicio,
                    "fecha_inicio_periodo": inicio,
                    "fecha_fin_periodo": fin,
                    "clave_capitulo": clave_capitulo,
                    "clave_concepto": clave_concepto,
                    "clave_partida": clave_partida,
                    "denominacion_partida": denominacion_partida,
                    "gasto_aprobado": m_aprobado,
                    "gasto_modificado": m_modificado,
                    "gasto_comprometido": m_comprometido,
                    "gasto_devengado": m_devengado,
                    "gasto_ejercido": m_ejercido,
                    "gasto_pagado": m_pagado,
                    "justificacion_modificacion": justificacion,
                    "area_responsable": area
                })
                
    df = pd.DataFrame(registros)
    df = df.drop_duplicates().sort_values(by=["ejercicio", "clave_capitulo", "clave_partida"]).reset_index(drop=True)
    
    salida_dir = "datos_b2/02_datos_limpios/presupuesto"
    os.makedirs(salida_dir, exist_ok=True)
    
    ruta_parquet = os.path.join(salida_dir, "presupuesto_partidas_2020_2025.parquet")
    ruta_csv = os.path.join(salida_dir, "presupuesto_partidas_2020_2025.csv")
    
    df.to_parquet(ruta_parquet, index=False, engine="pyarrow", compression="snappy")
    df.to_csv(ruta_csv, index=False, encoding="utf-8")
    print(f"-> Guardado: {ruta_parquet} ({len(df):,} filas)")
    print(f"-> Guardado CSV: {ruta_csv}")
    
    print("\nResumen de Presupuesto Pagado por Capítulo:")
    resumen = df.groupby(["ejercicio", "clave_capitulo"]).agg(
        partidas=("clave_partida", "count"),
        total_aprobado=("gasto_aprobado", "sum"),
        total_pagado=("gasto_pagado", "sum")
    )
    resumen["total_aprobado_formato"] = resumen["total_aprobado"].apply(lambda x: f"${x:,.2f}")
    resumen["total_pagado_formato"] = resumen["total_pagado"].apply(lambda x: f"${x:,.2f}")
    print(resumen[["partidas", "total_aprobado_formato", "total_pagado_formato"]])
    return df

def procesar_publicidad_oficial():
    print("\n--- 2. Procesando Publicidad Oficial (Formato 43320) ---")
    patron = "datos_b2/01_datos_crudos/**/PA-06_publicidad/*43320*.json"
    archivos = sorted(glob.glob(patron, recursive=True))
    
    registros = []
    for f in archivos:
        print(f"-> Leyendo: {f}")
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
            registros.extend(d.get("filas", []))
            
    cols = [
        "ejercicio", "fecha_inicio_periodo", "fecha_fin_periodo", "funcion_sujeto_obligado",
        "area_solicitante", "clasificacion_servicio", "tipo_servicio", "tipo_medio",
        "descripcion_unidad", "tipo_aviso", "nombre_campana", "anio_campana",
        "tema_campana", "objetivo_institucional", "objetivo_comunicacion",
        "costo_por_unidad", "clave_campana", "autoridad_clave", "cobertura",
        "ambito_geografico", "fecha_inicio_campana", "fecha_fin_campana",
        "sexo_publico_objetivo", "lugar_residencia", "nivel_educativo", "grupo_edad",
        "nivel_socioeconomico", "proveedor_contratacion", "recursos_presupuesto",
        "contrato_montos", "area_responsable", "fecha_validacion", "fecha_actualizacion", "nota"
    ]
    df = pd.DataFrame(registros, columns=cols)
    
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
        
    df["ejercicio"] = pd.to_numeric(df["ejercicio"], errors="coerce").fillna(2025).astype(int)
    df["costo_por_unidad"] = df["costo_por_unidad"].apply(limpiar_monto)
    
    for dcol in ["fecha_inicio_campana", "fecha_fin_campana", "fecha_inicio_periodo", "fecha_fin_periodo", "fecha_actualizacion"]:
        df[dcol] = df[dcol].apply(limpiar_fecha)
        
    df = df.drop_duplicates().sort_values(by=["ejercicio", "fecha_inicio_campana", "costo_por_unidad"], ascending=[True, True, False]).reset_index(drop=True)
    
    salida_dir = "datos_b2/02_datos_limpios/publicidad_oficial"
    os.makedirs(salida_dir, exist_ok=True)
    
    ruta_parquet = os.path.join(salida_dir, "publicidad_oficial_2025.parquet")
    ruta_csv = os.path.join(salida_dir, "publicidad_oficial_2025.csv")
    
    df.to_parquet(ruta_parquet, index=False, engine="pyarrow", compression="snappy")
    df.to_csv(ruta_csv, index=False, encoding="utf-8")
    print(f"-> Guardado: {ruta_parquet} ({len(df):,} filas)")
    print(f"-> Guardado CSV: {ruta_csv}")
    
    print("\nResumen de Publicidad Oficial por Tipo de Medio:")
    resumen = df.groupby("tipo_medio").agg(
        campanas=("nombre_campana", "count"),
        gasto_total=("costo_por_unidad", "sum")
    ).sort_values(by="gasto_total", ascending=False)
    resumen["gasto_total_formato"] = resumen["gasto_total"].apply(lambda x: f"${x:,.2f}")
    print(resumen[["campanas", "gasto_total_formato"]])
    return df

def procesar_acuerdos_consejo():
    print("\n--- 3. Procesando Acuerdos Normativos del Consejo General (Formato 43495) ---")
    patron = "datos_b2/01_datos_crudos/**/43495*/*.json"
    archivos = sorted(glob.glob(patron, recursive=True))
    
    registros = []
    for f in archivos:
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
            for r in d.get("filas", []):
                registros.append({
                    "ejercicio": int(r[0]) if r[0] and str(r[0]).isdigit() else 0,
                    "fecha_inicio_periodo": limpiar_fecha(r[1]),
                    "fecha_fin_periodo": limpiar_fecha(r[2]),
                    "proceso_electoral": str(r[3]).strip(),
                    "fecha_publicacion_dof": limpiar_fecha(r[4]),
                    "denominacion_acuerdo": str(r[5]).strip(),
                    "hipervinculo_acuerdo": str(r[6]).strip(),
                    "area_responsable": str(r[7]).strip() if len(r) > 7 else ""
                })
                
    df = pd.DataFrame(registros).drop_duplicates().sort_values(by=["ejercicio", "fecha_publicacion_dof"]).reset_index(drop=True)
    
    salida_dir = "datos_b2/02_datos_limpios/acuerdos_consejo_general"
    os.makedirs(salida_dir, exist_ok=True)
    
    ruta_parquet = os.path.join(salida_dir, "acuerdos_consejo_general_2022_2026.parquet")
    ruta_csv = os.path.join(salida_dir, "acuerdos_consejo_general_2022_2026.csv")
    
    df.to_parquet(ruta_parquet, index=False, engine="pyarrow", compression="snappy")
    df.to_csv(ruta_csv, index=False, encoding="utf-8")
    print(f"-> Guardado: {ruta_parquet} ({len(df):,} acuerdos normativos)")
    print(f"-> Guardado CSV: {ruta_csv}")
    return df

if __name__ == "__main__":
    procesar_presupuesto_partidas()
    procesar_publicidad_oficial()
    procesar_acuerdos_consejo()
