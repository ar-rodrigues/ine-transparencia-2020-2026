#!/usr/bin/env python3
"""
Pipeline ETL: Capa de Agregación Analítica (Capa Oro / 03_datos_agregados)
Proyecto: Repositorio de Auditoría y Análisis de Personal — INE (2020–2026)

Este script consolida y precalcula los indicadores clave (KPIs), rankings,
series de tiempo y comparativas analíticas a partir de la capa limpia (02_datos_limpios).

Estructura de salida generada:
03_datos_agregados/
├── financiamiento_partidos/
│   ├── kpi_financiamiento_anual_partidos.parquet
│   ├── serie_mensual_tipo_financiamiento.parquet
│   └── comparativa_electoral_vs_ordinario.parquet
├── contrataciones/
│   ├── kpi_procedimientos_contratacion.parquet
│   ├── ranking_top_proveedores.parquet
│   └── serie_anual_materia_contratacion.parquet
├── presupuesto/
│   ├── ejecucion_presupuestal_capitulos.parquet
│   └── top_partidas_gasto.parquet
├── personal_y_nomina/
│   ├── evolucion_plantilla_headcount.parquet
│   ├── distribucion_salarial_por_puesto_2025.parquet
│   └── comparativa_nomina_vs_honorarios_2025.parquet
├── viaticos/
│   ├── kpi_viaticos_nacional_internacional.parquet
│   └── ranking_areas_gasto_viaticos.parquet
├── publicidad_oficial/
│   └── gasto_publicidad_por_medio_2025.parquet
└── resumen_ejecutivo/
    └── resumen_ejecutivo_ine_anual.parquet
"""

import os
import sys
import duckdb
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
DATOS_B2_DIR = BASE_DIR / "datos_b2"
LIMPIOS_DIR = DATOS_B2_DIR / "02_datos_limpios"
AGREGADOS_DIR = DATOS_B2_DIR / "03_datos_agregados"

def log(msg: str):
    print(f"[ETL-ORO] {msg}")

def ejecutar_agregaciones():
    log(f"Iniciando generación de Capa Oro en: {AGREGADOS_DIR}")
    AGREGADOS_DIR.mkdir(parents=True, exist_ok=True)
    
    conn = duckdb.connect()

    # =========================================================================
    # 1. FINANCIAMIENTO A PARTIDOS POLÍTICOS (2020–2026)
    # =========================================================================
    fin_dir = AGREGADOS_DIR / "financiamiento_partidos"
    fin_dir.mkdir(parents=True, exist_ok=True)
    src_fin = LIMPIOS_DIR / "financiamiento_partidos/financiamiento_partidos_2020_2026.parquet"

    if src_fin.exists():
        log("Procesando Financiamiento a Partidos...")
        
        # 1.1 KPI Financiamiento Anual por Partido
        q1 = f"""
        SELECT 
            ejercicio,
            partido_siglas,
            FIRST(denominacion_partido_agrupacion) AS denominacion_partido,
            ROUND(SUM(monto_mensual), 2) AS monto_total_anual,
            ROUND(SUM(monto_mensual) * 100.0 / SUM(SUM(monto_mensual)) OVER(PARTITION BY ejercicio), 2) AS porcentaje_bolsa_anual,
            DENSE_RANK() OVER(PARTITION BY ejercicio ORDER BY SUM(monto_mensual) DESC) AS ranking_anual
        FROM '{src_fin}'
        GROUP BY ejercicio, partido_siglas
        ORDER BY ejercicio, monto_total_anual DESC
        """
        out1 = fin_dir / "kpi_financiamiento_anual_partidos.parquet"
        conn.execute(f"COPY ({q1}) TO '{out1}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out1.name}")

        # 1.2 Serie Mensual por Tipo de Financiamiento
        q2 = f"""
        SELECT 
            ejercicio,
            mes_numero,
            mes_nombre,
            tipo_financiamiento,
            ROUND(SUM(monto_mensual), 2) AS monto_mensual_total,
            COUNT(DISTINCT partido_siglas) AS total_partidos_beneficiarios
        FROM '{src_fin}'
        GROUP BY ejercicio, mes_numero, mes_nombre, tipo_financiamiento
        ORDER BY ejercicio, mes_numero, tipo_financiamiento
        """
        out2 = fin_dir / "serie_mensual_tipo_financiamiento.parquet"
        conn.execute(f"COPY ({q2}) TO '{out2}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out2.name}")

        # 1.3 Comparativa Años Electorales vs Ordinarios
        q3 = f"""
        WITH totales AS (
            SELECT 
                ejercicio,
                CASE WHEN ejercicio IN (2021, 2024) THEN TRUE ELSE FALSE END AS es_anio_electoral,
                ROUND(SUM(monto_mensual), 2) AS monto_total_ejercicio,
                COUNT(DISTINCT partido_siglas) AS partidos_con_registro
            FROM '{src_fin}'
            GROUP BY ejercicio
        )
        SELECT 
            ejercicio,
            es_anio_electoral,
            monto_total_ejercicio,
            ROUND(monto_total_ejercicio - LAG(monto_total_ejercicio) OVER(ORDER BY ejercicio), 2) AS variacion_nominal_anual,
            ROUND((monto_total_ejercicio / NULLIF(LAG(monto_total_ejercicio) OVER(ORDER BY ejercicio), 0) - 1.0) * 100.0, 2) AS variacion_pct_anual,
            partidos_con_registro
        FROM totales
        ORDER BY ejercicio
        """
        out3 = fin_dir / "comparativa_electoral_vs_ordinario.parquet"
        conn.execute(f"COPY ({q3}) TO '{out3}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out3.name}")

    # =========================================================================
    # 2. CONTRATACIONES PÚBLICAS Y PROVEEDORES (2021–2023)
    # =========================================================================
    con_dir = AGREGADOS_DIR / "contrataciones"
    con_dir.mkdir(parents=True, exist_ok=True)
    src_con = LIMPIOS_DIR / "contrataciones/contrataciones_ine_consolidadas_2021_2023.parquet"

    if src_con.exists():
        log("Procesando Contrataciones Públicas...")
        
        # 2.1 KPI por Tipo de Procedimiento (Riesgo / Competitividad)
        q4 = f"""
        SELECT 
            ejercicio,
            COALESCE(NULLIF(TRIM(tipo_procedimiento), ''), 'No especificado') AS tipo_procedimiento,
            COUNT(*) AS total_contratos,
            ROUND(SUM(monto_total_con_impuestos), 2) AS monto_total_con_impuestos,
            ROUND(AVG(monto_total_con_impuestos), 2) AS monto_promedio_por_contrato,
            ROUND(SUM(monto_total_con_impuestos) * 100.0 / SUM(SUM(monto_total_con_impuestos)) OVER(PARTITION BY ejercicio), 2) AS porcentaje_monto_anual,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(PARTITION BY ejercicio), 2) AS porcentaje_contratos_anual
        FROM '{src_con}'
        GROUP BY ejercicio, tipo_procedimiento
        ORDER BY ejercicio, monto_total_con_impuestos DESC
        """
        out4 = con_dir / "kpi_procedimientos_contratacion.parquet"
        conn.execute(f"COPY ({q4}) TO '{out4}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out4.name}")

        # 2.2 Ranking Top 50 Proveedores Históricos
        q5 = f"""
        WITH gran_total AS (
            SELECT SUM(monto_total_con_impuestos) AS monto_global
            FROM '{src_con}'
        )
        SELECT 
            DENSE_RANK() OVER(ORDER BY SUM(monto_total_con_impuestos) DESC) AS ranking,
            proveedor_nombre,
            rfc_proveedor,
            tipo_persona,
            COUNT(*) AS total_contratos,
            MIN(ejercicio) AS primer_ejercicio,
            MAX(ejercicio) AS ultimo_ejercicio,
            ROUND(SUM(monto_total_con_impuestos), 2) AS monto_total_acumulado,
            ROUND(SUM(monto_total_con_impuestos) * 100.0 / (SELECT monto_global FROM gran_total), 2) AS porcentaje_del_gasto_total
        FROM '{src_con}'
        WHERE proveedor_nombre IS NOT NULL AND TRIM(proveedor_nombre) != ''
        GROUP BY proveedor_nombre, rfc_proveedor, tipo_persona
        ORDER BY monto_total_acumulado DESC
        LIMIT 50
        """
        out5 = con_dir / "ranking_top_proveedores.parquet"
        conn.execute(f"COPY ({q5}) TO '{out5}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out5.name}")

        # 2.3 Serie Anual por Materia de Contratación
        q6 = f"""
        SELECT 
            ejercicio,
            COALESCE(NULLIF(TRIM(materia), ''), 'No especificada') AS materia,
            COUNT(*) AS total_contratos,
            ROUND(SUM(monto_total_con_impuestos), 2) AS monto_total_con_impuestos,
            ROUND(SUM(monto_total_con_impuestos) * 100.0 / SUM(SUM(monto_total_con_impuestos)) OVER(PARTITION BY ejercicio), 2) AS porcentaje_monto_anual
        FROM '{src_con}'
        GROUP BY ejercicio, materia
        ORDER BY ejercicio, monto_total_con_impuestos DESC
        """
        out6 = con_dir / "serie_anual_materia_contratacion.parquet"
        conn.execute(f"COPY ({q6}) TO '{out6}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out6.name}")

        # 2.4 Mapa de Contrataciones por Entidad Federativa (Desconcentración territorial)
        q6_geo = f"""
        WITH cat_entidades AS (
            SELECT * FROM (VALUES
                ('00', 'MX-CEN', 'Oficinas Centrales / Nivel Central'),
                ('01', 'MX-AGU', 'Aguascalientes'),
                ('02', 'MX-BCN', 'Baja California'),
                ('03', 'MX-BCS', 'Baja California Sur'),
                ('04', 'MX-CAM', 'Campeche'),
                ('05', 'MX-COA', 'Coahuila'),
                ('06', 'MX-COL', 'Colima'),
                ('07', 'MX-CHP', 'Chiapas'),
                ('08', 'MX-CHH', 'Chihuahua'),
                ('09', 'MX-CMX', 'Ciudad de México'),
                ('10', 'MX-DUR', 'Durango'),
                ('11', 'MX-GUA', 'Guanajuato'),
                ('12', 'MX-GRO', 'Guerrero'),
                ('13', 'MX-HID', 'Hidalgo'),
                ('14', 'MX-JAL', 'Jalisco'),
                ('15', 'MX-MEX', 'Estado de México'),
                ('16', 'MX-MIC', 'Michoacán'),
                ('17', 'MX-MOR', 'Morelos'),
                ('18', 'MX-NAY', 'Nayarit'),
                ('19', 'MX-NLE', 'Nuevo León'),
                ('20', 'MX-OAX', 'Oaxaca'),
                ('21', 'MX-PUE', 'Puebla'),
                ('22', 'MX-QUE', 'Querétaro'),
                ('23', 'MX-ROO', 'Quintana Roo'),
                ('24', 'MX-SLP', 'San Luis Potosí'),
                ('25', 'MX-SIN', 'Sinaloa'),
                ('26', 'MX-SON', 'Sonora'),
                ('27', 'MX-TAB', 'Tabasco'),
                ('28', 'MX-TAM', 'Tamaulipas'),
                ('29', 'MX-TLA', 'Tlaxcala'),
                ('30', 'MX-VER', 'Veracruz'),
                ('31', 'MX-YUC', 'Yucatán'),
                ('32', 'MX-ZAC', 'Zacatecas')
            ) AS t(cve_inegi, codigo_iso, entidad_federativa)
        ),
        contratos_mapeados AS (
            SELECT 
                CASE 
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%aguascalientes%' OR strip_accents(lower(area_solicitante)) LIKE '%ags%' THEN '01'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%baja california sur%' OR strip_accents(lower(area_solicitante)) LIKE '%bcs%' THEN '03'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%baja california%' OR strip_accents(lower(area_solicitante)) LIKE '%bc%' THEN '02'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%campeche%' OR strip_accents(lower(area_solicitante)) LIKE '%camp%' THEN '04'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%coahuila%' OR strip_accents(lower(area_solicitante)) LIKE '%coah%' THEN '05'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%colima%' OR strip_accents(lower(area_solicitante)) LIKE '%col%' THEN '06'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%chiapas%' OR strip_accents(lower(area_solicitante)) LIKE '%chis%' THEN '07'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%chihuahua%' OR strip_accents(lower(area_solicitante)) LIKE '%chih%' THEN '08'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%ciudad de m%' OR strip_accents(lower(area_solicitante)) LIKE '%cdmx%' OR strip_accents(lower(area_solicitante)) LIKE '%distrito federal%' THEN '09'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%durango%' OR strip_accents(lower(area_solicitante)) LIKE '%dgo%' THEN '10'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%guanajuato%' OR strip_accents(lower(area_solicitante)) LIKE '%gto%' THEN '11'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%guerrero%' OR strip_accents(lower(area_solicitante)) LIKE '%gro%' THEN '12'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%hidalgo%' OR strip_accents(lower(area_solicitante)) LIKE '%hgo%' THEN '13'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%jalis%' THEN '14'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%michoac%' THEN '16'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%morelos%' OR strip_accents(lower(area_solicitante)) LIKE '%mor%' THEN '17'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%nayarit%' OR strip_accents(lower(area_solicitante)) LIKE '%nay%' THEN '18'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%nuevo le%' THEN '19'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%oaxaca%' OR strip_accents(lower(area_solicitante)) LIKE '%oax%' THEN '20'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%puebla%' OR strip_accents(lower(area_solicitante)) LIKE '%pue%' THEN '21'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%queretaro%' OR strip_accents(lower(area_solicitante)) LIKE '%qro%' THEN '22'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%quintana roo%' OR strip_accents(lower(area_solicitante)) LIKE '%qroo%' THEN '23'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%san luis potos%' OR strip_accents(lower(area_solicitante)) LIKE '%slp%' THEN '24'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%sinaloa%' OR strip_accents(lower(area_solicitante)) LIKE '%sin%' THEN '25'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%sonora%' OR strip_accents(lower(area_solicitante)) LIKE '%son%' THEN '26'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%tabasco%' OR strip_accents(lower(area_solicitante)) LIKE '%tab%' THEN '27'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%tamaulipas%' OR strip_accents(lower(area_solicitante)) LIKE '%tamps%' THEN '28'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%tlaxcala%' OR strip_accents(lower(area_solicitante)) LIKE '%tlax%' THEN '29'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%veracruz%' OR strip_accents(lower(area_solicitante)) LIKE '%ver%' THEN '30'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%yucat%' OR strip_accents(lower(area_solicitante)) LIKE '%yuc%' THEN '31'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%zacatecas%' OR strip_accents(lower(area_solicitante)) LIKE '%zac%' THEN '32'
                    WHEN strip_accents(lower(area_solicitante)) LIKE '%mexico%' OR strip_accents(lower(area_solicitante)) LIKE '%edomex%' THEN '15'
                    ELSE '00'
                END AS cve_inegi,
                monto_total_con_impuestos
            FROM '{src_con}'
        ),
        agregados_con AS (
            SELECT 
                cve_inegi,
                COUNT(*) AS total_contratos,
                ROUND(SUM(monto_total_con_impuestos), 2) AS monto_total_contratado,
                ROUND(AVG(monto_total_con_impuestos), 2) AS monto_promedio_contrato
            FROM contratos_mapeados
            GROUP BY cve_inegi
        )
        SELECT 
            c.cve_inegi,
            c.codigo_iso,
            c.entidad_federativa,
            COALESCE(a.total_contratos, 0) AS total_contratos,
            COALESCE(a.monto_total_contratado, 0.0) AS monto_total_contratado,
            COALESCE(a.monto_promedio_contrato, 0.0) AS monto_promedio_contrato,
            ROUND(COALESCE(a.monto_total_contratado, 0.0) * 100.0 / SUM(COALESCE(a.monto_total_contratado, 0.0)) OVER(), 2) AS porcentaje_monto_total,
            DENSE_RANK() OVER(ORDER BY COALESCE(a.monto_total_contratado, 0.0) DESC) AS ranking_monto
        FROM cat_entidades c
        LEFT JOIN agregados_con a ON c.cve_inegi = a.cve_inegi
        ORDER BY c.cve_inegi
        """
        out6_geo = con_dir / "mapa_contrataciones_por_estado.parquet"
        conn.execute(f"COPY ({q6_geo}) TO '{out6_geo}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out6_geo.name}")

    # =========================================================================
    # 3. PRESUPUESTO Y EJECUCIÓN DEL GASTO (2020 vs 2025)
    # =========================================================================
    pre_dir = AGREGADOS_DIR / "presupuesto"
    pre_dir.mkdir(parents=True, exist_ok=True)
    src_pre = LIMPIOS_DIR / "presupuesto/presupuesto_partidas_2020_2025.parquet"

    if src_pre.exists():
        log("Procesando Presupuesto...")
        
        # 3.1 Ejecución Presupuestal por Capítulo
        q7 = f"""
        SELECT 
            ejercicio,
            clave_capitulo,
            CASE 
                WHEN clave_capitulo = '1000' THEN 'Servicios Personales'
                WHEN clave_capitulo = '2000' THEN 'Materiales y Suministros'
                WHEN clave_capitulo = '3000' THEN 'Servicios Generales'
                WHEN clave_capitulo = '4000' THEN 'Transferencias, Asignaciones, Subsidios y Partidos'
                WHEN clave_capitulo = '5000' THEN 'Bienes Muebles, Inmuebles e Intangibles'
                ELSE 'Otros Capítulos'
            END AS nombre_capitulo,
            ROUND(SUM(gasto_aprobado), 2) AS presupuesto_aprobado,
            ROUND(SUM(gasto_modificado), 2) AS presupuesto_modificado,
            ROUND(SUM(gasto_comprometido), 2) AS presupuesto_comprometido,
            ROUND(SUM(gasto_devengado), 2) AS presupuesto_devengado,
            ROUND(SUM(gasto_pagado), 2) AS presupuesto_pagado,
            ROUND(SUM(gasto_pagado) - SUM(gasto_aprobado), 2) AS variacion_pagado_vs_aprobado,
            ROUND((SUM(gasto_pagado) / NULLIF(SUM(gasto_aprobado), 0) - 1.0) * 100.0, 2) AS porcentaje_variacion
        FROM '{src_pre}'
        GROUP BY ejercicio, clave_capitulo
        ORDER BY ejercicio, clave_capitulo
        """
        out7 = pre_dir / "ejecucion_presupuestal_capitulos.parquet"
        conn.execute(f"COPY ({q7}) TO '{out7}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out7.name}")

        # 3.2 Top 20 Partidas con Mayor Gasto Pagado
        q8 = f"""
        WITH rank_partidas AS (
            SELECT 
                ejercicio,
                clave_capitulo,
                clave_partida,
                denominacion_partida,
                ROUND(SUM(gasto_aprobado), 2) AS gasto_aprobado,
                ROUND(SUM(gasto_pagado), 2) AS gasto_pagado,
                ROUND(SUM(gasto_pagado) - SUM(gasto_aprobado), 2) AS variacion_monto,
                DENSE_RANK() OVER(PARTITION BY ejercicio ORDER BY SUM(gasto_pagado) DESC) AS ranking_anual
            FROM '{src_pre}'
            GROUP BY ejercicio, clave_capitulo, clave_partida, denominacion_partida
        )
        SELECT * FROM rank_partidas
        WHERE ranking_anual <= 20
        ORDER BY ejercicio, ranking_anual
        """
        out8 = pre_dir / "top_partidas_gasto.parquet"
        conn.execute(f"COPY ({q8}) TO '{out8}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out8.name}")

    # =========================================================================
    # 4. PERSONAL Y NÓMINA (2020–2026)
    # =========================================================================
    per_dir = AGREGADOS_DIR / "personal_y_nomina"
    per_dir.mkdir(parents=True, exist_ok=True)
    src_pad = LIMPIOS_DIR / "personal_y_nomina/padron_historico_empleados_2020_2026.parquet"
    src_rem = LIMPIOS_DIR / "personal_y_nomina/remuneraciones_personal_2025.parquet"
    src_hon = LIMPIOS_DIR / "personal_y_nomina/contrataciones_honorarios_2025.parquet"

    if src_pad.exists():
        log("Procesando Padrón y Personal...")
        # 4.1 Evolución del Headcount Histórico
        q9 = f"""
        SELECT 
            ejercicio,
            COUNT(DISTINCT rfc_raiz_sat) AS empleados_unicos_rfc,
            COUNT(*) AS total_registros_padron
        FROM '{src_pad}'
        WHERE rfc_raiz_sat IS NOT NULL AND rfc_raiz_sat != ''
        GROUP BY ejercicio
        ORDER BY ejercicio
        """
        out9 = per_dir / "evolucion_plantilla_headcount.parquet"
        conn.execute(f"COPY ({q9}) TO '{out9}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out9.name}")

    if src_rem.exists():
        # 4.2 Distribución Salarial por Puesto (2025)
        q10 = f"""
        SELECT 
            denominacion_puesto,
            cargo,
            COUNT(*) AS total_plazas_reportadas,
            ROUND(AVG(sueldo_mensual_bruto), 2) AS sueldo_bruto_promedio,
            ROUND(AVG(sueldo_mensual_neto), 2) AS sueldo_neto_promedio,
            ROUND(MIN(sueldo_mensual_neto), 2) AS sueldo_neto_minimo,
            ROUND(MAX(sueldo_mensual_neto), 2) AS sueldo_neto_maximo
        FROM '{src_rem}'
        WHERE denominacion_puesto IS NOT NULL AND denominacion_puesto != ''
        GROUP BY denominacion_puesto, cargo
        ORDER BY sueldo_neto_promedio DESC
        """
        out10 = per_dir / "distribucion_salarial_por_puesto_2025.parquet"
        conn.execute(f"COPY ({q10}) TO '{out10}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out10.name}")

    if src_rem.exists() and src_hon.exists():
        # 4.3 Comparativa Nómina de Estructura vs Honorarios (2025)
        q11 = f"""
        WITH nom AS (
            SELECT 
                'Personal de Nómina / Estructura' AS regimen_contratacion,
                COUNT(DISTINCT nombre_completo) AS total_personas_unicas,
                ROUND(SUM(sueldo_mensual_bruto), 2) AS masa_mensual_bruta,
                ROUND(SUM(sueldo_mensual_neto), 2) AS masa_mensual_neta,
                ROUND(AVG(sueldo_mensual_neto), 2) AS costo_promedio_mensual_persona
            FROM '{src_rem}'
            WHERE periodo_trimestre = 'Trimestre 4' OR periodo_trimestre LIKE '%4%'
        ),
        hon AS (
            SELECT 
                'Contrataciones por Honorarios Asimilados' AS regimen_contratacion,
                COUNT(DISTINCT nombre_completo) AS total_personas_unicas,
                ROUND(SUM(remuneracion_mensual_bruta), 2) AS masa_mensual_bruta,
                ROUND(SUM(remuneracion_mensual_neta), 2) AS masa_mensual_neta,
                ROUND(AVG(remuneracion_mensual_neta), 2) AS costo_promedio_mensual_persona
            FROM '{src_hon}'
        )
        SELECT * FROM nom UNION ALL SELECT * FROM hon
        """
        out11 = per_dir / "comparativa_nomina_vs_honorarios_2025.parquet"
        conn.execute(f"COPY ({q11}) TO '{out11}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out11.name}")

    # =========================================================================
    # 5. VIÁTICOS Y COMISIONES (2022–2025)
    # =========================================================================
    via_dir = AGREGADOS_DIR / "viaticos"
    via_dir.mkdir(parents=True, exist_ok=True)
    src_via = LIMPIOS_DIR / "viaticos/gastos_viaticos_comisiones_2022_2025.parquet"

    if src_via.exists():
        log("Procesando Viáticos...")
        # 5.1 KPI Nacional vs Internacional
        q12 = f"""
        SELECT 
            ejercicio,
            COALESCE(NULLIF(TRIM(tipo_viaje), ''), 'Nacional') AS tipo_viaje,
            COUNT(*) AS total_comisiones,
            ROUND(SUM(importe_total_erogado), 2) AS gasto_total_erogado,
            ROUND(AVG(importe_total_erogado), 2) AS gasto_promedio_por_comision
        FROM '{src_via}'
        GROUP BY ejercicio, tipo_viaje
        ORDER BY ejercicio, tipo_viaje
        """
        out12 = via_dir / "kpi_viaticos_nacional_internacional.parquet"
        conn.execute(f"COPY ({q12}) TO '{out12}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out12.name}")

        # 5.2 Ranking de Áreas con Mayor Gasto en Viáticos
        q13 = f"""
        SELECT 
            DENSE_RANK() OVER(ORDER BY SUM(importe_total_erogado) DESC) AS ranking,
            area_adscripcion,
            COUNT(*) AS total_comisiones,
            ROUND(SUM(importe_total_erogado), 2) AS gasto_total_erogado,
            ROUND(AVG(importe_total_erogado), 2) AS gasto_promedio_por_comision
        FROM '{src_via}'
        WHERE area_adscripcion IS NOT NULL AND TRIM(area_adscripcion) != ''
        GROUP BY area_adscripcion
        ORDER BY gasto_total_erogado DESC
        LIMIT 25
        """
        out13 = via_dir / "ranking_areas_gasto_viaticos.parquet"
        conn.execute(f"COPY ({q13}) TO '{out13}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out13.name}")

        # 5.3 Mapa de Viáticos por Entidad Federativa de Destino (32 entidades)
        q13_geo = f"""
        WITH cat_entidades AS (
            SELECT * FROM (VALUES
                ('01', 'MX-AGU', 'Aguascalientes'),
                ('02', 'MX-BCN', 'Baja California'),
                ('03', 'MX-BCS', 'Baja California Sur'),
                ('04', 'MX-CAM', 'Campeche'),
                ('05', 'MX-COA', 'Coahuila'),
                ('06', 'MX-COL', 'Colima'),
                ('07', 'MX-CHP', 'Chiapas'),
                ('08', 'MX-CHH', 'Chihuahua'),
                ('09', 'MX-CMX', 'Ciudad de México'),
                ('10', 'MX-DUR', 'Durango'),
                ('11', 'MX-GUA', 'Guanajuato'),
                ('12', 'MX-GRO', 'Guerrero'),
                ('13', 'MX-HID', 'Hidalgo'),
                ('14', 'MX-JAL', 'Jalisco'),
                ('15', 'MX-MEX', 'Estado de México'),
                ('16', 'MX-MIC', 'Michoacán'),
                ('17', 'MX-MOR', 'Morelos'),
                ('18', 'MX-NAY', 'Nayarit'),
                ('19', 'MX-NLE', 'Nuevo León'),
                ('20', 'MX-OAX', 'Oaxaca'),
                ('21', 'MX-PUE', 'Puebla'),
                ('22', 'MX-QUE', 'Querétaro'),
                ('23', 'MX-ROO', 'Quintana Roo'),
                ('24', 'MX-SLP', 'San Luis Potosí'),
                ('25', 'MX-SIN', 'Sinaloa'),
                ('26', 'MX-SON', 'Sonora'),
                ('27', 'MX-TAB', 'Tabasco'),
                ('28', 'MX-TAM', 'Tamaulipas'),
                ('29', 'MX-TLA', 'Tlaxcala'),
                ('30', 'MX-VER', 'Veracruz'),
                ('31', 'MX-YUC', 'Yucatán'),
                ('32', 'MX-ZAC', 'Zacatecas')
            ) AS t(cve_inegi, codigo_iso, entidad_federativa)
        ),
        viajes_mapeados AS (
            SELECT 
                CASE 
                    WHEN strip_accents(lower(estado_destino)) LIKE '%aguascalientes%' THEN '01'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%baja california sur%' THEN '03'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%baja california%' THEN '02'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%campeche%' THEN '04'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%coahuila%' THEN '05'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%colima%' THEN '06'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%chiapas%' THEN '07'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%chihuahua%' THEN '08'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%ciudad de m%' OR strip_accents(lower(estado_destino)) LIKE '%cdmx%' OR strip_accents(lower(estado_destino)) LIKE '%distrito federal%' THEN '09'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%durango%' THEN '10'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%guanajuato%' THEN '11'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%guerrero%' THEN '12'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%hidalgo%' THEN '13'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%jalis%' OR strip_accents(lower(estado_destino)) LIKE '%jalico%' THEN '14'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%michoac%' THEN '16'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%morelos%' THEN '17'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%nayarit%' THEN '18'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%nuevo le%' THEN '19'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%oaxaca%' THEN '20'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%puebla%' THEN '21'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%queretaro%' THEN '22'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%quintana roo%' THEN '23'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%san luis potos%' THEN '24'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%sinaloa%' THEN '25'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%sonora%' THEN '26'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%tabasco%' THEN '27'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%tamaulipas%' THEN '28'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%tlaxcala%' THEN '29'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%veracruz%' THEN '30'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%yucat%' THEN '31'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%zacatecas%' THEN '32'
                    WHEN strip_accents(lower(estado_destino)) LIKE '%mexico%' THEN '15'
                    ELSE NULL
                END AS cve_inegi,
                importe_total_erogado
            FROM '{src_via}'
            WHERE tipo_viaje = 'Nacional'
        ),
        agregados_viajes AS (
            SELECT 
                cve_inegi,
                COUNT(*) AS total_viajes,
                ROUND(SUM(importe_total_erogado), 2) AS gasto_total_erogado,
                ROUND(AVG(importe_total_erogado), 2) AS gasto_promedio_viaje
            FROM viajes_mapeados
            WHERE cve_inegi IS NOT NULL
            GROUP BY cve_inegi
        )
        SELECT 
            c.cve_inegi,
            c.codigo_iso,
            c.entidad_federativa,
            COALESCE(a.total_viajes, 0) AS total_viajes,
            COALESCE(a.gasto_total_erogado, 0.0) AS gasto_total_erogado,
            COALESCE(a.gasto_promedio_viaje, 0.0) AS gasto_promedio_viaje,
            ROUND(COALESCE(a.gasto_total_erogado, 0.0) * 100.0 / SUM(COALESCE(a.gasto_total_erogado, 0.0)) OVER(), 2) AS porcentaje_gasto_nacional,
            DENSE_RANK() OVER(ORDER BY COALESCE(a.gasto_total_erogado, 0.0) DESC) AS ranking_gasto_nacional
        FROM cat_entidades c
        LEFT JOIN agregados_viajes a ON c.cve_inegi = a.cve_inegi
        ORDER BY c.cve_inegi
        """
        out13_geo = via_dir / "mapa_viaticos_por_estado.parquet"
        conn.execute(f"COPY ({q13_geo}) TO '{out13_geo}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out13_geo.name}")

    # =========================================================================
    # 6. PUBLICIDAD OFICIAL (2025)
    # =========================================================================
    pub_dir = AGREGADOS_DIR / "publicidad_oficial"
    pub_dir.mkdir(parents=True, exist_ok=True)
    src_pub = LIMPIOS_DIR / "publicidad_oficial/publicidad_oficial_2025.parquet"

    if src_pub.exists():
        log("Procesando Publicidad Oficial...")
        q14 = f"""
        WITH total_pub AS (
            SELECT SUM(costo_por_unidad) AS gasto_global
            FROM '{src_pub}'
        )
        SELECT 
            tipo_medio,
            COUNT(*) AS total_pautas,
            ROUND(SUM(costo_por_unidad), 2) AS gasto_total,
            ROUND(AVG(costo_por_unidad), 2) AS gasto_promedio_por_pauta,
            ROUND(SUM(costo_por_unidad) * 100.0 / (SELECT gasto_global FROM total_pub), 2) AS porcentaje_del_gasto_total
        FROM '{src_pub}'
        GROUP BY tipo_medio
        ORDER BY gasto_total DESC
        """
        out14 = pub_dir / "gasto_publicidad_por_medio_2025.parquet"
        conn.execute(f"COPY ({q14}) TO '{out14}' (FORMAT PARQUET, COMPRESSION ZSTD)")
        log(f"  -> Guardado: {out14.name}")

    # =========================================================================
    # 7. TABLERO MAESTRO EJECUTIVO MULTIDIMENSIONAL (2020–2026)
    # =========================================================================
    res_dir = AGREGADOS_DIR / "resumen_ejecutivo"
    res_dir.mkdir(parents=True, exist_ok=True)
    log("Generando Tablero Maestro Ejecutivo Anual...")

    q15 = f"""
    WITH anios AS (
        SELECT UNNEST([2020, 2021, 2022, 2023, 2024, 2025, 2026]) AS ejercicio
    ),
    fin AS (
        SELECT ejercicio, ROUND(SUM(monto_mensual), 2) AS financiamiento_partidos_total
        FROM '{src_fin}'
        GROUP BY ejercicio
    ),
    con AS (
        SELECT ejercicio, COUNT(*) AS total_contratos_publicos, ROUND(SUM(monto_total_con_impuestos), 2) AS monto_contrataciones_total
        FROM '{src_con}'
        GROUP BY ejercicio
    ),
    pre AS (
        SELECT ejercicio, ROUND(SUM(gasto_aprobado), 2) AS presupuesto_aprobado_total, ROUND(SUM(gasto_pagado), 2) AS presupuesto_pagado_total
        FROM '{src_pre}'
        GROUP BY ejercicio
    ),
    via AS (
        SELECT ejercicio, COUNT(*) AS total_comisiones_viaticos, ROUND(SUM(importe_total_erogado), 2) AS viaticos_total_erogado
        FROM '{src_via}'
        GROUP BY ejercicio
    ),
    pad AS (
        SELECT ejercicio, COUNT(DISTINCT rfc_raiz_sat) AS plantilla_empleados_activos
        FROM '{src_pad}'
        WHERE rfc_raiz_sat IS NOT NULL AND rfc_raiz_sat != ''
        GROUP BY ejercicio
    )
    SELECT 
        a.ejercicio,
        pre.presupuesto_aprobado_total,
        pre.presupuesto_pagado_total,
        fin.financiamiento_partidos_total,
        con.total_contratos_publicos,
        con.monto_contrataciones_total,
        via.total_comisiones_viaticos,
        via.viaticos_total_erogado,
        pad.plantilla_empleados_activos
    FROM anios a
    LEFT JOIN pre ON a.ejercicio = pre.ejercicio
    LEFT JOIN fin ON a.ejercicio = fin.ejercicio
    LEFT JOIN con ON a.ejercicio = con.ejercicio
    LEFT JOIN via ON a.ejercicio = via.ejercicio
    LEFT JOIN pad ON a.ejercicio = pad.ejercicio
    ORDER BY a.ejercicio
    """
    out15 = res_dir / "resumen_ejecutivo_ine_anual.parquet"
    conn.execute(f"COPY ({q15}) TO '{out15}' (FORMAT PARQUET, COMPRESSION ZSTD)")
    log(f"  -> Guardado: {out15.name}")

    conn.close()
    log("¡Capa de agregación analítica generada exitosamente!")

if __name__ == "__main__":
    ejecutar_agregaciones()
