#!/usr/bin/env python3
"""
Generador del Informe Integral de Auditoría PNT - INE Ejercicio Fiscal 2022
Auditoría Documental, Presupuestal, Contrataciones, Padrón de Proveedores y Revocación de Mandato.
"""

import json
import os
import base64

def get_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")

# Cargar datos calculados
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_path = os.path.join(base_dir, "analisis/auditoria_datos_calculados_2022.json")
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
for fmt in sorted(data['formatos_presentes'], key=lambda x: x['filas'], reverse=True):
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

# 3. Top Proveedores por Monto
rows_top_monto = ""
for p in data['contratos']['top_monto'][:15]:
    tipo_prov = "Persona Moral" if p['is_moral'] else "Persona Física"
    en_pad = '<span class="badge badge-success">SÍ</span>' if p['en_padron'] else '<span class="badge badge-danger">NO</span>'
    rows_top_monto += f"""
    <tr>
        <td><code>{p['rfc']}</code></td>
        <td><strong>{p['razon']}</strong></td>
        <td class="text-center">{tipo_prov}</td>
        <td class="text-center">{p['year'] or '—'}</td>
        <td class="text-center">{en_pad}</td>
        <td class="text-right"><strong>{mx(p['monto_total'])}</strong></td>
        <td class="text-right">{mx(p['monto_adjudicado'])}</td>
        <td class="text-right">{mx(p['monto_licitado'])}</td>
        <td class="text-center">{n(p['contratos_totales'])}</td>
    </tr>
    """

# 4. Top Proveedores por Frecuencia / Recurrencia
rows_top_frec = ""
for p in data['contratos']['top_frecuencia'][:15]:
    en_pad = '<span class="badge badge-success">SÍ</span>' if p['en_padron'] else '<span class="badge badge-danger">NO</span>'
    rows_top_frec += f"""
    <tr>
        <td><code>{p['rfc']}</code></td>
        <td><strong>{p['razon']}</strong></td>
        <td class="text-center"><strong>{n(p['contratos_totales'])}</strong></td>
        <td class="text-center">{n(p['contratos_adjudicados'])}</td>
        <td class="text-center">{n(p['contratos_licitados'])}</td>
        <td class="text-center">{en_pad}</td>
        <td class="text-right"><strong>{mx(p['monto_total'])}</strong></td>
    </tr>
    """

# 5. Proveedores Recientes Materiales (Riesgo Creación Reciente)
rows_recientes = ""
for p in data['contratos']['recientes_materiales'][:15]:
    rows_recientes += f"""
    <tr>
        <td><code>{p['rfc']}</code></td>
        <td><strong>{p['razon']}</strong></td>
        <td class="text-center"><span class="badge badge-warning">{p['year']}</span></td>
        <td class="text-right"><strong>{mx(p['monto_total'])}</strong></td>
        <td class="text-center">{n(p['contratos_totales'])}</td>
        <td class="text-right">{mx(p['monto_adjudicado'])}</td>
        <td class="text-right">{mx(p['monto_licitado'])}</td>
    </tr>
    """

# 6. Presupuesto por Capítulos
rows_presupuesto = ""
for c in data['partidas']['capitulos']:
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

# 7. Financiamiento a Partidos Políticos
rows_partidos = ""
for pt in data['partidos']['detalle']:
    rows_partidos += f"""
    <tr>
        <td><strong>{pt['partido']}</strong></td>
        <td class="text-right"><strong>{mx(pt['mensual_acumulado'])}</strong></td>
        <td class="text-right">{mx(pt['anual_referencia'])}</td>
        <td class="text-center">{pt['registros']}</td>
        <td><small>{', '.join(pt['tipos'])[:60]}...</small></td>
    </tr>
    """

# 8. Cruce Interanual 2021-2022
rows_interanuales = ""
for r in data['cruces'].get('recurrentes_interanuales', []):
    rows_interanuales += f"""
    <tr>
        <td><code>{r['rfc']}</code></td>
        <td><strong>{r['razon']}</strong></td>
        <td class="text-right">{mx(r['monto_2021'])}</td>
        <td class="text-right">{mx(r['monto_2022'])}</td>
        <td class="text-right"><strong>{mx(r['monto_acumulado_2_anios'])}</strong></td>
    </tr>
    """

# 9. Áreas Compradoras Top
rows_areas = ""
for ar in data['contratos']['top_areas_compradoras']:
    rows_areas += f"""
    <tr>
        <td><strong>{ar['area']}</strong></td>
        <td class="text-right"><strong>{n(ar['contratos'])}</strong></td>
    </tr>
    """

html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Informe Integral de Auditoría PNT — INE Ejercicio 2022</title>
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
        <div class="header-sub"><strong>INSTITUTO NACIONAL ELECTORAL (INE) — EJERCICIO FISCAL 2022</strong></div>
        <div class="header-sub">Órgano Garante: FED - OIC-INE | Nivel: Federal | Base de Datos: PNT SIPOT</div>
      </td>
    </tr>
  </table>

  <!-- 1. RESUMEN EJECUTIVO Y KPIS -->
  <h2>1. Resumen Ejecutivo y Métricas Clave</h2>
  <p>
    El presente informe documenta la auditoría exhaustiva e independiente a la totalidad de la información pública registrada en la <strong>Plataforma Nacional de Transparencia (PNT)</strong> correspondiente al <strong>Instituto Nacional Electoral (INE)</strong> para el ejercicio fiscal <strong>2022</strong>, año marcado presupuestalmente por la ejecución del primer proceso de <strong>Revocación de Mandato</strong> de la Presidencia de la República.
  </p>
  <p>
    La auditoría evaluó los <strong>90,696 registros públicos en 29 formatos</strong>, confrontándolos con las obligaciones del Artículo 70 de la LGTAIP y ejecutando los procedimientos de auditoría forense (PA-01 a PA-08), incluyendo la verificación del <strong>Padrón de Proveedores (Formato 43369)</strong>, contrataciones públicas, viáticos, financiamiento partidista y resultados de participación ciudadana.
  </p>

  <div class="kpi-grid">
    <div class="kpi-card">
      <div class="kpi-value">{n(data['total_registros_descargados'])}</div>
      <div class="kpi-label">Registros Auditados (100%)</div>
    </div>
    <div class="kpi-card alert">
      <div class="kpi-value">{data['contratos']['pct_num_adjudicacion_directa']:.1f}%</div>
      <div class="kpi-label">Adjudicaciones Directas (N)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-value">{mx(data['contratos']['monto_gran_total'])}</div>
      <div class="kpi-label">Monto Contratos Totales (PA-01)</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-value">{mx(data['partidas']['total_pagado'])}</div>
      <div class="kpi-label">Gasto Total Pagado 2022</div>
    </div>
  </div>

  <div class="kpi-grid">
    <div class="kpi-card alert">
      <div class="kpi-value">{data['padron_proveedores']['pct_fuera_padron']:.1f}%</div>
      <div class="kpi-label">Proveedores Fuera de Padrón</div>
    </div>
    <div class="kpi-card alert">
      <div class="kpi-value">{mx(data['padron_proveedores']['monto_contratados_fuera_padron'])}</div>
      <div class="kpi-label">Monto Contratado Fuera Padrón</div>
    </div>
    <div class="kpi-card alert">
      <div class="kpi-value">35 / 48</div>
      <div class="kpi-label">Obligaciones Art 70 Faltantes</div>
    </div>
    <div class="kpi-card">
      <div class="kpi-value">17.77%</div>
      <div class="kpi-label">Participación Revocación Mandato</div>
    </div>
  </div>

  <!-- 2. PARTE I: INVESTIGACIÓN DOCUMENTAL RIGUROSA (PRESENTE VS FALTANTE) -->
  <h2>2. Parte I: Investigación de Documentación Presente vs. Faltante (LGTAIP)</h2>

  <h3>2.1 Documentación Pública Presente en PNT (29 Formatos Descargados)</h3>
  <p>
    El repositorio contiene <strong>29 formatos oficiales</strong> debidamente homologados por el INE en la PNT, con un universo de <strong>90,696 registros</strong> analizados.
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

  <h3>2.2 Observación de Información Faltante y Brechas de Transparencia (Art. 70 LGTAIP)</h3>
  <div class="alert-box">
    <strong>ALERTA DE FISCALIZACIÓN Y RECHAZO TÉCNICO:</strong> A pesar de la incorporación de los formatos <code>43369 (Padrón de proveedores)</code> y <code>43316 (Viáticos)</code> en 2022, el INE <strong>mantuvo la omisión de 35 fracciones obligatorias</strong> del Artículo 70 de la LGTAIP. Continúan ausentes los microdatos de sueldos (Fracc. VIII), personal por honorarios (Fracc. XI), declaraciones patrimoniales (Fracc. XII), publicidad oficial (Fracc. XXIII) y resultados de auditorías del OIC (Fracc. XXIV). Además, el INE incorporó los formatos <code>36780</code>, <code>37516</code> y <code>37533</code> únicamente con leyendas justificativas ("no se generó información"), sin datos tabulares.
  </div>

  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>Fracción Art. 70</th>
          <th>Materia Obligatoria Omitida</th>
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

  <!-- PA-01 CONTRATOS Y PADRÓN -->
  <h3>3.1 PA-01: Auditoría de Contrataciones y Cruce con Padrón de Proveedores</h3>
  <p>
    En 2022 el INE celebró un total de <strong>86,957 contratos</strong> por un monto acumulado de <strong>{mx(data['contratos']['monto_gran_total'])}</strong>.
  </p>
  <ul class="bullets">
    <li><strong>Hiper-atomización del gasto por Adjudicación Directa:</strong> El <strong>99.61%</strong> de las contrataciones ({n(data['contratos']['total_filas_adjudicaciones'])} eventos) se realizaron por adjudicación directa, sumando <strong>{mx(data['contratos']['monto_total_adjudicaciones'])}</strong> (46.40% del monto total).</li>
    <li><strong>Licitaciones Públicas e Invitaciones:</strong> Representaron sólo el 0.39% de los eventos (342 procedimientos), concentrando <strong>{mx(data['contratos']['monto_total_licitaciones'])}</strong> (53.60% del monto total).</li>
    <li><strong>CRUCE CRÍTICO CON EL PADRÓN DE PROVEEDORES (43369):</strong> De 10,200 proveedores únicos contratados por el INE en 2022, <strong>sólo 51 proveedores (0.50%) se encuentran inscritos en el Padrón Oficial publicado</strong>. El <strong>99.50% de los proveedores (10,149 empresas y personas físicas)</strong> recibieron contratos encontrándose <strong>fuera del padrón oficial</strong>, concentrando un monto de <strong>{mx(data['padron_proveedores']['monto_contratados_fuera_padron'])}</strong> (95.96% del gasto total contratado).</li>
  </ul>

  <h4>A. Proveedores con Mayor Monto Contratado (Top 15)</h4>
  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>RFC</th>
          <th>Razón Social / Proveedor</th>
          <th class="text-center">Tipo</th>
          <th class="text-center">Año Reg.</th>
          <th class="text-center">En Padrón</th>
          <th class="text-right">Monto Total</th>
          <th class="text-right">Monto Adjudicado</th>
          <th class="text-right">Monto Licitado</th>
          <th class="text-center">Contratos</th>
        </tr>
      </thead>
      <tbody>
        {rows_top_monto}
      </tbody>
    </table>
  </div>

  <h4>B. Concentración y Recurrencia de Proveedores (Top 15 por Frecuencia)</h4>
  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>RFC</th>
          <th>Razón Social / Proveedor</th>
          <th class="text-center">Total Contratos</th>
          <th class="text-center">Directas</th>
          <th class="text-center">Licitadas</th>
          <th class="text-center">En Padrón</th>
          <th class="text-right">Monto Total</th>
        </tr>
      </thead>
      <tbody>
        {rows_top_frec}
      </tbody>
    </table>
  </div>

  <h4>C. Empresas de Creación Reciente (Constituidas ≥ 2019 con Montos ≥ $1,000,000)</h4>
  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>RFC</th>
          <th>Razón Social</th>
          <th class="text-center">Año RFC</th>
          <th class="text-right">Monto Total</th>
          <th class="text-center">Contratos</th>
          <th class="text-right">Adjudicación Directa</th>
          <th class="text-right">Licitación / Inv.</th>
        </tr>
      </thead>
      <tbody>
        {rows_recientes}
      </tbody>
    </table>
  </div>

  <h4>D. Áreas Compradoras con Mayor Volumen de Adjudicación</h4>
  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>Área Compradora / Junta Distrital / Unidad Técnica</th>
          <th class="text-right">Adjudicaciones Directas Emitidas</th>
        </tr>
      </thead>
      <tbody>
        {rows_areas}
      </tbody>
    </table>
  </div>

  <!-- PA-08 PRESUPUESTO -->
  <h3>3.2 PA-08: Auditoría Financiera y Presupuesto por Partidas (Formato 43338)</h3>
  <p>
    El INE contó con un Presupuesto de Egresos Aprobado anual de <strong>$19,736,593,972.00</strong> (Formato 43359), modificado a <strong>$19,788,143,472.00</strong>. El formato 43338 reporta un ejercicio efectivamente pagado de <strong>$19,167,419,258.98</strong> (97.12% de ejercicio global).
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
  <div class="alert-box info">
    <strong>DISCREPANCIA CONTABLE PERSISTENTE:</strong> Al igual que en 2021, la columna <em>Gasto Ejercido</em> reporta únicamente $269.8 millones frente a $19,167.4 millones pagados. Esto confirma que el mecanismo de exportación contable del INE a la PNT tiene un defecto estructural que omite la fase intermedia del gasto ejercido.
  </div>

  <!-- PA-05 FINANCIAMIENTO PARTIDOS -->
  <h3>3.3 PA-05 Especial: Financiamiento Público a Partidos Políticos (Formato 43496)</h3>
  <p>
    En 2022 se dispersaron más de <strong>$5,787 millones de pesos</strong> en prerrogativas públicas ordinarias y específicas. Se verificó que Morena, el PAN y el PRI concentraron más del 68% de la totalidad de las transferencias federales.
  </p>
  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>Partido Político / Organización</th>
          <th class="text-right">Monto Mensual Acumulado</th>
          <th class="text-right">Financiamiento Anual Reportado</th>
          <th class="text-center">Registros</th>
          <th>Modalidad de Financiamiento</th>
        </tr>
      </thead>
      <tbody>
        {rows_partidos}
      </tbody>
    </table>
  </div>

  <!-- PA-07 CRUCE INTERANUAL -->
  <h3>3.4 PA-07: Cruce Interanual 2021 ↔ 2022 (Proveedores Recurrentes de Alto Monto)</h3>
  <p>
    Se cruzaron las bases de contratación de ambos ejercicios fiscales, detectando proveedores estratégicos con asignaciones multimillonarias consecutivas:
  </p>
  <div class="scroll-table">
    <table>
      <thead>
        <tr>
          <th>RFC</th>
          <th>Razón Social / Contratista</th>
          <th class="text-right">Monto 2021</th>
          <th class="text-right">Monto 2022</th>
          <th class="text-right">Monto Acumulado (2 Años)</th>
        </tr>
      </thead>
      <tbody>
        {rows_interanuales}
      </tbody>
    </table>
  </div>

  <!-- AUDITORÍA DE REVOCACIÓN DE MANDATO -->
  <h3>3.5 Cómputos y Participación Ciudadana: Revocación de Mandato 2022 (Formato 43506)</h3>
  <p>
    El formato 43506 recopila las actas y resultados de cómputo en los <strong>300 Distritos Electorales Federales</strong> durante la jornada del 10 de abril de 2022.
  </p>
  <ul class="bullets">
    <li><strong>Cobertura y digitalización:</strong> Se capturó el 100% de las 600 filas correspondientes a los acuerdos y actas distritales de cómputo con hipervínculos operativos al repositorio documental institucional.</li>
    <li><strong>Participación ciudadana distrital:</strong> La participación media distrital se situó en <strong>17.77%</strong>, quedando por debajo del umbral del 40% requerido constitucionalmente para tener efectos vinculantes.</li>
  </ul>

  <!-- 4. MATRIZ DE HALLAZGOS Y OBSERVACIONES -->
  <h2>4. Matriz de Hallazgos y Observaciones de Auditoría</h2>

  <div class="finding-card ha">
    <div class="finding-title">
      <span>INE-2022-PA01-001: Desconexión Masiva entre Contratación Pública y Padrón de Proveedores</span>
      <span class="badge badge-danger">H-A (ALTO RIESGO)</span>
    </div>
    <p>
      <strong>Condición:</strong> De los 10,200 proveedores y contratistas que recibieron pagos del INE en 2022, el <strong>99.50% (10,149 proveedores) operaron fuera del padrón oficial</strong> de proveedores publicado en PNT (Formato 43369). Un total de <strong>$3,971,082,709.01 MXN</strong> (el 95.96% del monto total contratado) se entregó a personas físicas y morales no inscritas o no actualizadas en el padrón.<br>
      <strong>Criterio:</strong> Artículo 70 Fracción XXXII de la LGTAIP y Reglamento de Adquisiciones del INE.<br>
      <strong>Causa:</strong> Falta de integración entre los padrones locales administrados por las 300 Juntas Distritales y la Dirección Ejecutiva de Administración en oficinas centrales.<br>
      <strong>Recomendación:</strong> Obligar a la inscripción y validación fiscal previa en el Padrón Único CompraINE antes de liberar órdenes de compra o pedidos directos en cualquier junta local o distrital.
    </p>
  </div>

  <div class="finding-card ha">
    <div class="finding-title">
      <span>INE-2022-PA08-002: Persistencia del Vacío Documental en 35 Fracciones del Artículo 70 LGTAIP</span>
      <span class="badge badge-danger">H-A (ALTO RIESGO)</span>
    </div>
    <p>
      <strong>Condición:</strong> A pesar del incremento a 29 formatos en 2022, persiste la ausencia total de datos de nómina masiva, contratos por honorarios asimilados, declaraciones de conflicto de interés de funcionarios y auditorías practicadas por el OIC. Formatos adicionales como 36780, 37516 y 37533 solo contienen notas aclaratorias afirmando que no se generó información.<br>
      <strong>Criterio:</strong> Lineamientos Técnicos Generales del INAI y Artículos 70 y 74 de la LGTAIP.<br>
      <strong>Recomendación:</strong> Emitir requerimiento formal de cumplimiento al Comité de Transparencia del INE para subsanar la carga de microdatos del ejercicio 2022 en el SIPOT.
    </p>
  </div>

  <div class="finding-card hb">
    <div class="finding-title">
      <span>INE-2022-PA01-003: Concentración Recurrente y Atomización en 86,615 Adjudicaciones Directas</span>
      <span class="badge badge-warning">H-B (MEDIO RIESGO)</span>
    </div>
    <p>
      <strong>Condición:</strong> El 99.61% de los procedimientos de compra se ejecutaron por la vía de excepción (adjudicación directa), sumando $1,920.6 millones. Se observan volúmenes atípicos de adjudicaciones a grandes consorcios (Nueva WalMart con 967 compras; Office Depot con 879; Tiendas Soriana con 629; Ofix con 559; Efectivale con 545 compras directas).<br>
      <strong>Criterio:</strong> Artículo 134 de la Constitución Política de los Estados Unidos Mexicanos y principios de eficiencia y concurrencia.<br>
      <strong>Recomendación:</strong> Establecer convenios marco y compras consolidadas centralizadas para abatir sobreprecios y dispersión operativa.
    </p>
  </div>

  <div class="finding-card hb">
    <div class="finding-title">
      <span>INE-2022-PA01-004: Contratación de Empresas Constituidas en 2019-2021 con Asignaciones Millonarias</span>
      <span class="badge badge-warning">H-B (MEDIO RIESGO)</span>
    </div>
    <p>
      <strong>Condición:</strong> Empresas con escasa antigüedad operativa continuaron ganando contratos significativos. Se identificó a <strong>Soluciones Tecnológicas Especializadas (STE190924S47)</strong>, constituida en septiembre de 2019, adjudicándose contratos por más de $15.8 millones de pesos.<br>
      <strong>Criterio:</strong> Comprobación de capacidad técnica, solvencia económica y experiencia mínima comprobable.<br>
      <strong>Recomendación:</strong> Practicar auditoría técnica a las actas de entrega-recepción y verificar las garantías de cumplimiento.
    </p>
  </div>

  <div class="finding-card hc">
    <div class="finding-title">
      <span>INE-2022-PA07-005: Formato de Viáticos (43316) con Registro Mínimo Simbólico (5 Filas)</span>
      <span class="badge badge-info">H-C (BAJO RIESGO / CONTROL)</span>
    </div>
    <p>
      <strong>Condición:</strong> Durante un año de despliegue territorial nacional por la Revocación de Mandato en 300 distritos, el formato de viáticos y gastos de representación (43316) únicamente reportó 5 registros, lo que resulta inverosímil frente al gasto de más de $3,546 millones pagados en Servicios Generales (Capítulo 3000).<br>
      <strong>Criterio:</strong> Artículo 70 Fracción IX de la LGTAIP.<br>
      <strong>Recomendación:</strong> Regularizar y cargar la totalidad de comisiones y viáticos devengados por el personal de campo y funcionarios de oficinas centrales.
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
html_path = os.path.join(base_dir, "informe_auditoria_ine_2022.html")
with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

print(f"Informe HTML generado exitosamente en: {html_path}")
