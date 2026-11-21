/**
 * ¿A dónde va el dinero del INE? (2020–2026) — AGIL Solutions
 * Scrollytelling + Parallax + Mapas Geográficos de México + Embed Limpio por Gráfica.
 * Motor silencioso: DuckDB-WASM leyendo Parquet en vivo (fallback JSON transparente).
 */

const DATA_ROOT = window.location.pathname.includes("/tableros/ine")
  ? "./datos_b2/03_datos_agregados"
  : "../datos_b2/03_datos_agregados";
const PNT_SOURCE = "Fuente: Plataforma Nacional de Transparencia (PNT) · INE";

const DATA_TABLES = [
  { key: "capitulos", rel: "presupuesto/ejecucion_presupuestal_capitulos" },
  { key: "publicidad", rel: "resumen_ejecutivo/medios_2025" },
  { key: "partidosCiclo", rel: "financiamiento_partidos/comparativa_electoral_vs_ordinario" },
  { key: "partidosAnual", rel: "financiamiento_partidos/kpi_financiamiento_anual_partidos" },
  { key: "procedimientos", rel: "contrataciones/kpi_procedimientos_contratacion" },
  { key: "adProveedores", rel: "contrataciones/top_proveedores_adjudicacion_directa" },
  { key: "adMateria", rel: "contrataciones/adjudicacion_directa_por_materia" },
  { key: "proveedores", rel: "contrataciones/ranking_top_proveedores" },
  { key: "contratacionesEstados", rel: "contrataciones/mapa_contrataciones_por_estado" },
  { key: "nominaComp", rel: "personal_y_nomina/comparativa_nomina_vs_honorarios_2025" },
  { key: "salariosTramos", rel: "personal_y_nomina/concentracion_salarial_tramos_2025" },
  { key: "salarios", rel: "personal_y_nomina/distribucion_salarial_por_puesto_2025" },
  { key: "viaticosEstados", rel: "viaticos/mapa_viaticos_por_estado" },
  { key: "viaticosOutliers", rel: "viaticos/viaticos_atipicos_outliers" },
];

const state = {
  engine: "init",
  duckdbConn: null,
  data: {},
  mexicoGeoLoaded: false,
  stageChart: null,
  activeStep: -1,
  // Sub-toggles por capítulo
  pubMode: "participacion", // 'participacion' | 'ticket'
  partidosMode: "pct", // 'pct' | 'bolsa'
  adMode: "materia", // 'materia' | 'proveedores'
  salarioMode: "concentracion", // 'concentracion' | 'cupula'
  viaticosMode: "mapa", // 'mapa' | 'outliers'
  explorerTable: "adProveedores",
  explorerPage: 1,
  explorerPageSize: 15,
  explorerSortKey: null,
  explorerSortDir: "desc",
};

const COLORS = {
  gold: "#c9a84c",
  goldLight: "#e2c47a",
  ine: "#c81d4e",
  emerald: "#10b981",
  cyan: "#38bdf8",
  purple: "#a78bfa",
  amber: "#f59e0b",
  slate: "#64748b",
  grid: "rgba(255,255,255,0.06)",
  axis: "rgba(245,242,236,0.58)",
  tooltipBg: "rgba(16, 16, 16, 0.96)",
};

const PARTY_COLORS = {
  MORENA: "#9f1239",
  PAN: "#2563eb",
  PRI: "#16a34a",
  MC: "#f97316",
  PVEM: "#22c55e",
  PT: "#dc2626",
  PRD: "#eab308",
};

// Normalización de nombres PNT -> GeoJSON México
function normalizeStateName(name) {
  if (!name) return "";
  if (name === "Estado de México") return "México";
  return name;
}

// ==================== FORMATO ====================
const fmtMoney = (v) => {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return "—";
  const n = Number(v);
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(2)} MMDP`;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(1)} MDP`;
  return new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 }).format(n);
};

const fmtExactMXN = (v) =>
  v === null || v === undefined ? "—" : new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: 0 }).format(Number(v));

const fmtInt = (v) => (v === null || v === undefined ? "—" : new Intl.NumberFormat("es-MX").format(Math.round(Number(v))));

const toPlainRow = (row) => {
  const out = {};
  for (const [k, val] of Object.entries(row)) out[k] = typeof val === "bigint" ? Number(val) : val;
  return out;
};

const baseTooltip = {
  backgroundColor: COLORS.tooltipBg,
  borderColor: "rgba(201, 168, 76, 0.45)",
  borderWidth: 1,
  confine: true,
  extraCssText: "max-width: 82vw; white-space: normal; word-break: break-word; line-height: 1.45;",
  textStyle: { color: "#f5f2ec", fontFamily: "Inter, sans-serif", fontSize: 12 },
};

// ==================== CARGA RÁPIDA DE DATOS (JSON LOCAL) ====================
async function initDataEngine() {
  state.engine = "json";
}

async function loadTable(item) {
  if (state.data[item.key] && state.data[item.key].length > 0) return state.data[item.key];
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const resp = await fetch(`${DATA_ROOT}/${item.rel}.json`, { cache: attempt > 0 ? "reload" : "default" });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const json = await resp.json();
      state.data[item.key] = json;
      return json;
    } catch {
      if (attempt === 1) return [];
    }
  }
  return [];
}

async function loadMexicoGeo() {
  try {
    const resp = await fetch("./mexico.geojson");
    const geoJson = await resp.json();
    echarts.registerMap("mexico", geoJson);
    state.mexicoGeoLoaded = true;
  } catch (e) {
    console.warn("No se pudo cargar el GeoJSON de México:", e);
  }
}

// ==================== ESCENAS DEL SCROLLYTELLING (9 CAPÍTULOS) ====================
function setStageMeta({ kicker, title, source = PNT_SOURCE, stepIndex, controlsHtml = "" }, opts = {}) {
  if (opts.controlsEl) {
    if (opts.sourceEl) opts.sourceEl.textContent = source;
    opts.controlsEl.innerHTML = controlsHtml;
    return opts.controlsEl;
  }
  document.getElementById("stage-kicker").textContent = kicker;
  document.getElementById("stage-title").textContent = title;
  document.getElementById("stage-source").textContent = source;
  document.getElementById("stage-counter").textContent = `0${stepIndex + 1} / 09`;
  const ctrlEl = document.getElementById("stage-controls");
  ctrlEl.innerHTML = controlsHtml;
  return ctrlEl;
}

function bindStageToggle(ctrlEl, attr, stateKey, stepIndex, opts) {
  ctrlEl.querySelectorAll(`[${attr}]`).forEach((b) =>
    b.addEventListener("click", () => {
      state[stateKey] = b.getAttribute(attr);
      renderStep(stepIndex, opts);
    })
  );
}

function syncMapZoomControls(chart, show, defaultZoom = 1.1) {
  const host = chart?.getDom?.();
  if (!host) return;
  host.querySelectorAll(".map-zoom-controls").forEach((el) => el.remove());
  if (!show) return;

  const box = document.createElement("div");
  box.className = "map-zoom-controls";
  box.innerHTML = `
    <button type="button" class="map-zoom-btn" data-z="in" title="Acercar">+</button>
    <button type="button" class="map-zoom-btn" data-z="out" title="Alejar">−</button>
    <button type="button" class="map-zoom-btn" data-z="reset" title="Restablecer">⟲</button>
  `;
  box.querySelectorAll(".map-zoom-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.stopPropagation();
      const action = btn.dataset.z;
      const curZoom = chart.getOption()?.series?.[0]?.zoom || defaultZoom;
      if (action === "in") {
        chart.setOption({ series: [{ zoom: Math.min(3.5, Number((curZoom * 1.45).toFixed(2))) }] });
      } else if (action === "out") {
        chart.setOption({ series: [{ zoom: Math.max(1, Number((curZoom / 1.45).toFixed(2))) }] });
      } else {
        chart.setOption({ series: [{ zoom: defaultZoom, center: null }] });
      }
    });
  });
  host.appendChild(box);
}

function renderStep(stepIndex, opts = {}) {
  const chart = opts.chart || state.stageChart;
  if (!chart) return;

  if (!opts.chart) {
    state.activeStep = stepIndex;
    document.querySelectorAll(".story-step").forEach((el) => el.classList.toggle("is-active", Number(el.dataset.step) === stepIndex));
    document.querySelectorAll(".dot-link").forEach((el) => el.classList.toggle("active", Number(el.dataset.step) === stepIndex));
  }

  chart.clear();
  syncMapZoomControls(chart, false);
  const isMob = chart.getWidth() < 480;

  // --- 01: DESTINO DEL PRESUPUESTO (% APILADO 2020 VS 2025 EN UNA SOLA GRÁFICA) ---
  if (stepIndex === 0) {
    const rows = (state.data.capitulos || []).filter((r) => r.presupuesto_pagado > 0);
    const years = [2020, 2025];
    const totals = {};
    years.forEach((y) => {
      totals[y] = rows.filter((r) => r.ejercicio === y).reduce((a, b) => a + b.presupuesto_pagado, 0);
    });

    const cats = [
      { key: "1000", label: isMob ? "Personal" : "Personal (Nómina y Honorarios)", color: COLORS.ine },
      { key: "4000", label: isMob ? "Partidos y Transf." : "Transferencias y Partidos", color: COLORS.gold },
      { key: "3000", label: isMob ? "Servicios Grales." : "Servicios Generales (Rentas, TI, Operación)", color: COLORS.cyan },
      { key: "2000", label: isMob ? "Materiales" : "Materiales y Suministros", color: COLORS.emerald },
      { key: "5000", label: isMob ? "Bienes" : "Bienes Muebles e Inmuebles", color: COLORS.purple },
    ];

    setStageMeta(
      {
        kicker: "01 · Destino del Presupuesto (% del Gasto Total)",
        title: "¿A dónde se fue cada peso del INE? Comparativa 2020 vs. 2025",
        source: `${PNT_SOURCE} · Ejercicios con desglose completo por capítulo`,
        stepIndex,
      },
      opts
    );

    chart.setOption({
      animationDuration: 750,
      tooltip: {
        ...baseTooltip,
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: (ps) => {
          const y = years[ps[0].dataIndex];
          const tot = totals[y];
          const lines = ps.map((p) => {
            const raw = rows.find((r) => r.ejercicio === y && r.clave_capitulo === cats[p.seriesIndex].key)?.presupuesto_pagado || 0;
            return `${p.marker} ${p.seriesName}: <b>${p.value}%</b> (${fmtMoney(raw)})`;
          });
          return `<b>Ejercicio ${y} · Total ejercido: ${fmtMoney(tot)}</b><br/>${lines.join("<br/>")}`;
        },
      },
      legend: { top: 0, left: "center", itemGap: isMob ? 8 : 14, itemWidth: isMob ? 12 : 18, textStyle: { color: "#e5e2dc", fontSize: isMob ? 10.5 : 11.5 } },
      grid: { left: isMob ? 6 : 16, right: isMob ? 10 : 20, top: isMob ? 64 : 52, bottom: 16, containLabel: true },
      xAxis: {
        type: "category",
        data: years.map((y) => `Ejercicio ${y}\n(${fmtMoney(totals[y])})`),
        axisLabel: { color: "#f5f2ec", fontFamily: "JetBrains Mono", fontSize: isMob ? 10.5 : 12, interval: 0 },
      },
      yAxis: {
        type: "value",
        max: 100,
        axisLabel: { color: COLORS.axis, fontFamily: "JetBrains Mono", formatter: "{value}%" },
        splitLine: { lineStyle: { color: COLORS.grid } },
      },
      series: cats.map((c) => ({
        name: c.label,
        type: "bar",
        stack: "pct",
        barWidth: "46%",
        itemStyle: { color: c.color },
        label: {
          show: true,
          position: "inside",
          color: "#ffffff",
          fontFamily: "JetBrains Mono",
          fontSize: 11,
          formatter: (p) => (p.value >= 8 ? `${p.value}%` : ""),
        },
        data: years.map((y) => {
          const val = rows.find((r) => r.ejercicio === y && r.clave_capitulo === c.key)?.presupuesto_pagado || 0;
          return Number(((val / totals[y]) * 100).toFixed(1));
        }),
      })),
    });
    return;
  }

  // --- 02: PUBLICIDAD OFICIAL (PARTICIPACIÓN % Y TICKET MEDIO POR PAUTA) ---
  if (stepIndex === 1) {
    if (!state.data.publicidad || state.data.publicidad.length === 0) {
      const item = DATA_TABLES.find((t) => t.key === "publicidad");
      if (item) {
        loadTable(item).then((rows) => {
          if (rows.length > 0) renderStep(1, opts);
        });
        return;
      }
    }
    const pub = (state.data.publicidad || []).slice(0, 6);
    const mode = state.pubMode;

    const ctrlEl = setStageMeta(
      {
        kicker: "02 · Publicidad Oficial 2025 ($147.65 MDP)",
        title: mode === "participacion" ? "Distribución del gasto publicitario por medio (%)" : "Ticket promedio por pauta contratada (MXN)",
        source: `${PNT_SOURCE} · Comunicación Social 2025`,
        stepIndex,
        controlsHtml: `
        <div class="segmented">
          <button class="seg-btn ${mode === "participacion" ? "active" : ""}" data-pubmode="participacion">% del Gasto</button>
          <button class="seg-btn ${mode === "ticket" ? "active" : ""}" data-pubmode="ticket">Ticket Promedio / Pauta</button>
        </div>`,
      },
      opts
    );
    bindStageToggle(ctrlEl, "data-pubmode", "pubMode", 1, opts);

    if (mode === "participacion") {
      chart.setOption({
        animationDuration: 750,
        tooltip: {
          ...baseTooltip,
          trigger: "item",
          formatter: (p) => {
            const r = pub[p.dataIndex];
            return `<b>${r.tipo_medio}</b><br/>Gasto total: <b>${fmtMoney(r.gasto_total)}</b> (${r.porcentaje_del_gasto_total}%)<br/>Pautas: ${fmtInt(r.total_pautas)}<br/>Ticket promedio: <b>${fmtExactMXN(r.gasto_promedio_por_pauta)}</b>`;
          },
        },
        legend: isMob
          ? {
              bottom: 0,
              left: "center",
              itemWidth: 10,
              itemHeight: 10,
              itemGap: 8,
              textStyle: { color: "#e5e2dc", fontSize: 10 },
            }
          : { show: false },
        series: [
          {
            type: "pie",
            radius: isMob ? ["36%", "62%"] : ["44%", "74%"],
            center: isMob ? ["50%", "39%"] : ["50%", "52%"],
            itemStyle: { borderColor: "#141414", borderWidth: 3, borderRadius: 8 },
            label: isMob
              ? {
                  show: true,
                  position: "inside",
                  color: "#0a0a0a",
                  fontWeight: "bold",
                  fontFamily: "JetBrains Mono",
                  fontSize: 10.5,
                  formatter: (p) => (p.percent >= 7 ? `${p.percent.toFixed(0)}%` : ""),
                }
              : { color: "#f5f2ec", fontSize: 12, formatter: "{b}\n{d}%" },
            labelLine: { show: !isMob },
            color: [COLORS.gold, COLORS.ine, COLORS.cyan, COLORS.emerald, COLORS.purple, COLORS.slate],
            data: pub.map((r) => ({ name: r.tipo_medio, value: r.gasto_total })),
          },
        ],
      });
    } else {
      const sorted = [...pub].sort((a, b) => a.gasto_promedio_por_pauta - b.gasto_promedio_por_pauta);
      chart.setOption({
        animationDuration: 750,
        tooltip: {
          ...baseTooltip,
          trigger: "axis",
          axisPointer: { type: "shadow" },
          formatter: (ps) => {
            const r = sorted[ps[0].dataIndex];
            return `<b>${r.tipo_medio}</b><br/>Ticket promedio: <b>${fmtExactMXN(r.gasto_promedio_por_pauta)}</b><br/>Total de pautas: ${fmtInt(r.total_pautas)}<br/>Gasto acumulado: ${fmtMoney(r.gasto_total)}`;
          },
        },
        grid: { left: isMob ? 4 : 12, right: isMob ? 58 : 64, top: 14, bottom: 16, containLabel: true },
        xAxis: {
          type: "value",
          splitNumber: isMob ? 3 : 5,
          axisLabel: { color: COLORS.axis, fontFamily: "JetBrains Mono", fontSize: isMob ? 10 : 11, formatter: (v) => `$${(v / 1e3).toFixed(0)}k` },
          splitLine: { lineStyle: { color: COLORS.grid } },
        },
        yAxis: {
          type: "category",
          data: sorted.map((r) => {
            const label = isMob ? r.tipo_medio.replace("Otros servicios asociados", "Otros serv.") : r.tipo_medio;
            return `${label} (${r.total_pautas})`;
          }),
          axisLabel: { color: "#f5f2ec", fontSize: isMob ? 10 : 11.5 },
        },
        series: [
          {
            type: "bar",
            label: {
              show: true,
              position: "right",
              color: "#f5f2ec",
              fontFamily: "JetBrains Mono",
              fontSize: isMob ? 10 : 11,
              formatter: (p) => fmtExactMXN(p.value),
            },
            data: sorted.map((r) => ({
              value: r.gasto_promedio_por_pauta,
              itemStyle: { color: r.tipo_medio === "Televisión" ? COLORS.ine : COLORS.gold, borderRadius: [0, 6, 6, 0] },
            })),
          },
        ],
      }, true);
    }
    return;
  }

  // --- 03: PARTIDOS POLÍTICOS (PORCENTAJES POR PARTIDO + EVOLUCIÓN) ---
  if (stepIndex === 2) {
    const mode = state.partidosMode;
    const ctrlEl = setStageMeta(
      {
        kicker: "03 · Financiamiento Público a Partidos",
        title: mode === "pct" ? "Reparto porcentual de la bolsa pública por partido (2020–2026)" : "Evolución de la bolsa total: años ordinarios vs. electorales",
        source: `${PNT_SOURCE} · Prerrogativas a Partidos Políticos`,
        stepIndex,
        controlsHtml: `
        <div class="segmented">
          <button class="seg-btn ${mode === "pct" ? "active" : ""}" data-pmode="pct">% por Partido</button>
          <button class="seg-btn ${mode === "bolsa" ? "active" : ""}" data-pmode="bolsa">Bolsa Total ($)</button>
        </div>`,
      },
      opts
    );
    bindStageToggle(ctrlEl, "data-pmode", "partidosMode", 2, opts);

    if (mode === "pct") {
      const years = [2020, 2021, 2023, 2024, 2026];
      const parties = ["MORENA", "PAN", "PRI", "MC", "PVEM", "PT", "PRD"];
      const anual = state.data.partidosAnual || [];

      chart.setOption({
        animationDuration: 650,
        tooltip: {
          ...baseTooltip,
          trigger: "axis",
          axisPointer: { type: "shadow" },
          formatter: (ps) => {
            const y = years[ps[0].dataIndex];
            const lines = ps
              .filter((p) => p.value > 0)
              .map((p) => {
                const row = anual.find((r) => r.ejercicio === y && r.partido_siglas === p.seriesName);
                return `${p.marker} ${p.seriesName}: <b>${p.value}%</b> (${fmtMoney(row?.monto_total_anual)})`;
              });
            return `<b>Ejercicio ${y}</b><br/>${lines.join("<br/>")}`;
          },
        },
        legend: { top: 0, left: "center", itemGap: isMob ? 10 : 14, itemWidth: isMob ? 12 : 18, textStyle: { color: "#e5e2dc", fontFamily: "JetBrains Mono", fontSize: isMob ? 10.5 : 11.5 } },
        grid: { left: isMob ? 6 : 16, right: isMob ? 10 : 16, top: isMob ? 66 : 44, bottom: 18, containLabel: true },
        xAxis: {
          type: "category",
          data: years.map((y) => (y === 2021 || y === 2024 ? `${y} ★` : `${y}`)),
          axisLabel: { color: "#f5f2ec", fontFamily: "JetBrains Mono", fontSize: isMob ? 10 : 11.5, interval: 0 },
        },
        yAxis: {
          type: "value",
          max: 100,
          axisLabel: { color: COLORS.axis, fontFamily: "JetBrains Mono", formatter: "{value}%" },
          splitLine: { lineStyle: { color: COLORS.grid } },
        },
        series: parties.map((sigla) => ({
          name: sigla,
          type: "bar",
          stack: "partidos",
          barWidth: "50%",
          itemStyle: { color: PARTY_COLORS[sigla] || COLORS.slate },
          label: {
            show: true,
            position: "inside",
            color: "#ffffff",
            fontFamily: "JetBrains Mono",
            fontSize: 10,
            formatter: (p) => (p.value >= 12 ? `${p.value}%` : ""),
          },
          data: years.map((y) => anual.find((r) => r.ejercicio === y && r.partido_siglas === sigla)?.porcentaje_bolsa_anual || 0),
        })),
      });
    } else {
      const ciclo = state.data.partidosCiclo || [];
      chart.setOption({
        animationDuration: 650,
        tooltip: {
          ...baseTooltip,
          trigger: "axis",
          formatter: (ps) => {
            const r = ciclo[ps[0].dataIndex];
            return `<b>Ejercicio ${r.ejercicio}</b> (${r.es_anio_electoral ? "Año Electoral ★" : "Ordinario"})<br/>Bolsa total: <b>${fmtMoney(r.monto_total_ejercicio)}</b>`;
          },
        },
        grid: { left: isMob ? 6 : 16, right: isMob ? 12 : 20, top: 28, bottom: 20, containLabel: true },
        xAxis: { type: "category", data: ciclo.map((r) => `${r.ejercicio}${r.es_anio_electoral ? " ★" : ""}`), axisLabel: { color: "#f5f2ec", fontFamily: "JetBrains Mono", fontSize: isMob ? 9.5 : 11.5, interval: 0 } },
        yAxis: { type: "value", axisLabel: { color: COLORS.axis, fontFamily: "JetBrains Mono", fontSize: isMob ? 10 : 11.5, formatter: (v) => `$${(v / 1e9).toFixed(0)}B` }, splitLine: { lineStyle: { color: COLORS.grid } } },
        series: [
          {
            type: "bar",
            barWidth: "46%",
            label: { show: true, position: "top", color: "#f5f2ec", fontFamily: "JetBrains Mono", fontSize: isMob ? 9.5 : 11, formatter: (p) => fmtMoney(p.value) },
            data: ciclo.map((r) => ({
              value: r.monto_total_ejercicio,
              itemStyle: { color: r.es_anio_electoral ? COLORS.ine : COLORS.gold, borderRadius: [8, 8, 0, 0] },
            })),
          },
        ],
      });
    }
    return;
  }

  // --- 04: CONTRATOS AD VS LICITACIÓN (% EN NÚMERO VS % EN DINERO + REFERENCIA 30%) ---
  if (stepIndex === 3) {
    const procs = state.data.procedimientos || [];
    const sumBy = (pred) =>
      procs.filter(pred).reduce((acc, r) => ({ c: acc.c + (r.total_contratos || 0), m: acc.m + (r.monto_total_con_impuestos || 0) }), { c: 0, m: 0 });

    const total = sumBy(() => true);
    const ad = sumBy((r) => r.tipo_procedimiento === "Adjudicación directa");
    const lic = sumBy((r) => r.tipo_procedimiento === "Licitación pública");
    const inv = sumBy((r) => r.tipo_procedimiento.includes("Invitación"));
    const otros = { c: total.c - ad.c - lic.c - inv.c, m: total.m - ad.m - lic.m - inv.m };

    const pct = (v, t) => Number(((v / t) * 100).toFixed(1));

    setStageMeta(
      {
        kicker: "04 · Foco Rojo en Compras Públicas (2021–2023)",
        title: "Volumen de contratos vs. Dinero ejercido por procedimiento",
        source: `${PNT_SOURCE} · 125,433 contratos auditados ($6,257 MDP)`,
        stepIndex,
      },
      opts
    );

    chart.setOption({
      animationDuration: 650,
      tooltip: {
        ...baseTooltip,
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: (ps) => {
          const isVol = ps[0].dataIndex === 0;
          const header = isVol ? `Por número de contratos (${fmtInt(total.c)})` : `Por monto ejercido (${fmtMoney(total.m)})`;
          const rawMap = [ad, lic, inv, otros];
          return `<b>${header}</b><br/>` + ps.map((p, i) => `${p.marker} ${p.seriesName}: <b>${p.value}%</b> (${isVol ? fmtInt(rawMap[i].c) + " contratos" : fmtMoney(rawMap[i].m)})`).join("<br/>");
        },
      },
      legend: { top: 0, left: "center", itemGap: isMob ? 10 : 14, itemWidth: isMob ? 12 : 18, textStyle: { color: "#e5e2dc", fontSize: isMob ? 10.5 : 11.5 } },
      grid: { left: isMob ? 6 : 16, right: isMob ? 12 : 24, top: isMob ? 68 : 46, bottom: 18, containLabel: true },
      xAxis: {
        type: "category",
        data: ["% por Número\nde Contratos", "% por Monto\nEjercido ($)"],
        axisLabel: { color: "#f5f2ec", fontFamily: "JetBrains Mono", fontSize: isMob ? 10.5 : 12, interval: 0 },
      },
      yAxis: {
        type: "value",
        max: 100,
        axisLabel: { color: COLORS.axis, fontFamily: "JetBrains Mono", formatter: "{value}%" },
        splitLine: { lineStyle: { color: COLORS.grid } },
      },
      series: [
        {
          name: "Adjudicación Directa",
          type: "bar",
          stack: "mix",
          barWidth: "44%",
          itemStyle: { color: COLORS.ine },
          label: { show: true, position: "inside", color: "#fff", fontFamily: "JetBrains Mono", fontWeight: "bold", formatter: "{c}%" },
          data: [pct(ad.c, total.c), pct(ad.m, total.m)],
          markLine: {
            symbol: "none",
            lineStyle: { color: COLORS.emerald, type: "dashed", width: 2 },
            label: { color: COLORS.emerald, fontFamily: "JetBrains Mono", fontSize: 10.5, position: "insideEndTop", formatter: "Límite recomendado AD (~30%)" },
            data: [{ yAxis: 30 }],
          },
        },
        {
          name: "Licitación Pública",
          type: "bar",
          stack: "mix",
          itemStyle: { color: COLORS.gold },
          label: { show: true, position: "inside", color: "#0a0a0a", fontFamily: "JetBrains Mono", fontWeight: "bold", formatter: (p) => (p.value >= 5 ? `${p.value}%` : "") },
          data: [pct(lic.c, total.c), pct(lic.m, total.m)],
        },
        {
          name: "Invitación a 3 personas",
          type: "bar",
          stack: "mix",
          itemStyle: { color: COLORS.cyan },
          data: [pct(inv.c, total.c), pct(inv.m, total.m)],
        },
        {
          name: "Otros",
          type: "bar",
          stack: "mix",
          itemStyle: { color: COLORS.slate },
          data: [pct(otros.c, total.c), pct(otros.m, total.m)],
        },
      ],
    });
    return;
  }

  // --- 05: DESTINO DE LA ADJUDICACIÓN DIRECTA (SERVICIOS VS PROVEEDORES) ---
  if (stepIndex === 4) {
    const mode = state.adMode;
    const ctrlEl = setStageMeta(
      {
        kicker: "05 · Adjudicación Directa ($2,734 MDP)",
        title: mode === "materia" ? "¿Qué servicios se contratan sin licitar?" : "Top 10 beneficiarios de Adjudicación Directa",
        source: `${PNT_SOURCE} · Adjudicaciones Directas 2021–2023`,
        stepIndex,
        controlsHtml: `
        <div class="segmented">
          <button class="seg-btn ${mode === "materia" ? "active" : ""}" data-admode="materia">Por Servicio / Materia</button>
          <button class="seg-btn ${mode === "proveedores" ? "active" : ""}" data-admode="proveedores">Top Beneficiarios</button>
        </div>`,
      },
      opts
    );
    bindStageToggle(ctrlEl, "data-admode", "adMode", 4, opts);

    if (mode === "materia") {
      const mat = (state.data.adMateria || []).filter((r) => r.monto_total > 1e6).reverse();
      chart.setOption({
        animationDuration: 650,
        tooltip: {
          ...baseTooltip,
          trigger: "axis",
          axisPointer: { type: "shadow" },
          formatter: (ps) => {
            const r = mat[ps[0].dataIndex];
            return `<b>${r.materia}</b><br/>Monto: <b>${fmtMoney(r.monto_total)}</b> (${r.pct_monto}%)<br/>Contratos directos: ${fmtInt(r.total_contratos)}`;
          },
        },
        grid: { left: isMob ? 4 : 12, right: isMob ? 48 : 64, top: 14, bottom: 16, containLabel: true },
        xAxis: { type: "value", splitNumber: isMob ? 3 : 5, axisLabel: { color: COLORS.axis, fontFamily: "JetBrains Mono", fontSize: isMob ? 10 : 11, formatter: (v) => `$${(v / 1e6).toFixed(0)}M` }, splitLine: { lineStyle: { color: COLORS.grid } } },
        yAxis: { type: "category", data: mat.map((r) => (isMob && r.materia.length > 18 ? r.materia.slice(0, 18) + "…" : r.materia)), axisLabel: { color: "#f5f2ec", fontSize: isMob ? 10 : 12 } },
        series: [
          {
            type: "bar",
            barWidth: "52%",
            label: { show: true, position: "right", color: "#f5f2ec", fontFamily: "JetBrains Mono", fontSize: 11, formatter: (p) => `${mat[p.dataIndex].pct_monto}%` },
            data: mat.map((r, i) => ({
              value: r.monto_total,
              itemStyle: { color: [COLORS.slate, COLORS.cyan, COLORS.gold, COLORS.goldLight, COLORS.ine][i % 5], borderRadius: [0, 6, 6, 0] },
            })),
          },
        ],
      });
    } else {
      const top = (state.data.adProveedores || []).slice(0, 10).reverse();
      chart.setOption({
        animationDuration: 650,
        tooltip: {
          ...baseTooltip,
          trigger: "axis",
          axisPointer: { type: "shadow" },
          formatter: (ps) => {
            const r = top[ps[0].dataIndex];
            return `<b>${r.proveedor_nombre}</b><br/>Tipo: ${r.tipo_persona} · Contratos AD: <b>${fmtInt(r.total_contratos)}</b><br/>Monto acumulado: <b>${fmtMoney(r.monto_total)}</b>`;
          },
        },
        grid: { left: isMob ? 4 : 10, right: isMob ? 54 : 56, top: 10, bottom: 12, containLabel: true },
        xAxis: { type: "value", splitNumber: isMob ? 3 : 5, axisLabel: { color: COLORS.axis, fontFamily: "JetBrains Mono", fontSize: isMob ? 10 : 11, formatter: (v) => `$${(v / 1e6).toFixed(0)}M` }, splitLine: { lineStyle: { color: COLORS.grid } } },
        yAxis: {
          type: "category",
          data: top.map((r) => {
            const limit = isMob ? 17 : 30;
            return r.proveedor_nombre.length > limit ? r.proveedor_nombre.slice(0, limit) + "…" : r.proveedor_nombre;
          }),
          axisLabel: { color: "#f5f2ec", fontSize: isMob ? 9.5 : 10.5 },
        },
        series: [
          {
            type: "bar",
            label: { show: true, position: "right", color: COLORS.axis, fontFamily: "JetBrains Mono", fontSize: 10.5, formatter: (p) => `${top[p.dataIndex].total_contratos} ctos.` },
            data: top.map((r) => ({
              value: r.monto_total,
              itemStyle: { color: r.tipo_persona === "FISICA" ? COLORS.ine : COLORS.gold, borderRadius: [0, 6, 6, 0] },
            })),
          },
        ],
      });
    }
    return;
  }

  // --- 06: MAPA GEOGRÁFICO DE CONTRATACIONES EN MÉXICO ---
  if (stepIndex === 5) {
    const estados = (state.data.contratacionesEstados || []).filter((r) => r.cve_inegi !== "00");
    setStageMeta(
      {
        kicker: "06 · Mapa Geográfico de Compras (Sin Oficinas Centrales)",
        title: "Gasto contratado por Entidad Federativa (2021–2023)",
        source: `${PNT_SOURCE} · Oficinas Centrales suma aparte $1,807 MDP (28.9%)`,
        stepIndex,
      },
      opts
    );

    if (state.mexicoGeoLoaded) {
      const mapData = estados.map((r) => ({
        name: normalizeStateName(r.entidad_federativa),
        value: r.monto_total_contratado,
        contratos: r.total_contratos,
        pct: r.porcentaje_monto_total,
        promedio: r.monto_promedio_contrato,
      }));
      const maxVal = Math.max(...mapData.map((d) => d.value));

      chart.setOption({
        animationDuration: 650,
        tooltip: {
          ...baseTooltip,
          trigger: "item",
          formatter: (p) => {
            const d = p.data;
            if (!d) return `<b>${p.name}</b><br/>Sin datos`;
            return `<b>${p.name}</b><br/>Monto contratado: <b>${fmtMoney(d.value)}</b> (${d.pct}% nacional)<br/>Contratos: ${fmtInt(d.contratos)}<br/>Promedio/contrato: ${fmtExactMXN(d.promedio)}`;
          },
        },
        visualMap: isMob
          ? {
              min: 0,
              max: maxVal,
              orient: "horizontal",
              left: "center",
              bottom: 0,
              itemWidth: 12,
              itemHeight: 80,
              text: ["Mayor", "Menor"],
              textStyle: { color: COLORS.axis, fontFamily: "JetBrains Mono", fontSize: 9.5 },
              inRange: { color: ["#1e1b18", "#5c4920", "#c9a84c", "#c81d4e"] },
              formatter: (v) => fmtMoney(v),
            }
          : {
              min: 0,
              max: maxVal,
              left: 14,
              bottom: 14,
              text: ["Mayor gasto", "Menor"],
              textStyle: { color: COLORS.axis, fontFamily: "JetBrains Mono", fontSize: 10 },
              inRange: { color: ["#1e1b18", "#5c4920", "#c9a84c", "#c81d4e"] },
              formatter: (v) => fmtMoney(v),
            },
        series: [
          {
            name: "Contrataciones",
            type: "map",
            map: "mexico",
            roam: isMob ? "move" : true,
            scaleLimit: { min: 1, max: 3.5 },
            zoom: isMob ? 1.05 : 1.15,
            top: isMob ? 6 : "middle",
            itemStyle: { areaColor: "#1a1a1a", borderColor: "rgba(255,255,255,0.22)", borderWidth: 0.7 },
            emphasis: { label: { show: true, color: "#ffffff", fontSize: 11 }, itemStyle: { areaColor: COLORS.goldLight } },
            data: mapData,
          },
        ],
      });
      syncMapZoomControls(chart, true, isMob ? 1.05 : 1.15);
    }
    return;
  }

  // --- 07: NÓMINA DE ESTRUCTURA VS HONORARIOS ---
  if (stepIndex === 6) {
    const comp = state.data.nominaComp || [];
    const totPers = comp.reduce((a, b) => a + b.total_personas_unicas, 0);
    const totMasa = comp.reduce((a, b) => a + b.masa_mensual_bruta, 0);

    setStageMeta(
      {
        kicker: "07 · Estructura Laboral (2025)",
        title: "Personal en Plaza Fija vs. Honorarios (% Personas y % Gasto Mensual)",
        source: `${PNT_SOURCE} · Padrón de Personal y Honorarios 2025`,
        stepIndex,
      },
      opts
    );

    const plaza = comp.find((r) => r.regimen_contratacion.includes("Nómina")) || comp[0];
    const hon = comp.find((r) => r.regimen_contratacion.includes("Honorarios")) || comp[1];

    chart.setOption({
      animationDuration: 650,
      tooltip: {
        ...baseTooltip,
        trigger: "axis",
        axisPointer: { type: "shadow" },
        formatter: (ps) => {
          const isPers = ps[0].dataIndex === 0;
          return `<b>${isPers ? "Fuerza Laboral (74,722 personas)" : "Masa Salarial Bruta ($1,809.6 MDP/mes)"}</b><br/>` +
            ps.map((p) => {
              const obj = p.seriesIndex === 0 ? hon : plaza;
              const raw = isPers ? `${fmtInt(obj.total_personas_unicas)} personas` : `${fmtMoney(obj.masa_mensual_bruta)}/mes`;
              return `${p.marker} ${p.seriesName}: <b>${p.value}%</b> (${raw})`;
            }).join("<br/>");
        },
      },
      legend: { top: 0, left: "center", itemGap: isMob ? 10 : 16, textStyle: { color: "#e5e2dc", fontSize: isMob ? 10.5 : 11.5 } },
      grid: { left: isMob ? 6 : 16, right: isMob ? 12 : 20, top: isMob ? 62 : 44, bottom: 18, containLabel: true },
      xAxis: {
        type: "category",
        data: ["% del Total\nde Trabajadores", "% del Costo\nMensual Bruto"],
        axisLabel: { color: "#f5f2ec", fontFamily: "JetBrains Mono", fontSize: isMob ? 10.5 : 12, interval: 0 },
      },
      yAxis: {
        type: "value",
        max: 100,
        axisLabel: { color: COLORS.axis, fontFamily: "JetBrains Mono", formatter: "{value}%" },
        splitLine: { lineStyle: { color: COLORS.grid } },
      },
      series: [
        {
          name: "Honorarios Asimilados (Eventual)",
          type: "bar",
          stack: "lab",
          barWidth: "46%",
          itemStyle: { color: COLORS.ine },
          label: { show: true, position: "inside", color: "#fff", fontFamily: "JetBrains Mono", fontWeight: "bold", formatter: "{c}%" },
          data: [Number(((hon.total_personas_unicas / totPers) * 100).toFixed(1)), Number(((hon.masa_mensual_bruta / totMasa) * 100).toFixed(1))],
        },
        {
          name: "Plaza de Estructura (Nómina Fija)",
          type: "bar",
          stack: "lab",
          itemStyle: { color: COLORS.gold },
          label: { show: true, position: "inside", color: "#0a0a0a", fontFamily: "JetBrains Mono", fontWeight: "bold", formatter: "{c}%" },
          data: [Number(((plaza.total_personas_unicas / totPers) * 100).toFixed(1)), Number(((plaza.masa_mensual_bruta / totMasa) * 100).toFixed(1))],
        },
      ],
    });
    return;
  }

  // --- 08: PIRÁMIDE SALARIAL Y MANDOS ALTOS ---
  if (stepIndex === 7) {
    const mode = state.salarioMode;
    const ctrlEl = setStageMeta(
      {
        kicker: "08 · Distribución Salarial 2025",
        title: mode === "concentracion" ? "% de Plazas vs. % de la Nómina por Nivel Salarial" : "Top 10 Puestos Mejor Pagados (Bruto vs. Neto Mensual)",
        source: `${PNT_SOURCE} · Tabulador Salarial 2025 (2,536 cargos)`,
        stepIndex,
        controlsHtml: `
        <div class="segmented">
          <button class="seg-btn ${mode === "concentracion" ? "active" : ""}" data-salmode="concentracion">Concentración %</button>
          <button class="seg-btn ${mode === "cupula" ? "active" : ""}" data-salmode="cupula">Sueldos Top 10</button>
        </div>`,
      },
      opts
    );
    bindStageToggle(ctrlEl, "data-salmode", "salarioMode", 7, opts);

    if (mode === "concentracion") {
      const tramos = state.data.salariosTramos || [];
      chart.setOption({
        animationDuration: 650,
        tooltip: {
          ...baseTooltip,
          trigger: "axis",
          axisPointer: { type: "shadow" },
          formatter: (ps) => {
            const r = tramos[ps[0].dataIndex];
            return `<b>${r.tramo}</b><br/>Plazas reportadas: <b>${r.pct_plazas}%</b> (${fmtInt(r.plazas)})<br/>Masa salarial absorbida: <b>${r.pct_masa}%</b> (${fmtMoney(r.masa_mensual_bruta)}/mes)`;
          },
        },
        legend: { top: 0, left: isMob ? "center" : undefined, right: isMob ? undefined : 0, textStyle: { color: COLORS.axis, fontSize: isMob ? 10.5 : 11 } },
        grid: { left: isMob ? 6 : 16, right: isMob ? 10 : 20, top: isMob ? 46 : 40, bottom: 20, containLabel: true },
        xAxis: {
          type: "category",
          data: tramos.map((r) =>
            isMob ? r.tramo.replace(" (", "\n(").replace(" ", "\n") : r.tramo.replace(" (", "\n(")
          ),
          axisLabel: { color: "#f5f2ec", fontSize: isMob ? 9 : 11, lineHeight: isMob ? 11 : 14, interval: 0 },
        },
        yAxis: {
          type: "value",
          axisLabel: { color: COLORS.axis, fontFamily: "JetBrains Mono", fontSize: isMob ? 10 : 11, formatter: "{value}%" },
          splitLine: { lineStyle: { color: COLORS.grid } },
        },
        series: [
          {
            name: "% de Plazas",
            type: "bar",
            itemStyle: { color: "rgba(245,242,236,0.28)", borderRadius: [6, 6, 0, 0] },
            label: { show: true, position: "top", color: COLORS.axis, fontFamily: "JetBrains Mono", fontSize: isMob ? 9 : 11, formatter: "{c}%" },
            data: tramos.map((r) => r.pct_plazas),
          },
          {
            name: "% de la Masa Salarial",
            type: "bar",
            itemStyle: { color: COLORS.ine, borderRadius: [6, 6, 0, 0] },
            label: { show: true, position: "top", color: COLORS.goldLight, fontFamily: "JetBrains Mono", fontWeight: "bold", fontSize: isMob ? 9 : 11, formatter: "{c}%" },
            data: tramos.map((r) => r.pct_masa),
          },
        ],
      });
    } else {
      const top = (state.data.salarios || []).slice(0, 10).reverse();
      chart.setOption({
        animationDuration: 650,
        tooltip: {
          ...baseTooltip,
          trigger: "axis",
          axisPointer: { type: "shadow" },
          formatter: (ps) => {
            const r = top[ps[0].dataIndex];
            return `<b>${r.cargo}</b><br/>Bruto mensual: <b>${fmtExactMXN(r.sueldo_bruto_promedio)}</b><br/>Neto mensual: <b>${fmtExactMXN(r.sueldo_neto_promedio)}</b>`;
          },
        },
        legend: { top: 0, left: isMob ? "center" : undefined, right: isMob ? undefined : 0, textStyle: { color: COLORS.axis, fontSize: isMob ? 10.5 : 11 } },
        grid: { left: isMob ? 4 : 10, right: isMob ? 14 : 20, top: isMob ? 36 : 34, bottom: 10, containLabel: true },
        xAxis: { type: "value", splitNumber: isMob ? 3 : 5, axisLabel: { color: COLORS.axis, fontFamily: "JetBrains Mono", fontSize: isMob ? 10 : 11, formatter: (v) => `$${(v / 1e3).toFixed(0)}k` }, splitLine: { lineStyle: { color: COLORS.grid } } },
        yAxis: {
          type: "category",
          data: top.map((r) => {
            const limit = isMob ? 17 : 30;
            return r.cargo.length > limit ? r.cargo.slice(0, limit) + "…" : r.cargo;
          }),
          axisLabel: { color: "#f5f2ec", fontSize: isMob ? 9.5 : 10.5 },
        },
        series: [
          { name: "Bruto Mensual", type: "bar", itemStyle: { color: "rgba(245,242,236,0.22)", borderRadius: [0, 4, 4, 0] }, data: top.map((r) => r.sueldo_bruto_promedio) },
          { name: "Neto Mensual", type: "bar", itemStyle: { color: COLORS.gold, borderRadius: [0, 4, 4, 0] }, data: top.map((r) => r.sueldo_neto_promedio) },
        ],
      });
    }
    return;
  }

  // --- 09: MAPA Y ANOMALÍAS DE VIÁTICOS ---
  if (stepIndex === 8) {
    const mode = state.viaticosMode;
    const ctrlEl = setStageMeta(
      {
        kicker: "09 · Viáticos y Comisiones Oficiales (2025)",
        title: mode === "mapa" ? "Mapa Nacional de Gasto en Viáticos ($114.05 MDP)" : "Viajes Atípicos vs. Promedio Nacional ($5,240)",
        source: `${PNT_SOURCE} · 21,764 comisiones registradas en 2025`,
        stepIndex,
        controlsHtml: `
        <div class="segmented">
          <button class="seg-btn ${mode === "mapa" ? "active" : ""}" data-vmode="mapa">Mapa de México</button>
          <button class="seg-btn ${mode === "outliers" ? "active" : ""}" data-vmode="outliers">Focos Rojos (&ge;10x prom.)</button>
        </div>`,
      },
      opts
    );
    bindStageToggle(ctrlEl, "data-vmode", "viaticosMode", 8, opts);

    if (mode === "mapa" && state.mexicoGeoLoaded) {
      const estados = state.data.viaticosEstados || [];
      const mapData = estados.map((r) => ({
        name: normalizeStateName(r.entidad_federativa),
        value: r.gasto_total_erogado,
        viajes: r.total_viajes,
        pct: r.porcentaje_gasto_nacional,
        promedio: r.gasto_promedio_viaje,
      }));
      const maxVal = Math.max(...mapData.map((d) => d.value));

      chart.setOption({
        animationDuration: 650,
        tooltip: {
          ...baseTooltip,
          trigger: "item",
          formatter: (p) => {
            const d = p.data;
            if (!d) return `<b>${p.name}</b>`;
            return `<b>${p.name}</b><br/>Gasto viáticos: <b>${fmtMoney(d.value)}</b> (${d.pct}% nacional)<br/>Comisiones: ${fmtInt(d.viajes)}<br/>Promedio/viaje: <b>${fmtExactMXN(d.promedio)}</b>`;
          },
        },
        visualMap: isMob
          ? {
              min: 0,
              max: maxVal,
              orient: "horizontal",
              left: "center",
              bottom: 0,
              itemWidth: 12,
              itemHeight: 80,
              text: ["Mayor", "Menor"],
              textStyle: { color: COLORS.axis, fontFamily: "JetBrains Mono", fontSize: 9.5 },
              inRange: { color: ["#141c24", "#1d4e6b", "#38bdf8", "#c81d4e"] },
              formatter: (v) => fmtMoney(v),
            }
          : {
              min: 0,
              max: maxVal,
              left: 14,
              bottom: 14,
              text: ["Mayor gasto", "Menor"],
              textStyle: { color: COLORS.axis, fontFamily: "JetBrains Mono", fontSize: 10 },
              inRange: { color: ["#141c24", "#1d4e6b", "#38bdf8", "#c81d4e"] },
              formatter: (v) => fmtMoney(v),
            },
        series: [
          {
            name: "Viáticos",
            type: "map",
            map: "mexico",
            roam: isMob ? "move" : true,
            scaleLimit: { min: 1, max: 3.5 },
            zoom: isMob ? 1.05 : 1.15,
            top: isMob ? 6 : "middle",
            itemStyle: { areaColor: "#1a1a1a", borderColor: "rgba(255,255,255,0.22)", borderWidth: 0.7 },
            emphasis: { label: { show: true, color: "#ffffff", fontSize: 11 }, itemStyle: { areaColor: COLORS.goldLight } },
            data: mapData,
          },
        ],
      });
      syncMapZoomControls(chart, true, isMob ? 1.05 : 1.15);
    } else {
      const top = (state.data.viaticosOutliers || []).slice(0, 12).reverse();
      chart.setOption({
        animationDuration: 750,
        tooltip: {
          ...baseTooltip,
          trigger: "axis",
          axisPointer: { type: "shadow" },
          formatter: (ps) => {
            const r = top[ps[0].dataIndex];
            return `<b>${r.ciudad_destino}, ${r.estado_destino}</b><br/>Cargo: ${r.cargo}<br/>Área: ${r.area_adscripcion}<br/>Importe: <b>${fmtExactMXN(r.importe_total_erogado)}</b> (<b>${r.veces_promedio}x</b> el promedio nacional)`;
          },
        },
        grid: { left: isMob ? 4 : 10, right: isMob ? 42 : 64, top: 24, bottom: 12, containLabel: true },
        xAxis: {
          type: "value",
          splitNumber: isMob ? 2 : 5,
          axisLabel: { color: COLORS.axis, fontFamily: "JetBrains Mono", fontSize: isMob ? 10 : 11, formatter: (v) => `$${(v / 1e3).toFixed(0)}k` },
          splitLine: { lineStyle: { color: COLORS.grid } },
        },
        yAxis: {
          type: "category",
          data: top.map((r, i) => {
            const city = isMob && r.ciudad_destino.length > 14 ? r.ciudad_destino.slice(0, 14) + "…" : r.ciudad_destino;
            return `#${12 - i} ${city} (${r.estado_destino.slice(0, 3).toUpperCase()})`;
          }),
          axisLabel: { color: "#f5f2ec", fontSize: isMob ? 9.5 : 11 },
        },
        series: [
          {
            type: "bar",
            itemStyle: { color: COLORS.ine, borderRadius: [0, 6, 6, 0] },
            label: { show: true, position: "right", color: COLORS.goldLight, fontFamily: "JetBrains Mono", fontSize: isMob ? 9.5 : 10.5, formatter: (p) => `${top[p.dataIndex].veces_promedio}x` },
            data: top.map((r) => r.importe_total_erogado),
            markLine: {
              symbol: "none",
              lineStyle: { color: COLORS.emerald, type: "dashed", width: 2 },
              label: { color: COLORS.emerald, fontFamily: "JetBrains Mono", fontSize: isMob ? 9.5 : 10, position: "end", formatter: isMob ? "Prom. $5.2k" : "Promedio nacional ($5.2k)" },
              data: [{ xAxis: 5240.56 }],
            },
          },
        ],
      });
    }
  }
}

// ==================== WIKIPEDIA-STYLE HOVER TOOLTIPS ====================
function setupWikiTooltips() {
  const pop = document.getElementById("wiki-popover");
  if (!pop) return;

  const show = (el) => {
    pop.textContent = el.dataset.tip || "";
    pop.hidden = false;
    const rect = el.getBoundingClientRect();
    const popRect = pop.getBoundingClientRect();
    let left = rect.left + rect.width / 2 - popRect.width / 2;
    left = Math.max(12, Math.min(window.innerWidth - popRect.width - 12, left));
    let top = rect.top - popRect.height - 10;
    if (top < 12) top = rect.bottom + 10;
    pop.style.left = `${left}px`;
    pop.style.top = `${top}px`;
  };

  const hide = () => {
    pop.hidden = true;
  };

  document.querySelectorAll(".wiki-tip").forEach((el) => {
    el.addEventListener("mouseenter", () => show(el));
    el.addEventListener("focus", () => show(el));
    el.addEventListener("mouseleave", hide);
    el.addEventListener("blur", hide);
  });
}

// ==================== PARALLAX & SCROLL OBSERVER ====================
function setupParallaxAndProgress() {
  const progressFill = document.getElementById("progress-fill");
  const grid = document.getElementById("parallax-grid");
  const glow = document.getElementById("parallax-glow");
  const accent = document.getElementById("parallax-accent");
  const heroContent = document.getElementById("hero-content");

  const onScroll = () => {
    const y = window.scrollY;
    const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
    if (progressFill && maxScroll > 0) progressFill.style.width = `${Math.min(100, (y / maxScroll) * 100)}%`;
    if (y < window.innerHeight * 1.2) {
      if (grid) grid.style.transform = `translate3d(0, ${y * 0.22}px, 0)`;
      if (glow) glow.style.transform = `translate3d(0, ${y * 0.36}px, 0)`;
      if (accent) accent.style.transform = `translate3d(0, ${y * -0.15}px, 0)`;
      if (heroContent) {
        heroContent.style.transform = `translate3d(0, ${y * 0.14}px, 0)`;
        heroContent.style.opacity = `${Math.max(0, 1 - y / (window.innerHeight * 0.85))}`;
      }
    }
  };

  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
}

function setupScrollyObserver() {
  const steps = document.querySelectorAll(".story-step");
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const idx = Number(entry.target.dataset.step);
          if (idx !== state.activeStep) renderStep(idx);
        }
      });
    },
    { rootMargin: "-35% 0px -45% 0px", threshold: 0.05 }
  );
  steps.forEach((s) => observer.observe(s));
}

// ==================== EXPLORER TABLE (ORDENABLE + PAGINADA) ====================
const EXPLORER_SCHEMAS = {
  adProveedores: {
    defaultSort: { key: "monto_total", dir: "desc" },
    columns: [
      { key: "ranking", label: "#", num: true, render: (r) => r.ranking },
      { key: "proveedor_nombre", label: "Proveedor (Adjudicación Directa)", render: (r) => `<strong>${r.proveedor_nombre}</strong>` },
      { key: "rfc_proveedor", label: "RFC", render: (r) => `<span class="badge-mini">${r.rfc_proveedor || "—"}</span>` },
      { key: "tipo_persona", label: "Tipo", render: (r) => `<span class="${r.tipo_persona === "FISICA" ? "badge-alert" : "badge-mini"}">${r.tipo_persona}</span>` },
      { key: "total_contratos", label: "Contratos AD", num: true, render: (r) => fmtInt(r.total_contratos) },
      { key: "monto_total", label: "Monto Acumulado", num: true, render: (r) => `<strong>${fmtMoney(r.monto_total)}</strong>` },
    ],
    searchFields: ["proveedor_nombre", "rfc_proveedor", "tipo_persona"],
  },
  proveedores: {
    defaultSort: { key: "monto_total_acumulado", dir: "desc" },
    columns: [
      { key: "ranking", label: "#", num: true, render: (r) => r.ranking },
      { key: "proveedor_nombre", label: "Proveedor (Todos los procedimientos)", render: (r) => `<strong>${r.proveedor_nombre}</strong>` },
      { key: "rfc_proveedor", label: "RFC", render: (r) => `<span class="badge-mini">${r.rfc_proveedor || "—"}</span>` },
      { key: "total_contratos", label: "Contratos", num: true, render: (r) => fmtInt(r.total_contratos) },
      { key: "monto_total_acumulado", label: "Monto Total", num: true, render: (r) => `<strong>${fmtMoney(r.monto_total_acumulado)}</strong>` },
      { key: "porcentaje_del_gasto_total", label: "% Nacional", num: true, render: (r) => `${r.porcentaje_del_gasto_total}%` },
    ],
    searchFields: ["proveedor_nombre", "rfc_proveedor"],
  },
  viaticosOutliers: {
    defaultSort: { key: "importe_total_erogado", dir: "desc" },
    columns: [
      { key: "ciudad_destino", label: "Destino", render: (r) => `<strong>${r.ciudad_destino}</strong>, ${r.estado_destino}` },
      { key: "cargo", label: "Cargo", render: (r) => r.cargo },
      { key: "area_adscripcion", label: "Área", render: (r) => r.area_adscripcion },
      { key: "importe_total_erogado", label: "Importe", num: true, render: (r) => `<strong>${fmtExactMXN(r.importe_total_erogado)}</strong>` },
      { key: "veces_promedio", label: "Vs. Promedio", num: true, render: (r) => `<span class="badge-alert">${r.veces_promedio}x promedio</span>` },
    ],
    searchFields: ["ciudad_destino", "estado_destino", "cargo", "area_adscripcion"],
  },
  puestos: {
    defaultSort: { key: "sueldo_bruto_promedio", dir: "desc" },
    columns: [
      { key: "denominacion_puesto", label: "Denominación", render: (r) => `<span class="badge-mini">${r.denominacion_puesto}</span>` },
      { key: "cargo", label: "Cargo (2025)", render: (r) => r.cargo },
      { key: "total_plazas_reportadas", label: "Plazas", num: true, render: (r) => fmtInt(r.total_plazas_reportadas) },
      { key: "sueldo_bruto_promedio", label: "Bruto Mensual", num: true, render: (r) => fmtExactMXN(r.sueldo_bruto_promedio) },
      { key: "sueldo_neto_promedio", label: "Neto Mensual", num: true, render: (r) => `<strong>${fmtExactMXN(r.sueldo_neto_promedio)}</strong>` },
    ],
    searchFields: ["denominacion_puesto", "cargo"],
  },
};

function renderExplorerTable() {
  const schema = EXPLORER_SCHEMAS[state.explorerTable];
  const rawList = state.explorerTable === "puestos" ? state.data.salarios || [] : state.data[state.explorerTable] || [];
  const q = (document.getElementById("explorer-search")?.value || "").trim().toLowerCase();

  const sortKey = state.explorerSortKey || schema.defaultSort.key;
  const sortDir = state.explorerSortKey ? state.explorerSortDir : schema.defaultSort.dir;

  const filtered = rawList.filter((r) => {
    if (!q) return true;
    return schema.searchFields.some((f) => String(r[f] ?? "").toLowerCase().includes(q));
  });

  const sorted = [...filtered].sort((a, b) => {
    const va = a[sortKey];
    const vb = b[sortKey];
    if (va === vb) return 0;
    if (va === null || va === undefined) return 1;
    if (vb === null || vb === undefined) return -1;
    const cmp = typeof va === "number" && typeof vb === "number"
      ? va - vb
      : String(va).localeCompare(String(vb), "es", { numeric: true });
    return sortDir === "asc" ? cmp : -cmp;
  });

  const totalItems = sorted.length;
  const totalPages = Math.max(1, Math.ceil(totalItems / state.explorerPageSize));
  state.explorerPage = Math.max(1, Math.min(state.explorerPage, totalPages));

  const startIdx = (state.explorerPage - 1) * state.explorerPageSize;
  const pageRows = sorted.slice(startIdx, startIdx + state.explorerPageSize);

  const thead = document.querySelector("#explorer-table thead");
  const tbody = document.querySelector("#explorer-table tbody");

  thead.innerHTML = `<tr>${schema.columns
    .map((c) => {
      const isSorted = sortKey === c.key;
      const arrow = isSorted ? (sortDir === "asc" ? "▲" : "▼") : "⇅";
      return `<th class="sortable ${c.num ? "num" : ""} ${isSorted ? "sorted" : ""}" data-sort-key="${c.key}">${c.label}<span class="sort-arrow">${arrow}</span></th>`;
    })
    .join("")}</tr>`;

  thead.querySelectorAll("th.sortable").forEach((th) => {
    th.addEventListener("click", () => {
      const key = th.dataset.sortKey;
      if (state.explorerSortKey === key) {
        state.explorerSortDir = state.explorerSortDir === "asc" ? "desc" : "asc";
      } else {
        state.explorerSortKey = key;
        state.explorerSortDir = th.classList.contains("num") ? "desc" : "asc";
      }
      state.explorerPage = 1;
      renderExplorerTable();
    });
  });

  tbody.innerHTML = pageRows.length
    ? pageRows
        .map((r) => `<tr>${schema.columns.map((c, idx) => `<td class="${c.num ? "num" : ""} ${idx === 1 ? "cell-primary" : ""}" data-label="${c.label}">${c.render(r)}</td>`).join("")}</tr>`)
        .join("")
    : `<tr><td colspan="${schema.columns.length}" style="text-align:center;color:var(--text-muted);padding:28px;">No se encontraron resultados para "${q}"</td></tr>`;

  const infoEl = document.getElementById("pagination-info");
  const indEl = document.getElementById("page-indicator");
  const prevBtn = document.getElementById("btn-prev-page");
  const nextBtn = document.getElementById("btn-next-page");

  const showFrom = totalItems === 0 ? 0 : startIdx + 1;
  const showTo = Math.min(totalItems, startIdx + state.explorerPageSize);
  if (infoEl) infoEl.textContent = `Mostrando ${fmtInt(showFrom)}–${fmtInt(showTo)} de ${fmtInt(totalItems)} registros`;
  if (indEl) indEl.textContent = `Página ${state.explorerPage} / ${totalPages}`;
  if (prevBtn) prevBtn.disabled = state.explorerPage <= 1;
  if (nextBtn) nextBtn.disabled = state.explorerPage >= totalPages;
}

// ==================== EMBED MODAL (SOLO GRÁFICA LIMPIA) ====================
function updateEmbedSnippet(stepVal) {
  const src = `${window.location.origin}${window.location.pathname}?embed=chart&step=${stepVal}`;
  document.getElementById("embed-code").value = `<iframe src="${src}" width="100%" height="560" style="border:none;border-radius:14px;background:#080808;overflow:hidden;" scrolling="no" loading="lazy"></iframe>`;
  document.getElementById("copy-feedback").textContent = "";
}

function openEmbedModal(stepVal) {
  const sel = document.getElementById("embed-chapter-select");
  sel.value = String(stepVal);
  updateEmbedSnippet(stepVal);
  document.getElementById("embed-modal").hidden = false;
}

function wireUI() {
  document.querySelectorAll("#explorer-switch .seg-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#explorer-switch .seg-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      state.explorerTable = btn.dataset.table;
      state.explorerPage = 1;
      state.explorerSortKey = null;
      renderExplorerTable();
    });
  });

  document.getElementById("explorer-search")?.addEventListener("input", () => {
    state.explorerPage = 1;
    renderExplorerTable();
  });

  document.getElementById("btn-prev-page")?.addEventListener("click", () => {
    if (state.explorerPage > 1) {
      state.explorerPage -= 1;
      renderExplorerTable();
    }
  });

  document.getElementById("btn-next-page")?.addEventListener("click", () => {
    state.explorerPage += 1;
    renderExplorerTable();
  });

  document.getElementById("btn-descargar-tabla")?.addEventListener("click", () => {
    const rawList = state.explorerTable === "puestos" ? state.data.salarios || [] : state.data[state.explorerTable] || [];
    if (!rawList.length) return;
    const keys = Object.keys(rawList[0]);
    const csvLines = [
      keys.join(","),
      ...rawList.map((row) =>
        keys
          .map((k) => {
            const val = row[k] ?? "";
            const str = String(val).replace(/"/g, '""');
            return `"${str}"`;
          })
          .join(",")
      ),
    ];
    const blob = new Blob([csvLines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ine_${state.explorerTable}_agil.csv`;
    a.click();
    URL.revokeObjectURL(url);
  });
  document.getElementById("btn-embed-current")?.addEventListener("click", () => openEmbedModal(Math.max(0, state.activeStep)));
  document.getElementById("embed-chapter-select")?.addEventListener("change", (e) => updateEmbedSnippet(e.target.value));

  // Modal de descarga B2 (Capa Plata)
  const vaultModal = document.getElementById("vault-modal");
  document.getElementById("btn-open-vault")?.addEventListener("click", async () => {
    if (vaultModal) {
      vaultModal.hidden = false;
      const tbody = document.querySelector("#vault-download-table tbody");
      if (!tbody.children.length) {
        try {
          const resp = await fetch("./catalogo_descargas_b2.json");
          const items = await resp.json();
          tbody.innerHTML = items
            .map(
              (item) => `<tr>
                <td><span class="badge-mini">${item.dominio}</span></td>
                <td><strong>${item.archivo}</strong></td>
                <td class="num">${typeof item.tamano_mb === "number" ? item.tamano_mb + " MB" : item.tamano_mb}</td>
                <td class="num"><a class="btn-gold btn-sm" href="${item.url}" target="_blank" rel="noopener noreferrer">Descargar</a></td>
              </tr>`
            )
            .join("");
        } catch {
          tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:20px;">Cargando catálogo...</td></tr>`;
        }
      }
    }
  });

  document.getElementById("vault-modal-close")?.addEventListener("click", () => {
    if (vaultModal) vaultModal.hidden = true;
  });
  vaultModal?.addEventListener("click", (e) => {
    if (e.target.id === "vault-modal") vaultModal.hidden = true;
  });

  document.getElementById("modal-close")?.addEventListener("click", () => (document.getElementById("embed-modal").hidden = true));
  document.getElementById("embed-modal")?.addEventListener("click", (e) => {
    if (e.target.id === "embed-modal") e.target.hidden = true;
  });
  document.getElementById("btn-copy-embed")?.addEventListener("click", async () => {
    await navigator.clipboard.writeText(document.getElementById("embed-code").value);
    document.getElementById("copy-feedback").textContent = "✓ Copiado al portapapeles";
  });

  window.addEventListener("keydown", (e) => {
    if (e.key !== "Escape") return;
    const vault = document.getElementById("vault-modal");
    const embed = document.getElementById("embed-modal");
    if (vault && !vault.hidden) {
      vault.hidden = true;
      return;
    }
    if (embed && !embed.hidden) {
      embed.hidden = true;
      return;
    }
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ type: "AGIL_CLOSE_MODAL" }, "*");
    }
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 980) {
      ensureDesktopChart();
      if (state.stageChart) state.stageChart.resize();
    } else {
      prepareMobileChartBoxes();
      if (state.dataReady) activateMobileCharts();
      (state.mobileCharts || []).forEach((c) => c.resize());
    }
  });
}

function createSkeletonMarkup() {
  return `
    <div class="chart-skeleton" aria-label="Cargando gráfica">
      <div class="sk-bars">
        <span class="sk-bar" style="height:42%"></span>
        <span class="sk-bar" style="height:78%"></span>
        <span class="sk-bar" style="height:56%"></span>
        <span class="sk-bar" style="height:90%"></span>
        <span class="sk-bar" style="height:64%"></span>
      </div>
      <span class="sk-label">Cargando visualización...</span>
    </div>
  `;
}

function ensureDesktopChart() {
  if (state.stageChart || typeof echarts === "undefined") return;
  const chartEl = document.getElementById("main-stage-chart");
  if (!chartEl) return;
  if (window.innerWidth <= 980 && !document.body.classList.contains("is-embed-chart")) return;
  state.stageChart = echarts.init(chartEl, null, { renderer: "canvas" });
  if (typeof ResizeObserver !== "undefined") {
    new ResizeObserver(() => state.stageChart && state.stageChart.resize()).observe(chartEl);
  }
  if (state.dataReady) renderStep(Math.max(0, state.activeStep));
}

function prepareMobileChartBoxes() {
  if (window.innerWidth > 980) return;
  document.querySelectorAll(".story-step").forEach((stepEl) => {
    if (stepEl.dataset.mobileBox === "1") return;
    stepEl.dataset.mobileBox = "1";

    const box = document.createElement("div");
    box.className = "mobile-stage-box";
    box.innerHTML = `
      <div class="mobile-stage-controls"></div>
      <div class="mobile-stage-chart">${createSkeletonMarkup()}</div>
      <div class="mobile-stage-source"></div>
    `;
    stepEl.appendChild(box);
  });
}

function activateMobileCharts() {
  if (window.innerWidth > 980 || typeof echarts === "undefined") return;
  if (!state.mobileCharts) state.mobileCharts = [];

  document.querySelectorAll(".story-step").forEach((stepEl) => {
    const stepIndex = Number(stepEl.dataset.step);
    const box = stepEl.querySelector(".mobile-stage-box");
    if (!box) return;
    const controlsEl = box.querySelector(".mobile-stage-controls");
    const chartDiv = box.querySelector(".mobile-stage-chart");
    const sourceEl = box.querySelector(".mobile-stage-source");
    if (!chartDiv || chartDiv.dataset.rendered === "1") return;

    const initThisChart = () => {
      if (chartDiv.dataset.rendered === "1") return;
      chartDiv.dataset.rendered = "1";
      chartDiv.innerHTML = "";
      requestAnimationFrame(() => {
        const mobileChart = echarts.init(chartDiv, null, { renderer: "canvas" });
        state.mobileCharts.push(mobileChart);
        renderStep(stepIndex, { chart: mobileChart, controlsEl, sourceEl });
        if (typeof ResizeObserver !== "undefined") {
          new ResizeObserver(() => mobileChart.resize()).observe(chartDiv);
        }
      });
    };

    if (typeof IntersectionObserver !== "undefined") {
      const io = new IntersectionObserver(
        (entries) => {
          if (entries.some((e) => e.isIntersecting)) {
            initThisChart();
            io.disconnect();
          }
        },
        { rootMargin: "0px 0px -30px 0px", threshold: 0.15 }
      );
      io.observe(chartDiv);
    } else {
      initThisChart();
    }
  });
}

// ==================== BOOTSTRAP ====================
(async function main() {
  const params = new URLSearchParams(window.location.search);
  const embedMode = params.get("embed");
  const requestedStep = params.has("step") ? Number(params.get("step")) : null;

  // Modo embed limpio de una sola gráfica (sin scroll ni texto superpuesto)
  if (embedMode === "chart" || (embedMode === "true" && requestedStep !== null)) {
    document.body.classList.add("is-embed-chart");
  } else if (embedMode === "true") {
    document.body.classList.add("is-embed-full");
  }

  wireUI();
  setupWikiTooltips();

  // Mostrar skeletons inmediatamente antes de descargar datos
  if (!document.body.classList.contains("is-embed-chart")) {
    prepareMobileChartBoxes();
  }

  const chartEl = document.getElementById("main-stage-chart");
  const stageWrap = chartEl?.parentElement;
  let desktopLoader = null;
  if (stageWrap && (window.innerWidth > 980 || document.body.classList.contains("is-embed-chart"))) {
    desktopLoader = document.createElement("div");
    desktopLoader.innerHTML = createSkeletonMarkup();
    stageWrap.appendChild(desktopLoader.firstElementChild);
    desktopLoader = stageWrap.querySelector(".chart-skeleton");
  }

  ensureDesktopChart();

  await Promise.allSettled([initDataEngine(), loadMexicoGeo(), ...DATA_TABLES.map((item) => loadTable(item))]);
  state.dataReady = true;
  if (desktopLoader) desktopLoader.remove();

  const initialStep = requestedStep !== null && !Number.isNaN(requestedStep) ? Math.max(0, Math.min(8, requestedStep)) : 0;
  if (state.stageChart) renderStep(initialStep);

  if (!document.body.classList.contains("is-embed-chart")) {
    setupParallaxAndProgress();
    setupScrollyObserver();
    activateMobileCharts();
    renderExplorerTable();
  }
})();
