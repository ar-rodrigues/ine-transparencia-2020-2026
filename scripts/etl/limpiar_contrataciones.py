#!/usr/bin/env python3
"""
Pipeline de Limpieza y Estandarización: Contrataciones Públicas del INE (2021-2025)
Fuente: 01_datos_crudos/**/PA-01_contratos_padron/
Destino: 02_datos_limpios/contrataciones/
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
    return val_str

def limpiar_monto(val):
    if val is None or pd.isna(val):
        return np.nan
    val_str = str(val).strip().replace("$", "").replace(",", "")
    if val_str == "" or val_str in ["-", "N/A", "ND", "None", "0.0"]:
        return 0.0
    try:
        return float(val_str)
    except ValueError:
        return np.nan

def armar_nombre_proveedor(razon_social, nombre, ap1, ap2):
    rs = str(razon_social).strip() if razon_social and not pd.isna(razon_social) else ""
    if rs:
        return rs
    partes = [str(p).strip() for p in [nombre, ap1, ap2] if p and not pd.isna(p) and str(p).strip()]
    return " ".join(partes) if partes else "NO_ESPECIFICADO"

def procesar_adjudicaciones_directas(salida_dir: str):
    print("\n--- Procesando Formato 43335: Adjudicaciones Directas (2021-2023) ---")
    patron = "datos_b2/01_datos_crudos/**/PA-01_contratos_padron/*43335*.json"
    archivos = sorted(glob.glob(patron, recursive=True))
    
    registros = []
    for f in archivos:
        print(f"-> Leyendo: {f}")
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
            registros.extend(d.get("filas", []))
            
    print(f"Total registros brutos cargados: {len(registros):,}")
    
    cols_43335 = [
        "ejercicio", "fecha_inicio_periodo", "fecha_fin_periodo", "tipo_procedimiento",
        "materia", "caracter_procedimiento", "numero_expediente", "motivos_adjudicacion_directa",
        "hipervinculo_suficiencia_recursos", "descripcion_obras_bienes_servicios",
        "cotizaciones_consideradas", "nombre_adjudicado", "primer_apellido_adjudicado",
        "segundo_apellido_adjudicado", "razon_social_adjudicado", "sexo",
        "rfc_proveedor", "tipo_vialidad", "nombre_vialidad", "numero_exterior",
        "numero_interior", "tipo_asentamiento", "nombre_asentamiento", "clave_localidad",
        "nombre_localidad", "clave_municipio", "nombre_municipio", "clave_entidad_federativa",
        "nombre_entidad_federativa", "codigo_postal", "pais_extranjero", "ciudad_extranjero",
        "calle_extranjero", "numero_extranjero", "area_solicitante", "area_responsable_ejecucion",
        "numero_contrato", "fecha_contrato", "fecha_inicio_vigencia", "fecha_fin_vigencia",
        "monto_sin_impuestos", "monto_total_con_impuestos", "monto_minimo", "monto_maximo",
        "tipo_moneda", "tipo_cambio", "forma_pago", "objeto_contrato", "monto_garantias",
        "fecha_inicio_entrega", "fecha_fin_entrega", "hipervinculo_contrato",
        "hipervinculo_suspension_rescision", "origen_recursos", "fuentes_financiamiento",
        "datos_obra_publica", "convenios_modificatorios", "datos_convenios_modificatorios",
        "mecanismos_vigilancia", "hipervinculo_avance_fisico", "hipervinculo_avance_financiero",
        "hipervinculo_acta_recepcion", "hipervinculo_finiquito", "area_responsable_informacion",
        "fecha_validacion", "fecha_actualizacion", "nota"
    ]
    
    df = pd.DataFrame(registros, columns=cols_43335)
    
    # Limpieza de espacios
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
        
    df["ejercicio"] = pd.to_numeric(df["ejercicio"], errors="coerce").fillna(0).astype(int)
    
    # Nombre y tipo de proveedor
    df["proveedor_nombre"] = [
        armar_nombre_proveedor(rs, nom, ap1, ap2)
        for rs, nom, ap1, ap2 in zip(
            df["razon_social_adjudicado"],
            df["nombre_adjudicado"],
            df["primer_apellido_adjudicado"],
            df["segundo_apellido_adjudicado"]
        )
    ]
    df["tipo_persona"] = np.where(df["razon_social_adjudicado"].str.strip() != "", "MORAL", "FISICA")
    df["rfc_proveedor"] = df["rfc_proveedor"].str.upper().str.strip()
    
    # Montos
    for mcol in ["monto_sin_impuestos", "monto_total_con_impuestos", "monto_minimo", "monto_maximo", "monto_garantias", "tipo_cambio"]:
        df[mcol] = df[mcol].apply(limpiar_monto)
        
    # Fechas
    for dcol in ["fecha_contrato", "fecha_inicio_vigencia", "fecha_fin_vigencia", "fecha_inicio_periodo", "fecha_fin_periodo", "fecha_inicio_entrega", "fecha_fin_entrega", "fecha_validacion", "fecha_actualizacion"]:
        df[dcol] = df[dcol].apply(limpiar_fecha)
        
    # Deduplicar
    antes = len(df)
    df = df.drop_duplicates()
    print(f"Deduplicación: de {antes:,} a {len(df):,} filas ({antes - len(df):,} duplicados descartados).")
    
    df = df.sort_values(by=["ejercicio", "fecha_contrato", "proveedor_nombre"]).reset_index(drop=True)
    
    # Reordenar con proveedor al frente para facilitar lectura
    cols_orden = [
        "ejercicio", "fecha_contrato", "proveedor_nombre", "tipo_persona", "rfc_proveedor",
        "monto_total_con_impuestos", "monto_sin_impuestos", "materia", "tipo_procedimiento",
        "numero_contrato", "objeto_contrato", "area_solicitante", "area_responsable_ejecucion",
        "fecha_inicio_vigencia", "fecha_fin_vigencia", "tipo_moneda", "forma_pago",
        "nombre_entidad_federativa", "nombre_municipio", "hipervinculo_contrato"
    ]
    resto_cols = [c for c in df.columns if c not in cols_orden]
    df = df[cols_orden + resto_cols]
    
    ruta_parquet = os.path.join(salida_dir, "adjudicaciones_directas_2021_2023.parquet")
    df.to_parquet(ruta_parquet, index=False, engine="pyarrow", compression="snappy")
    print(f"-> Guardado: {ruta_parquet} ({os.path.getsize(ruta_parquet) / (1024*1024):.2f} MB)")
    
    return df

def procesar_licitaciones_publicas(salida_dir: str):
    print("\n--- Procesando Formato 43336: Licitaciones Públicas (2022-2023) ---")
    patron = "datos_b2/01_datos_crudos/**/PA-01_contratos_padron/*43336*.json"
    archivos = sorted(glob.glob(patron, recursive=True))
    
    registros = []
    for f in archivos:
        print(f"-> Leyendo: {f}")
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
            registros.extend(d.get("filas", []))
            
    print(f"Total licitaciones cargadas: {len(registros):,}")
    
    # Usar nombres equivalentes
    df = pd.DataFrame(registros)
    # Seleccionar y mapear columnas clave
    cols_rename = {
        0: "ejercicio",
        1: "fecha_inicio_periodo",
        2: "fecha_fin_periodo",
        3: "tipo_procedimiento",
        4: "materia",
        5: "caracter_procedimiento",
        7: "numero_expediente",
        10: "descripcion_obras_bienes_servicios",
        18: "nombre_contratista",
        19: "primer_apellido_contratista",
        20: "segundo_apellido_contratista",
        21: "razon_social_contratista",
        22: "sexo",
        23: "rfc_proveedor",
        42: "area_solicitante",
        43: "area_contratante",
        44: "area_responsable_ejecucion",
        45: "numero_contrato",
        46: "fecha_contrato",
        47: "fecha_inicio_vigencia",
        48: "fecha_fin_vigencia",
        49: "monto_sin_impuestos",
        50: "monto_total_con_impuestos",
        51: "monto_minimo",
        52: "monto_maximo",
        53: "tipo_moneda",
        55: "forma_pago",
        56: "objeto_contrato",
        59: "hipervinculo_contrato",
        61: "partida_presupuestal",
        81: "nota"
    }
    
    df = df[list(cols_rename.keys())].rename(columns=cols_rename)
    
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
        
    df["ejercicio"] = pd.to_numeric(df["ejercicio"], errors="coerce").fillna(0).astype(int)
    df["proveedor_nombre"] = [
        armar_nombre_proveedor(rs, nom, ap1, ap2)
        for rs, nom, ap1, ap2 in zip(
            df["razon_social_contratista"],
            df["nombre_contratista"],
            df["primer_apellido_contratista"],
            df["segundo_apellido_contratista"]
        )
    ]
    df["tipo_persona"] = np.where(df["razon_social_contratista"].str.strip() != "", "MORAL", "FISICA")
    df["rfc_proveedor"] = df["rfc_proveedor"].str.upper().str.strip()
    
    for mcol in ["monto_sin_impuestos", "monto_total_con_impuestos", "monto_minimo", "monto_maximo"]:
        df[mcol] = df[mcol].apply(limpiar_monto)
        
    for dcol in ["fecha_contrato", "fecha_inicio_vigencia", "fecha_fin_vigencia", "fecha_inicio_periodo", "fecha_fin_periodo"]:
        df[dcol] = df[dcol].apply(limpiar_fecha)
        
    df = df.drop_duplicates()
    df = df.sort_values(by=["ejercicio", "fecha_contrato", "proveedor_nombre"]).reset_index(drop=True)
    
    cols_orden = [
        "ejercicio", "fecha_contrato", "proveedor_nombre", "tipo_persona", "rfc_proveedor",
        "monto_total_con_impuestos", "monto_sin_impuestos", "materia", "tipo_procedimiento",
        "numero_contrato", "objeto_contrato", "area_solicitante", "area_responsable_ejecucion",
        "fecha_inicio_vigencia", "fecha_fin_vigencia", "tipo_moneda", "forma_pago",
        "hipervinculo_contrato", "partida_presupuestal", "nota"
    ]
    df = df[cols_orden]
    
    ruta_parquet = os.path.join(salida_dir, "licitaciones_publicas_2022_2023.parquet")
    df.to_parquet(ruta_parquet, index=False, engine="pyarrow", compression="snappy")
    print(f"-> Guardado: {ruta_parquet} ({os.path.getsize(ruta_parquet) / 1024:.2f} KB)")
    
    return df

def procesar_padron_proveedores(salida_dir: str):
    print("\n--- Procesando Formato 43369: Padrón de Proveedores (2022, 2025) ---")
    patron = "datos_b2/01_datos_crudos/**/PA-01_contratos_padron/*43369*.json"
    archivos = sorted(glob.glob(patron, recursive=True))
    
    registros = []
    for f in archivos:
        print(f"-> Leyendo: {f}")
        with open(f, "r", encoding="utf-8") as fp:
            d = json.load(fp)
            registros.extend(d.get("filas", []))
            
    df = pd.DataFrame(registros)
    cols_rename = {
        0: "ejercicio",
        1: "fecha_inicio_periodo",
        2: "fecha_fin_periodo",
        3: "personalidad_juridica",
        4: "nombre_proveedor",
        5: "primer_apellido",
        6: "segundo_apellido",
        7: "sexo",
        8: "razon_social",
        13: "rfc_proveedor",
        14: "tipo_proveedor_catalogo",
        27: "entidad_federativa",
        28: "municipio",
        45: "fecha_registro_padron",
        48: "area_responsable",
        49: "nota"
    }
    cols_to_use = [k for k in cols_rename.keys() if k < df.shape[1]]
    df = df[cols_to_use].rename(columns={k: cols_rename[k] for k in cols_to_use})
    
    for c in df.columns:
        df[c] = df[c].astype(str).str.strip()
        
    df["ejercicio"] = pd.to_numeric(df["ejercicio"], errors="coerce").fillna(0).astype(int)
    df["proveedor_nombre"] = [
        armar_nombre_proveedor(rs, nom, ap1, ap2)
        for rs, nom, ap1, ap2 in zip(
            df["razon_social"],
            df["nombre_proveedor"],
            df["primer_apellido"],
            df["segundo_apellido"]
        )
    ]
    df["rfc_proveedor"] = df["rfc_proveedor"].str.upper().str.strip()
    df = df.drop_duplicates()
    
    ruta_parquet = os.path.join(salida_dir, "padron_proveedores_2022_2025.parquet")
    df.to_parquet(ruta_parquet, index=False, engine="pyarrow", compression="snappy")
    print(f"-> Guardado: {ruta_parquet} ({os.path.getsize(ruta_parquet) / 1024:.2f} KB)")
    return df

def crear_resumen_unificado_contrataciones(df_adj, df_lic, salida_dir: str):
    print("\n--- Generando Tabla Consolidada de Todas las Contrataciones ---")
    cols_comunes = [
        "ejercicio", "fecha_contrato", "proveedor_nombre", "tipo_persona", "rfc_proveedor",
        "monto_total_con_impuestos", "monto_sin_impuestos", "materia", "tipo_procedimiento",
        "numero_contrato", "objeto_contrato", "area_solicitante", "area_responsable_ejecucion",
        "fecha_inicio_vigencia", "fecha_fin_vigencia", "tipo_moneda", "forma_pago",
        "hipervinculo_contrato"
    ]
    sub_adj = df_adj[cols_comunes].copy()
    sub_lic = df_lic[cols_comunes].copy()
    
    df_total = pd.concat([sub_adj, sub_lic], ignore_index=True)
    df_total = df_total.sort_values(by=["ejercicio", "fecha_contrato", "proveedor_nombre"]).reset_index(drop=True)
    
    ruta_parquet = os.path.join(salida_dir, "contrataciones_ine_consolidadas_2021_2023.parquet")
    df_total.to_parquet(ruta_parquet, index=False, engine="pyarrow", compression="snappy")
    print(f"-> Guardado consolidado: {ruta_parquet} ({os.path.getsize(ruta_parquet) / (1024*1024):.2f} MB)")
    
    # También un CSV resumen con los top contratos (o los más representativos) para abrir en Excel
    ruta_csv_top = os.path.join(salida_dir, "top_contratos_mayores_ine.csv")
    df_top = df_total[df_total["monto_total_con_impuestos"] >= 1_000_000].sort_values(by="monto_total_con_impuestos", ascending=False)
    df_top.to_csv(ruta_csv_top, index=False, encoding="utf-8")
    print(f"-> Guardado CSV con contratos >= $1M MXN para consulta directa: {ruta_csv_top} ({len(df_top):,} contratos)")

    # Reporte estadístico ejecutivo
    print("\n" + "=" * 70)
    print("RESUMEN EJECUTIVO DE CONTRATACIONES DEL INE (2021-2023)")
    print("=" * 70)
    resumen = df_total.groupby(["ejercicio", "tipo_procedimiento"]).agg(
        contratos=("monto_total_con_impuestos", "count"),
        monto_total=("monto_total_con_impuestos", "sum")
    )
    resumen["monto_total_formato"] = resumen["monto_total"].apply(lambda x: f"${x:,.2f}")
    print(resumen[["contratos", "monto_total_formato"]])

if __name__ == "__main__":
    salida = "datos_b2/02_datos_limpios/contrataciones"
    os.makedirs(salida, exist_ok=True)
    
    df_adj = procesar_adjudicaciones_directas(salida)
    df_lic = procesar_licitaciones_publicas(salida)
    procesar_padron_proveedores(salida)
    crear_resumen_unificado_contrataciones(df_adj, df_lic, salida)
