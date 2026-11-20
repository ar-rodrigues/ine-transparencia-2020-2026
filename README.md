# Observatorio del Instituto Nacional Electoral (INE 2020–2026)
### Inteligencia de Datos · Auditoría de Cuentas Públicas
**Desarrollado por [AGIL Solutions](https://agilsolutions.com)**

[![Licencia](https://img.shields.io/badge/licencia-MIT-gold.svg)](LICENSE)
[![Datos: PNT](https://img.shields.io/badge/fuente-PNT%20%C2%B7%20INE-crimson.svg)](https://consultapublicamx.inai.org.mx/vtransparencia/)
[![Formato](https://img.shields.io/badge/datos-Apache%20Parquet%20%7C%20DuckDB-blue.svg)](#arquitectura-de-datos)

Investigación visual, pipeline de ingeniería de datos y repositorio auditable sobre más de **$27,820 millones de pesos ejercidos**, **125,433 contratos públicos**, el tabulador de **2,536 cargos salariales** y los registros de viáticos del Instituto Nacional Electoral (INE) para los ejercicios fiscales 2020 a 2026, obtenidos directamente de la **Plataforma Nacional de Transparencia (PNT)**.

---

## 📌 Hallazgos Principales de la Auditoría

1. **Destino del Presupuesto (2025):** De los **$27,820 MDP** pagados en 2025 (un sobreejercicio de +$820 MDP frente al aprobado), el **79.3%** se concentró exclusivamente en **Servicios Personales (47.1%)** y **Transferencias a Partidos Políticos (32.2%)**.
2. **Publicidad Oficial:** La **Televisión absorbió el 56.1%** del gasto con solo 87 pautas, a un costo promedio de **$952,815 pesos por pauta** (20 veces más caro que una pauta digital de $46.7k).
3. **Bolsa a Partidos Políticos:** En año electoral presidencial (2024), la bolsa pública saltó **+65.5%** a **$10,117 MDP**. Tres fuerzas políticas concentraron el 67.7% del dinero: **MORENA (30.9%)**, **PAN (18.6%)** y **PRI (18.2%)**.
4. **Foco Rojo en Contrataciones:** El **98.7% de los contratos (123,827)** se entregaron por **Adjudicación Directa**, representando el **43.7% del dinero erogado ($2,734 MDP)**, superando el umbral internacional recomendado (~30%). Destacan personas físicas con hasta **46 contratos directos recurrentes**.
5. **Concentración Geográfica Atípica:** Fuera de Oficinas Centrales (28.9%), **Zacatecas concentró el 18.4% del monto contratado nacional ($1,150 MDP)**, superando la suma de CDMX, Jalisco, Nuevo León y Edomex juntos, impulsado por obra pública concentrada.
6. **Estructura Laboral Paralela:** En 2025, el **73.8% de la fuerza laboral (55,165 personas)** operó bajo **honorarios asimilados** sin plaza fija ni estabilidad laboral, frente a 19,557 trabajadores de estructura.
7. **Concentración Salarial:** El **7.8% de las plazas** (mandos medios y altos) absorbe el **33.7% de la masa salarial mensual**. La presidencia y consejerías perciben **$262,634 brutos mensuales** ($178.3k netos).
8. **Viáticos Atípicos:** De 21,764 comisiones (promedio nacional de $5,240), se identificaron comisiones nacionales atípicas de hasta **$120,001 pesos (22.9x el promedio)** en Jalisco y 10 comisiones superiores a $50k concentradas en la JDE 09 de Linares, NL.

---

## 🏛️ Arquitectura de Datos (*Medallion Architecture*)

El lago de datos está estructurado en tres capas reproducibles almacenadas en **Backblaze B2**:

```text
INE/
├── datos_b2/
│   ├── 01_datos_crudos/      # Capa Bronce (~1.5 GB): JSONs y CSVs sin alterar de la PNT
│   ├── 02_datos_limpios/     # Capa Plata  (~122 MB): Tablas Parquet normalizadas y deduplicadas
│   └── 03_datos_agregados/   # Capa Oro    (~160 KB): 21 tablas analíticas y KPIs (Parquet + JSON)
│
├── scripts/                  # Pipelines automatizados de limpieza y agregación
│   ├── etl/                  # Scripts de transformación Python + DuckDB
│   └── utilidades/           # Descargador B2 y exportador Parquet -> CSV/JSON
│
└── tablero/                  # Especial interactivo Scrollytelling + Parallax (HTML5 / ECharts)
```

---

## 🚀 Cómo Reproducir el Proyecto Localmente

### 1. Clonar el repositorio
```bash
git clone https://github.com/ar-rodrigues/ine-transparencia-2020-2026.git
cd ine-transparencia-2020-2026
```

### 2. Levantar el Tablero Interactivo
El tablero no requiere NodeJS ni compilaciones pesadas. Utiliza **DuckDB-WASM** y **Apache ECharts** cargados desde el navegador consumiendo la **Capa Oro** incluida en el repositorio:
```bash
python3 -m http.server 8765
```
Abre en tu navegador: `http://localhost:8765/tablero/`

---

## 📦 Descarga de Datos desde Backblaze B2

El repositorio incluye un script CLI oficial para descargar cualquiera de las capas de datos:

```bash
# Instalar dependencia
pip install boto3

# Descargar Capa Oro (160 KB - Parquets agregados)
python3 scripts/utilidades/descargar_datos_b2.py --capa oro

# Descargar Capa Plata (122 MB - 125k contratos, nómina, viáticos en Parquet)
python3 scripts/utilidades/descargar_datos_b2.py --capa plata

# Descargar Capa Bronce (1.5 GB - JSONs crudos de la PNT)
python3 scripts/utilidades/descargar_datos_b2.py --capa bronce
```

### Consultas rápidas con DuckDB CLI (sin servidor de base de datos)
```bash
# Consultar el Top 10 de proveedores con adjudicación directa
duckdb -c "SELECT ranking, proveedor_nombre, total_contratos, monto_total FROM 'datos_b2/03_datos_agregados/contrataciones/top_proveedores_adjudicacion_directa.parquet' LIMIT 10;"

# Exportar cualquier tabla agregada a CSV
python3 scripts/utilidades/exportar_agregados.py --formato csv
```

---

## 🧩 Incrustar Gráficas en Ghost o Sitios Web

Cada una de las 9 gráficas interactivas se puede incrustar de forma individual y responsiva en cualquier post o página web usando un `<iframe>` limpio:

```html
<iframe 
  src="https://tu-dominio.com/tablero/?embed=chart&step=3" 
  width="100%" 
  height="560" 
  style="border:none;border-radius:14px;background:#080808;overflow:hidden;" 
  scrolling="no" 
  loading="lazy">
</iframe>
```
*Parámetro `step` (0 al 8):*
- `0`: Destino del Presupuesto (Comparativa 2020 vs 2025)
- `1`: Publicidad Oficial y Ticket Promedio
- `2`: Reparto a Partidos Políticos
- `3`: Adjudicaciones Directas vs. Licitaciones (Foco Rojo)
- `4`: ¿En qué y a quién se adjudica directamente?
- `5`: Mapa Geográfico de Contrataciones (México)
- `6`: Estructura Laboral: Nómina vs. Honorarios
- `7`: Pirámide Salarial y Mandos Altos
- `8`: Mapa Nacional y Anomalías de Viáticos

---

## ⚖️ Licencia y Atribución

Este proyecto está bajo licencia MIT. Los datos originales son de dominio público conforme a la Ley General de Transparencia y Acceso a la Información Pública (LGTAIP) y provienen de la **Plataforma Nacional de Transparencia (PNT)**.

Cualquier uso o cita debe atribuirse a: **AGIL Solutions — Inteligencia de Datos**.
