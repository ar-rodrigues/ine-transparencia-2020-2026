#!/usr/bin/env python3
"""
Generador del Informe Integral de Auditoría PNT - INE Ejercicio Fiscal 2025
Auditoría Masiva (935k registros), Masa Salarial (PA-04), Honorarios (PA-02), Viáticos (PA-07), Contratos (59875), Cruce Onomástico y Quinquenio 2021-2025.
"""

import json
import os
import base64

def get_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# Cargar datos calculados
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_path = os.path.join(base_dir, "analisis/auditoria_datos_calculados_2025.json")
with open(data_path) as f:
    data = json.load(f)

# Logos
logo_agil_b64 = get_b64("/home/nazulpg/Documentos/logos/logo_agil.png")

# Formateadores
def mx(v):
    if v is None:
        return "—"
    try:
        return f"${float(v):,.2f}"
    except:
        return "—"

def n(v):
    if v is None:
        return "—"
    try:
        return f"{int(v):,}"
    except:
        return "—"

def pct(v):
    if v is None:
        return "—"
    try:
        return f"{float(v):.2f}%"
    except:
        return "—"

# Construcción de tablas
# 1. Tabla Formatos Presentes
rows_presentes = ""
for fmt in sorted(data['formatos_presentes'], key=lambda x: x['filas'], reverse=True)[:35]:
    rows_presentes += f"""
    <tr>
        <td><strong>{fmt['formato']}</strong></td>
        <td><code>{fmt['obligacion'] or 'ESPECÍFICA / GENERAL'}</code></td>
        <td class="text-right"><strong>{n(fmt['filas'])}</strong></td>
        <td class="text-center">{fmt['cols']}</td>
        <td class="text-center">{fmt['archivos']}</td>
        <td class="text-center"><span class="badge badge-success">DISPONIBLE</span></td>
    </tr>
    """

# 2. Tabla Formatos Faltantes Art 70
rows_faltantes = ""
for falt in data['formatos_faltantes_art70']:
    rows_faltantes += f"""
    <tr>
        <td><strong>{falt['fraccion']}</strong></td>
        <td>{falt['nombre']}</td>
        <td class="text-center"><span class="badge badge-danger">{falt['estado']}</span></td>
        <td>{falt['impacto']}</td>
    </tr>
    """

# 3. Top Puestos Nómina (43315)
rows_sueldos_puestos = ""
for p in data['sueldos_pa04']['top_puestos']:
    rows_sueldos_puestos += f"""
    <tr>
        <td><strong>{p['puesto']}</strong></td>
        <td class="text-right"><strong>{n(p['registros'])}</strong></td>
    </tr>
    """

# 4. Outliers Salariales
rows_outliers = ""
for out in data['sueldos_pa04']['outliers_altos_ingresos'][:12]:
    rows_outliers += f"""
    <tr>
        <td><strong>{out['nombre']}</strong></td>
        <td>{out['puesto']}</td>
        <td><small>{out['area'][:50]}</small></td>
        <td class="text-right"><strong>{mx(out['bruto'])}</strong></td>
        <td class="text-right">{mx(out['neto'])}</td>
    </tr>
    """

# 5. Top Honorarios (43343)
rows_honorarios = ""
for h in data['honorarios_pa02']['top_personas_monto'][:12]:
    rows_honorarios += f"""
    <tr>
        <td><strong>{h['nombre']}</strong></td>
        <td class="text-center"><strong>{h['contratos']}</strong></td>
        <td class="text-right"><strong>{mx(h['monto'])}</strong></td>
    </tr>
    """

# 6. Top Comisionados Viáticos (43316)
rows_viaticos = ""
for v in data['viaticos_pa07']['top_comisionados']:
    rows_viaticos += f"""
    <tr>
        <td><strong>{v['nombre']}</strong></td>
        <td class="text-right"><strong>{n(v['comisiones'])}</strong></td>
    </tr>
    """

# 7. Desglose Contrataciones 2025 (59875)
rows_contratos_proc = ""
for cp in data['contratos_pa01']['desglose_procedimientos']:
    rows_contratos_proc += f"""
    <tr>
        <td><strong>{cp['tipo']}</strong></td>
        <td class="text-center"><strong>{n(cp['contratos'])}</strong></td>
        <td class="text-right"><strong>{mx(cp['monto'])}</strong></td>
        <td class="text-center"><strong>{pct(cp['pct_monto'])}</strong></td>
    </tr>
    """

# 8. Top Proveedores 2025
rows_top_monto = ""
for p in data['contratos_pa01']['top_monto'][:12]:
    tipo_prov = "Persona Moral" if p['is_moral'] else "Persona Física"
    rows_top_monto += f"""
    <tr>
        <td><code>{p['rfc']}</code></td>
        <td><strong>{p['razon']}</strong></td>
        <td class="text-center">{tipo_prov}</td>
        <td class="text-center">{p['year'] or '—'}</td>
        <td class="text-right"><strong>{mx(p['monto_total'])}</strong></td>
        <td class="text-center">{n(p['contratos_totales'])}</td>
    </tr>
    """

# 9. Presupuesto por Capítulos 2025
rows_presupuesto = ""
for c in data['partidas_pa08']['capitulos']:
    pag_pct = (c['pagado'] / c['aprobado'] * 100) if c['aprobado'] > 0 else 0
    rows_presupuesto += f"""
    <tr>
        <td><strong>Capítulo {c['capitulo']}</strong></td>
        <td>{c['nombre']}</td>
        <td class="text-center">{c['partidas']}</td>
        <td class="text-right">{mx(c['aprobado'])}</td>
        <td class="text-right">{mx(c['modificado'])}</td>
        <td class="text-right">{mx(c['devengado'])}</td>
        <td class="text-right"><strong>{mx(c['ejercido'])}</strong></td>
        <td class="text-right"><strong>{mx(c['pagado'])}</strong></td>
        <td class="text-center">{pct(pag_pct)}</td>
    </tr>
    """

# 10. Financiamiento a Partidos Políticos
rows_partidos = ""
for pt in data['partidos_pa05']['detalle']:
    rows_partidos += f"""
    <tr>
        <td><strong>{pt['partido']}</strong></td>
        <td class="text-right"><strong>{mx(pt['mensual_acumulado'])}</strong></td>
        <td class="text-right">{mx(pt['anual_referencia'])}</td>
        <td class="text-center">{pt['registros']}</td>
        <td><small>{', '.join(pt['tipos'])[:60]}...</small></td>
    </tr>
    """

# 11. Cruce Quinquenal 2021-2025
rows_quinquenio = ""
for q in data['cruce_quinquenal'][:15]:
    rows_quinquenio += f"""
    <tr>
        <td><code>{q['rfc']}</code></td>
        <td><strong>{q['razon']}</strong></td>
        <td class="text-right">{mx(q['monto_2021'])}</td>
        <td class="text-right">{mx(q['monto_2022'])}</td>
        <td class="text-right">{mx(q['monto_2023'])}</td>
        <td class="text-right">{mx(q['monto_2024'])}</td>
        <td class="text-right">{mx(q['monto_2025'])}</td>
        <td class="text-right"><strong>{mx(q['monto_quinquenio'])}</strong></td>
    </tr>
    """

html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Informe Integral de Auditoría PNT — INE Ejercicio 2025</title>
  <style>
    @page {{
      size: letter;
      margin: 18mm 15mm 20mm 15mm;
      @bottom-right {{
        content: counter(page) " / " counter(pages);
        font-size: 8pt;
        color: #555;
      }}
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #222;
      line-height: 1.45;
      margin: 0;
      padding: 20px;
      background: #fdfdfd;
      font-size: 10pt;
    }}
    .header-table {{
      width: 100%;
      border-bottom: 3px solid #0B2545;
      padding-bottom: 15px;
      margin-bottom: 25px;
    }}
    .header-logo {{
      width: 230px;
      vertical-align: middle;
    }}
    .header-logo img {{
      max-width: 220px;
      height: auto;
    }}
    .header-title-cell {{
      text-align: right;
      vertical-align: middle;
    }}
    .header-motto {{
      font-size: 9.5pt;
      font-style: italic;
      color: #0077b6;
      font-weight: bold;
      margin-bottom: 5px;
    }}
    .header-title {{
      font-size: 18pt;
      font-weight: 800;
      color: #0B2545;
      margin: 0;
      letter-spacing: -0.5px;
    }}
    .header-sub {{
      font-size: 10pt;
      color: #4a5568;
      margin-top: 3px;
    }}
    h1, h2, h3, h4 {{
      color: #0B2545;
      font-weight: 700;
      page-break-after: avoid;
    }}
    h2 {{
      border-bottom: 2px solid #e2e8f0;
      padding-bottom: 6px;
      margin-top: 28px;
      font-size: 13pt;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    h3 {{
      font-size: 11pt;
      margin-top: 18px;
      color: #1e3a8a;
    }}
    p, ul, ol {{
      margin-bottom: 10px;
    }}
    .alert-box {{
      background: #fff5f5;
      border-left: 4px solid #e53e3e;
      padding: 12px 16px;
      margin: 15px 0;
      border-radius: 0 4px 4px 0;
      font-size: 9.5pt;
    }}
    .alert-box.info {{
      background: #ebf8ff;
      border-left-color: #3182ce;
    }}
    .alert-box.warning {{
      background: #fffaf0;
      border-left-color: #dd6b20;
    }}
    .kpi-grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin: 20px 0;
    }}
    .kpi-card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-top: 3px solid #0B2545;
      border-radius: 4px;
      padding: 12px;
      text-align: center;
      box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }}
    .kpi-card.alert {{
      border-top-color: #e53e3e;
    }}
    .kpi-value {{
      font-size: 15pt;
      font-weight: 800;
      color: #0B2545;
      margin-bottom: 4px;
    }}
    .kpi-label {{
      font-size: 7.5pt;
      text-transform: uppercase;
      color: #718096;
      font-weight: 600;
      letter-spacing: 0.5px;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 14px 0;
      font-size: 8.5pt;
      page-break-inside: auto;
    }}
    tr {{
      page-break-inside: avoid;
      page-break-after: auto;
    }}
    th, td {{
      padding: 6px 8px;
      border: 1px solid #cbd5e1;
      text-align: left;
    }}
    th {{
      background-color: #0B2545;
      color: #ffffff;
      font-weight: 600;
      font-size: 8pt;
      text-transform: uppercase;
    }}
    tr:nth-child(even) {{
      background-color: #f8fafc;
    }}
    .text-right {{
      text-align: right;
    }}
    .text-center {{
      text-align: center;
    }}
    .badge {{
      display: inline-block;
      padding: 2px 6px;
      font-size: 7pt;
      font-weight: 700;
      border-radius: 3px;
      text-transform: uppercase;
    }}
    .badge-success {{
      background-color: #def7ec;
      color: #03543f;
    }}
    .badge-danger {{
      background-color: #fde8e8;
      color: #9b1c1c;
    }}
    .badge-warning {{
      background-color: #feecdc;
      color: #944403;
    }}
    .badge-info {{
      background-color: #e1effe;
      color: #1e429f;
    }}
    .finding-card {{
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-left: 5px solid #0B2545;
      border-radius: 4px;
      padding: 14px;
      margin: 14px 0;
      page-break-inside: avoid;
    }}
    .finding-card.ha {{
      border-left-color: #dc2626;
    }}
    .finding-card.hb {{
      border-left-color: #d97706;
    }}
    .finding-card.hc {{
      border-left-color: #2563eb;
    }}
    .finding-title {{
      font-size: 10.5pt;
      font-weight: 700;
      color: #1e293b;
      margin-bottom: 6px;
      display: flex;
      justify-content: space-between;
    }}
    .footer-block {{
      margin-top: 40px;
      border-top: 2px solid #0B2545;
      padding-top: 20px;
      text-align: center;
      page-break-inside: avoid;
    }}
    .footer-motto {{
      font-size: 10.5pt;
      font-style: italic;
      color: #0077b6;
      font-weight: 700;
      margin-bottom: 12px;
    }}
    .footer-sign {{
      font-size: 9pt;
      line-height: 1.5;
      color: #1e293b;
    }}
    .scroll-table {{
      overflow-x: auto;
      margin: 10px 0;
    }}
  </style>
</head>
<body>

  <!-- ENCABEZADO REGLAMENTARIO AGIL SOLUTIONS -->
  <table class="header-table">
    <tr>
      <td class="header-logo">
        <img src="data:image/png;base64,{logo_agil_b64}" alt="AGIL SOLUTIONS">
      </td>
      <td class="header-title-cell">
        <div class="header-motto">"Lo que no se mide, no se puede Gestionar"</div>
        <div class="header-title">AUDITORÍA INTEGRAL DE TRANSPARENCIA PNT</div>
        <div class="header-sub"><strong>INSTITUTO NACIONAL ELECTORAL (INE) — EJERCICIO FISCAL 2025</strong></div>
        <div class="header-sub">Auditoría Masiva de Nómina, Honorarios y Quinquenio | Órgano Garante: FED - OIC-INE | PNT SIPOT</div>
      </td>
    </tr>
  </table>

  <!-- 1. RESUMEN EJECUTIVO Y KPIS -->
  <h2>1. Resumen Ejecutivo y Métricas Clave</h2>
  <p>
    El presente informe documenta los resultados de la auditoría exhaustiva e independiente aplicada a la totalidad de la información pública registrada en la <strong>Plataforma Nacional de Transparencia (PNT)</strong> correspondiente al <strong>Instituto Nacional Electoral (INE) para el ejercicio fiscal 2025</strong>.
  </p>
  <p>
    En este ejercicio, el repositorio del INE alcanzó un volumen monumental de <strong>935,597 registros estructurados en 83 formatos oficiales</strong>, publicando por primera vez en toda la serie analizada la <strong>Masa Salarial Completa (Formato 43315 con 169,885 filas y 75,985 personas)</strong>, el personal contratado por <strong>Honorarios Asimilados (Formato 43343 con 74,079 contratos por $3,458.4 M)</strong>, <strong>Viáticos masivos (Formato 43316 con 99,842 filas)</strong> y Declaraciones Patrimoniales (85,646 registros). Se ejecutó el cruce onomástico formal entre nómina y honorarios, así como la consolidación del <strong>quinquenio histórico completo 2021-2025</strong>.
  </p>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-value">{n(data['total_registros_descargados'])}</div>
      <div class="kpi-label">Registros Auditados (100%)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-value">{n(data['sueldos_pa04']['personas_unicas'])}</div>
      <div class="kpi-label">Personas en Nómina (PA-04)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-value">{mx(data['honorarios_pa02']['monto_total_bruto'])}</div>
      <div class="kpi-label">Monto Honorarios (PA-02)</div>
    </div>
    <div class="kpi-card alert">
      <div class="kpi-value">{n(data['cruces_onomasticos']['total_coincidencias_sueldos_honorarios'])}</div>
      <div class="kpi-label">Coincidencias Nómina ∩ Honorarios</div>
    </div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-value">{n(data['viaticos_pa07']['personas_comisionadas_unicas'])}</div>
      <div class="kpi-label">Comisionados Viáticos (PA-07)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-value">{mx(data['contratos_pa01']['monto_gran_total'])}</div>
      <div class="kpi-label">Contratos Totales (59875)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-value">{mx(data['partidas_pa08']['total_pagado'])}</div>
      <div class="kpi-label">Gasto Total Pagado 2025</div>
    </div>
    <div class="kpi-card alert">
      <div class="kpi-value">536</div>
      <div class="kpi-label">Outliers Salariales (≥$150k)</div>
    </div>
  </div>

  <!-- 2. PARTE I: INVESTIGACIÓN DOCUMENTAL RIGUROSA (PRESENTE VS FALTANTE) -->
  <h2>2. Parte I: Investigación de Documentación Presente vs. Faltante (LGTAIP)</h2>

  <h3>2.1 Documentación Pública Presente en PNT (83 Formatos Descargados)</h3>
  <p>
    En 2025 el INE logró una apertura sin precedentes en la PNT, completando <strong>83 formatos oficiales</strong>. A continuación se presentan los 35 formatos de mayor envergadura:
  </p>
  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>Formato PNT Oficial</th>
          <th>Obligación / Marco Normativo</th>
          <th class="text-right">Registros</th>
          <th class="text-center">Columnas</th>
          <th class="text-center">Partes</th>
          <th class="text-center">Estatus</th>
        </tr>
      </thead>
      <tbody>
        {rows_presentes}
      </tbody>
    </table>
  </div>

  <h3>2.2 Observación de Información Faltante y Brechas Restantes (Art. 70 LGTAIP)</h3>
  <p>
    A diferencia de los ejercicios 2021 a 2024 donde existían vacíos de 38 a 23 fracciones sustantivas, en 2025 la cobertura alcanzó más del 90% de las obligaciones comunes del Artículo 70 de la LGTAIP. Únicamente se identificaron áreas de oportunidad no estructuradas en las siguientes materias:
  </p>
  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>Fracción Art. 70</th>
          <th>Materia Omitida / Desierta</th>
          <th class="text-center">Condición en Repositorio</th>
          <th>Riesgo e Impacto para la Auditoría</th>
        </tr>
      </thead>
      <tbody>
        {rows_faltantes}
      </tbody>
    </table>
  </div>

  <!-- 3. PARTE II: PROCEDIMIENTOS DE AUDITORÍA FORENSE (PA-01 A PA-08) -->
  <h2>3. Parte II: Procedimientos de Auditoría (PA-01 a PA-08)</h2>

  <!-- PA-04 SUELDOS Y SALARIOS -->
  <h3>3.1 PA-04: Auditoría a la Masa Salarial y Remuneraciones (Formato 43315)</h3>
  <p>
    Por primera vez se auditaron los microdatos salariales de <strong>75,985 personas servidoras públicas únicas</strong> a lo largo de 169,885 registros trimestrales.
  </p>
  <div style="display: flex; gap: 20px;">
    <div style="flex: 1;">
      <h4>Puestos con Mayor Personal Registrado</h4>
      <div class="scroll-table">
        <table>
          <thead>
            <tr>
              <th>Denominación del Puesto</th>
              <th class="text-right">Registros Trimestrales</th>
            </tr>
          </thead>
          <tbody>
            {rows_sueldos_puestos}
          </tbody>
        </table>
      </div>
    </div>
    <div style="flex: 1.2;">
      <h4>Muestra de Outliers Salariales (Altas Remuneraciones Mensuales ≥ $150,000 MXN)</h4>
      <div class="scroll-table">
        <table>
          <thead>
            <tr>
              <th>Servidor(a) Público(a)</th>
              <th>Puesto / Cargo</th>
              <th>Área de Adscripción</th>
              <th class="text-right">Bruto Mensual</th>
              <th class="text-right">Neto Mensual</th>
            </tr>
          </thead>
          <tbody>
            {rows_outliers}
          </tbody>
        </table>
      </div>
    </div>
  </div>

  <!-- PA-02 HONORARIOS -->
  <h3>3.2 PA-02: Auditoría de Contrataciones por Honorarios Asimilados (Formato 43343)</h3>
  <p>
    Se auditó el universo de <strong>74,079 contratos de honorarios</strong> celebrados con <strong>55,156 personas físicas</strong>, acumulando un importe bruto total de <strong>{mx(data['honorarios_pa02']['monto_total_bruto'])}</strong>.
  </p>
  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>Persona Contratada por Honorarios</th>
          <th class="text-center">Contratos Asignados</th>
          <th class="text-right">Monto Total Bruto Acumulado</th>
        </tr>
      </thead>
      <tbody>
        {rows_honorarios}
      </tbody>
    </table>
  </div>

  <!-- PA-07 VIÁTICOS -->
  <h3>3.3 PA-07: Auditoría Masiva de Viáticos y Comisiones Oficiales (Formato 43316)</h3>
  <p>
    En contraste con los registros simbólicos de ejercicios anteriores, en 2025 se publicaron <strong>99,842 comisiones oficiales</strong> asignadas a <strong>33,562 personas comisionadas únicas</strong>, reflejando el despliegue logístico distrital y de fiscalización en campo.
  </p>
  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>Servidor(a) Comisionado(a)</th>
          <th class="text-right">Comisiones Oficiales Registradas en 2025</th>
        </tr>
      </thead>
      <tbody>
        {rows_viaticos}
      </tbody>
    </table>
  </div>

  <!-- CRUCE NÓMINA VS HONORARIOS -->
  <h3>3.4 Cruce Forense de Integridad: Coincidencias Nómina ↔ Honorarios</h3>
  <div class="alert-box warning">
    <strong>HALLAZGO ANALÍTICO RELEVANTE:</strong> Al cruzar los nombres del personal de base/confianza (Formato 43315) con las personas contratadas por honorarios asimilados (Formato 43343), se detectaron <strong>32,369 coincidencias onomásticas exactas</strong>. Esto evidencia un esquema masivo de transición y doble vía contractual donde miles de capacitadores y técnicos electorales operan intermitentemente bajo ambas modalidades a lo largo del ejercicio fiscal.
  </div>

  <!-- PA-01 CONTRATACIONES -->
  <h3>3.5 PA-01: Auditoría de Contrataciones Públicas (Formato 59875)</h3>
  <p>
    En 2025 se celebraron <strong>12,189 contratos</strong> por un monto total de <strong>{mx(data['contratos_pa01']['monto_gran_total'])}</strong>.
  </p>
  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>Modalidad de Procedimiento</th>
          <th class="text-center">Contratos Celebrados</th>
          <th class="text-right">Monto Total Contratado</th>
          <th class="text-center">% del Monto Total</th>
        </tr>
      </thead>
      <tbody>
        {rows_contratos_proc}
      </tbody>
    </table>
  </div>

  <h4>Proveedores con Mayor Monto Contratado en 2025 (Top 12)</h4>
  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>RFC</th>
          <th>Razón Social / Proveedor</th>
          <th class="text-center">Tipo</th>
          <th class="text-center">Año Reg.</th>
          <th class="text-right">Monto Total</th>
          <th class="text-center">Contratos</th>
        </tr>
      </thead>
      <tbody>
        {rows_top_monto}
      </tbody>
    </table>
  </div>

  <!-- PA-08 PRESUPUESTO -->
  <h3>3.6 PA-08: Presupuesto por Partidas (Formato 43338)</h3>
  <p>
    El INE contó con un Presupuesto de Egresos Aprobado anual de <strong>$28,264,307,082.00</strong> (Formato 43359), modificado a <strong>$28,266,307,082.00</strong>. El gasto reportado efectivamente pagado ascendió a <strong>$27,820,476,140.45</strong> (98.42% de ejercicio presupuestal).
  </p>
  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>Capítulo</th>
          <th>Denominación del Capítulo</th>
          <th class="text-center">Partidas</th>
          <th class="text-right">Aprobado</th>
          <th class="text-right">Modificado</th>
          <th class="text-right">Devengado</th>
          <th class="text-right">Ejercido</th>
          <th class="text-right">Pagado</th>
          <th class="text-center">% Pag/Apr</th>
        </tr>
      </thead>
      <tbody>
        {rows_presupuesto}
      </tbody>
    </table>
  </div>

  <!-- CRUCE QUINQUENAL -->
  <h3>3.7 PA-07: Consolidación y Concentración del Quinquenio Histórico Completo 2021-2025</h3>
  <p>
    Se consolidó la serie histórica de cinco ejercicios fiscales completos para identificar a los mayores contratistas de la institución en el último lustro:
  </p>
  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>RFC</th>
          <th>Razón Social / Contratista</th>
          <th class="text-right">2021</th>
          <th class="text-right">2022</th>
          <th class="text-right">2023</th>
          <th class="text-right">2024</th>
          <th class="text-right">2025</th>
          <th class="text-right">Total Quinquenio</th>
        </tr>
      </thead>
      <tbody>
        {rows_quinquenio}
      </tbody>
    </table>
  </div>

  <!-- 4. MATRIZ DE HALLAZGOS Y OBSERVACIONES -->
  <h2>4. Matriz de Hallazgos y Observaciones de Auditoría</h2>

  <div class="finding-card ha">
    <div class="finding-title">
      <span>INE-2025-PA04-001: 536 Outliers Salariales con Remuneración Bruta Superior a $150,000 MXN</span>
      <span class="badge badge-danger">H-A (ALTO RIESGO)</span>
    </div>
    <p>
      <strong>Condición:</strong> La apertura de microdatos en el formato 43315 evidenció 536 registros de servidores públicos con remuneraciones mensuales brutas entre $150,000 y $262,000 MXN mensuales en puestos directivos, de coordinación y consejerías electorales.<br>
      <strong>Criterio:</strong> Artículo 127 de la Constitución Política de los Estados Unidos Mexicanos y Ley Federal de Remuneraciones de los Servidores Públicos.<br>
      <strong>Recomendación:</strong> Conciliar el tabulador formal frente a las resoluciones judiciales de amparo interpuestas por funcionarios del INE respecto al tope salarial presidencial.
    </p>
  </div>

  <div class="finding-card ha">
    <div class="finding-title">
      <span>INE-2025-PA02-002: Dualidad Contractual y Cruce de 32,369 Personas entre Nómina y Honorarios</span>
      <span class="badge badge-danger">H-A (ALTO RIESGO)</span>
    </div>
    <p>
      <strong>Condición:</strong> Se detectaron 32,369 coincidencias de nombres entre la nómina permanente/eventual y el padrón de honorarios asimilados en el mismo ejercicio fiscal. Esto requiere verificar que no existan traslapes temporales de periodos de contratación ni doble percepción indebida.<br>
      <strong>Criterio:</strong> Ley General de Responsabilidades Administrativas y Reglamento Interior del INE.<br>
      <strong>Recomendación:</strong> Implementar un candado informático de interoperabilidad en el Sistema Integral de Recursos Humanos (SIRH) que bloquee el alta por honorarios a cualquier RFC con plaza activa.
    </p>
  </div>

  <div class="finding-card hb">
    <div class="finding-title">
      <span>INE-2025-PA01-003: Concentración en Seguridad Privada y Servicios de Soporte</span>
      <span class="badge badge-warning">H-B (MEDIO RIESGO)</span>
    </div>
    <p>
      <strong>Condición:</strong> En 2025 empresas de seguridad privada y seguros médicos institucionales concentraron las mayores bolsas presupuestales, encabezadas por <em>Lumack Seguridad Privada ($160.9 M)</em> y <em>Axxa Seguros ($141.5 M)</em>.<br>
      <strong>Criterio:</strong> Principios de racionalidad, austeridad republicana y concurrencia del Artículo 134 Constitucional.<br>
      <strong>Recomendación:</strong> Evaluar esquemas de licitación consolidada multianual para reducir costos en primas de aseguramiento y resguardo perimetral.
    </p>
  </div>

  <div class="finding-card hc">
    <div class="finding-title">
      <span>INE-2025-PA07-004: Falla de Captura en Importes de Viáticos Comprobados</span>
      <span class="badge badge-info">H-C (BAJO RIESGO / CONTROL)</span>
    </div>
    <p>
      <strong>Condición:</strong> Si bien el formato 43316 capturó un récord de 99,842 filas de comisiones y servidores públicos comisionados, diversas columnas de importes monetarios devengados se registraron en ceros o con notas genéricas.<br>
      <strong>Criterio:</strong> Lineamientos Técnicos Generales del INAI (Fracción IX del Artículo 70).<br>
      <strong>Recomendación:</strong> Corregir el script de extracción que exporta los finiquitos y reembolsos de viáticos desde el sistema administrativo del INE hacia el SIPOT.
    </p>
  </div>

  <!-- PIE INSTITUCIONAL OBLIGATORIO AGIL SOLUTIONS -->
  <div class="footer-block">
    <div class="footer-motto">"Lo que no se mide, no se puede Gestionar"</div>
    <div class="footer-sign">
      <strong>A T E N T A M E N T E</strong><br>
      <strong>AGIL SOLUTIONS</strong><br>
      <em>Dirección de Auditoría Forense y Tecnologías de la Información</em>
    </div>
  </div>

</body>
</html>
"""

# Guardar informe HTML
html_path = os.path.join(base_dir, "informe_auditoria_ine_2025.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Informe HTML generado exitosamente en: {html_path}")
