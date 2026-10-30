import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

const DATA_PATHS = {
  municipality: "/outputs/resultadosIntegrados/ccpc_municipioResultadosIntegrados.csv",
  sectionsSummary: "/outputs/resultadosIntegrados/seccionesPorEntidad.json",
};

/**
 * Robust CSV parser that correctly handles escaped quotes, multi-line values, and whitespace.
 */
function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];

    if (char === '"' && quoted && next === '"') {
      cell += '"';
      i += 1;
      continue;
    }
    if (char === '"') {
      quoted = !quoted;
      continue;
    }
    if (char === "," && !quoted) {
      row.push(cell);
      cell = "";
      continue;
    }
    if ((char === "\n" || char === "\r") && !quoted) {
      if (char === "\r" && next === "\n") i += 1;
      row.push(cell);
      if (row.some(Boolean)) rows.push(row);
      row = [];
      cell = "";
      continue;
    }
    cell += char;
  }
  if (cell || row.length) {
    row.push(cell);
    if (row.some(Boolean)) rows.push(row);
  }
  if (!rows.length) return [];
  const headers = rows.shift().map((header) => header.replace(/^\uFEFF/, "").trim());
  return rows.map((values) =>
    Object.fromEntries(headers.map((header, i) => [header, (values[i] ?? "").trim()]))
  );
}

/**
 * Safe numeric parser that strictly distinguishes empty strings/nulls from 0.
 * In standard JavaScript, Number("") evaluates to 0, which previously caused missing risk scores
 * to be treated as 0.0 and corrupted territorial averages.
 */
const numberOrNull = (value) => {
  if (value === null || value === undefined) return null;
  const str = String(value).trim();
  if (str === "") return null;
  const parsed = Number(str);
  return Number.isFinite(parsed) ? parsed : null;
};

const n = (value) => numberOrNull(value) ?? 0;

const pct = (value) => {
  const val = numberOrNull(value);
  if (val === null) return "Sin dato";
  return `${(val * 100).toFixed(1)}%`;
};

const fmt = (value) => new Intl.NumberFormat("es-MX").format(n(value));

const avg = (rows, key) => {
  const values = rows.map((row) => numberOrNull(row[key])).filter((v) => v !== null);
  if (!values.length) return null;
  return values.reduce((sum, v) => sum + v, 0) / values.length;
};

const riskValue = (row) => numberOrNull(row.risk_score);

const riskLabel = (row) => {
  const level = String(row.risk_level || "").toLowerCase().trim();
  if (level === "alto" || level === "medio" || level === "bajo") return level;
  return "sin_historico";
};

const riskDisplayLabel = (level) => {
  const map = {
    alto: "Alto",
    medio: "Medio",
    bajo: "Bajo",
    sin_historico: "Sin histórico",
  };
  return map[level] || level;
};

const riskText = (row) => {
  const val = riskValue(row);
  return val === null ? "Sin dato" : val.toFixed(1);
};

const unique = (rows, key) =>
  [...new Set(rows.map((row) => row[key]).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b, "es")
  );

function Card({ label, value, meta, hint, tag, alertLevel }) {
  return (
    <article className={`card kpi ${alertLevel ? `kpi-alert-${alertLevel}` : ""}`} title={hint || meta}>
      <div className="kpi-top">
        <span className="kpi-label">{label}</span>
        {tag && <span className="kpi-tag">{tag}</span>}
      </div>
      <strong className="kpi-value">{value}</strong>
      <span className="kpi-meta">{meta}</span>
    </article>
  );
}

function Panel({ title, kicker, description, children, className = "", extraAction }) {
  return (
    <article className={`card panel-card ${className}`}>
      <div className="section-head">
        <div>
          {kicker && <div className="panel-kicker">{kicker}</div>}
          <h2>{title}</h2>
          {description && <p>{description}</p>}
        </div>
        {extraAction && <div className="panel-extra-action">{extraAction}</div>}
      </div>
      {children}
    </article>
  );
}

function Pill({ value }) {
  const key = String(value || "sin_historico").toLowerCase().replaceAll(" ", "_");
  return (
    <span className={`pill ${key}`}>
      {riskDisplayLabel(key)}
    </span>
  );
}

/**
 * Chart A: Distribución de municipios por nivel de riesgo
 * Categorías: bajo, medio, alto (con referencia a sin_historico)
 * Gráfico: Barras verticales con colores institucionales
 */
function RiskDistribution({ items, totalClassified, withoutHistoryCount, totalMunicipalities, selected, onSelect }) {
  const max = Math.max(...items.map((item) => n(item.value)), 1);

  return (
    <div className="risk-chart-wrapper">
      <div className="risk-chart" role="region" aria-label="Distribución de municipios por nivel de riesgo">
        {items.map((item) => {
          const isSelected = selected === item.label;
          const heightPercent = Math.max(12, (n(item.value) / max) * 160);
          return (
            <button
              type="button"
              className={`risk-column ${item.label} ${isSelected ? "selected" : ""}`}
              key={item.label}
              aria-pressed={isSelected}
              onClick={() => onSelect(isSelected ? "todos" : item.label)}
              title={`Filtrar municipios con riesgo ${riskDisplayLabel(item.label)}: ${fmt(item.value)} municipios (${item.percent.toFixed(1)}%)`}
            >
              <span className="risk-column-value">{fmt(item.value)}</span>
              <div className="risk-column-track">
                <span
                  className={`risk-column-bar ${item.label}`}
                  style={{ height: `${heightPercent}px` }}
                />
              </div>
              <span className="risk-column-label">
                <span className={`risk-color-dot ${item.label}`} />
                {riskDisplayLabel(item.label)}
              </span>
              <small className="risk-column-pct">{item.percent.toFixed(1)}%</small>
            </button>
          );
        })}
      </div>

      <div className="risk-chart-notes">
        <div className="risk-legend-info">
          <span>
            <strong>Base evaluada con histórico:</strong> {fmt(totalClassified)} municipios ({((totalClassified / totalMunicipalities) * 100).toFixed(1)}% del territorio).
          </span>
          {withoutHistoryCount > 0 && (
            <span className="unclassified-note">
              <strong>Sin histórico suficiente:</strong> {fmt(withoutHistoryCount)} municipios ({((withoutHistoryCount / totalMunicipalities) * 100).toFixed(1)}%), principalmente municipios bajo sistemas normativos indígenas con menor serie temporal en CCPC.
            </span>
          )}
        </div>
        {selected !== "todos" && (
          <button
            type="button"
            className="btn-reset-filter"
            onClick={() => onSelect("todos")}
          >
            Quitar filtro de riesgo (mostrando: {riskDisplayLabel(selected)})
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * Chart C: Riesgo promedio por entidad federativa
 * Eje: entidad · Valor: promedio de risk_score · Orden descendente
 */
function EntityRankingChart({ groups, selectedEntity, onSelectEntity }) {
  const [showAll, setShowAll] = useState(false);
  const maxScore = Math.max(...groups.map((g) => g.score), 100);

  const displayedGroups = showAll ? groups : groups.slice(0, 10);
  const selectedRank = groups.findIndex((g) => g.label === selectedEntity) + 1;
  const selectedData = groups.find((g) => g.label === selectedEntity);

  return (
    <div className="entity-ranking-container">
      <div className="entity-ranking-actions">
        <div className="ranking-badge-status">
          {selectedEntity ? (
            <span>
              <strong>{selectedEntity}:</strong> Posición <b>#{selectedRank}</b> de {groups.length} entidades ({selectedData ? selectedData.score.toFixed(1) : 0} pts promedio)
            </span>
          ) : (
            <span>Promedio nacional de entidades ordenadas de mayor a menor riesgo</span>
          )}
        </div>
        <button
          type="button"
          className="btn-toggle-ranking"
          onClick={() => setShowAll((prev) => !prev)}
        >
          {showAll ? "Ver solo Top 10" : `Ver las ${groups.length} entidades`}
        </button>
      </div>

      <div className="bars" role="region" aria-label="Ranking de riesgo promedio por entidad">
        {displayedGroups.map((group, index) => {
          const isSelected = selectedEntity === group.label;
          const rankNumber = String(index + 1).padStart(2, "0");
          const widthPct = Math.max(5, (group.score / maxScore) * 100);

          let barColor = "var(--risk-low)";
          if (group.score >= 60) barColor = "var(--risk-high)";
          else if (group.score >= 40) barColor = "var(--risk-medium)";

          return (
            <div
              className={`bar-row ${isSelected ? "highlight-state" : ""}`}
              key={group.label}
              onClick={() => onSelectEntity(isSelected ? "" : group.label)}
              title={`Hacer clic para enfocar en ${group.label}. Riesgo promedio: ${group.score.toFixed(1)} / 100`}
            >
              <div className="bar-label-group">
                <span className="bar-rank">{rankNumber}</span>
                <span className="bar-state-name" title={group.label}>
                  {group.label}
                </span>
              </div>
              <div
                className="track"
                aria-label={`${group.label}: ${group.score.toFixed(1)} puntos`}
              >
                <b style={{ width: `${widthPct}%`, backgroundColor: barColor }} />
              </div>
              <strong className="bar-value">{group.score.toFixed(1)}</strong>
            </div>
          );
        })}
      </div>

      <p className="chart-reading">
        <strong>Pregunta que responde:</strong> ¿Qué entidades concentran los puntajes promedio más altos?{" "}
        <span className="text-muted">
          Puntaje de 0 a 100 calculado exclusivamente sobre municipios con histórico medido. Un puntaje elevado refleja alta abstención reciente, pendiente negativa y volatilidad.
        </span>
      </p>
    </div>
  );
}

/**
 * Chart B: Top 10 municipios con mayor riesgo
 * Requisitos:
 * Mostrar: entidad, municipio, risk_score, risk_level, latest_abstention, latest_participation, participation_slope, risk_reason.
 * Pregunta: ¿Qué municipios deben considerarse prioritarios?
 */
function PriorityTable({ rows, selectedRiskFilter }) {
  const [selectedKey, setSelectedKey] = useState("");

  const activeKey = useMemo(() => {
    if (!rows.length) return "";
    const exists = rows.some((row) => `${row.EDOCVE}-${row.MPIOCVE}` === selectedKey);
    return exists ? selectedKey : `${rows[0].EDOCVE}-${rows[0].MPIOCVE}`;
  }, [rows, selectedKey]);

  const selected = useMemo(() => {
    return rows.find((row) => `${row.EDOCVE}-${row.MPIOCVE}` === activeKey) || rows[0] || null;
  }, [rows, activeKey]);

  if (!rows.length) {
    return (
      <div className="empty-state">
        <p>No se encontraron municipios con los filtros seleccionados.</p>
      </div>
    );
  }

  return (
    <div className="priority-table-section">
      <div className="priority-table-wrap">
        <table className="priority-table" aria-label="Top municipios prioritarios con mayor riesgo">
          <thead>
            <tr>
              <th scope="col" className="col-num">#</th>
              <th scope="col" className="col-territory">Municipio / Entidad</th>
              <th scope="col" className="col-risk">Riesgo (0–100)</th>
              <th scope="col" className="col-level">Nivel</th>
              <th scope="col" className="col-stat" title="latest_abstention: Porcentaje de abstención en el proceso electoral más reciente">Abstención</th>
              <th scope="col" className="col-stat" title="latest_participation: Porcentaje de participación ciudadana en 2024">Participación</th>
              <th scope="col" className="col-slope" title="participation_slope: Tendencia anual de cambio en la participación">Pendiente anual</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => {
              const key = `${row.EDOCVE}-${row.MPIOCVE}`;
              const isSelected = activeKey === key;
              const slopeVal = numberOrNull(row.participation_slope);
              const isNegativeSlope = slopeVal !== null && slopeVal < 0;

              return (
                <tr
                  key={key}
                  className={`priority-row ${isSelected ? "selected" : ""}`}
                  onClick={() => setSelectedKey(key)}
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      setSelectedKey(key);
                    }
                  }}
                  title={`Seleccionar ${row.MPIONOM} (${row.EDONOM}) para ver diagnóstico detallado`}
                >
                  <td className="col-num">
                    <span className="priority-number">{String(index + 1).padStart(2, "0")}</span>
                  </td>
                  <td className="col-territory">
                    <strong>{row.MPIONOM || "Sin nombre"}</strong>
                    <small>{row.EDONOM}</small>
                  </td>
                  <td className="col-risk">
                    <strong className="risk-score-value">{riskText(row)}</strong>
                  </td>
                  <td className="col-level">
                    <Pill value={riskLabel(row)} />
                  </td>
                  <td className="col-stat">{pct(row.latest_abstention)}</td>
                  <td className="col-stat">{pct(row.latest_participation)}</td>
                  <td className="col-slope">
                    <span className={isNegativeSlope ? "negative-trend" : "positive-trend"}>
                      {slopeVal === null
                        ? "Sin dato"
                        : `${slopeVal < 0 ? "▼" : "▲"} ${(slopeVal * 100).toFixed(2)}% pts/año`}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {selected && (
        <div className="priority-detail-card" aria-live="polite">
          <div className="priority-detail-header">
            <div>
              <span className="detail-eyebrow">Detalle del municipio prioritario seleccionado</span>
              <h3 className="detail-title">
                {selected.MPIONOM} <span className="detail-state">({selected.EDONOM})</span>
              </h3>
            </div>
            <div className="detail-header-risk">
              <span className="detail-score-label">Puntaje de riesgo</span>
              <div className="detail-score-badge">
                <strong>{riskText(selected)}</strong> / 100
                <Pill value={riskLabel(selected)} />
              </div>
            </div>
          </div>

          <div className="priority-detail-metrics">
            <div className="metric-box">
              <span className="metric-box-label">Abstención reciente (2024)</span>
              <strong className="metric-box-val">{pct(selected.latest_abstention)}</strong>
              <small>latest_abstention</small>
            </div>
            <div className="metric-box">
              <span className="metric-box-label">Participación reciente (2024)</span>
              <strong className="metric-box-val">{pct(selected.latest_participation)}</strong>
              <small>latest_participation</small>
            </div>
            <div className="metric-box">
              <span className="metric-box-label">Tendencia histórica</span>
              <strong
                className={`metric-box-val ${
                  n(selected.participation_slope) < 0 ? "negative-trend" : "positive-trend"
                }`}
              >
                {numberOrNull(selected.participation_slope) !== null
                  ? `${(n(selected.participation_slope) * 100).toFixed(2)}% anual`
                  : "N/D"}
              </strong>
              <small>participation_slope</small>
            </div>
            <div className="metric-box">
              <span className="metric-box-label">Lista nominal reciente</span>
              <strong className="metric-box-val">{fmt(selected.latest_ln)}</strong>
              <small>Ciudadanos registrados</small>
            </div>
          </div>

          <div className="priority-detail-explanation">
            <div className="explanation-title">
              <span className="icon-alert">⚠️</span>
              <strong>Diagnóstico institucional explicable (risk_reason):</strong>
            </div>
            <p className="explanation-text">
              {selected.risk_reason ||
                "Sin factores críticos específicos registrados en la serie histórica."}
            </p>
            <div className="explanation-footer">
              <b>Uso operativo para el INE / DECEYEC:</b> Este municipio presenta señales convergentes que justifican priorizar módulos itinerantes de actualización del padrón y campañas focales de educación cívica (ENCÍVICA) dirigidas a revertir la abstención.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Custom hook to load dataset safely
 */
function useDataset(key, parseAsCsv = true) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");

    fetch(DATA_PATHS[key])
      .then((response) => {
        if (!response.ok) throw new Error(`No se pudo cargar ${DATA_PATHS[key]}`);
        return parseAsCsv ? response.text() : response.json();
      })
      .then((payload) => {
        if (active) {
          setData(parseAsCsv ? parseCsv(payload) : payload);
        }
      })
      .catch((err) => {
        console.error(err);
        if (active) setError(err.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [key, parseAsCsv]);

  return { data, loading, error };
}

/**
 * Main Overview (Página 1: Resumen Ejecutivo)
 */
function ExecutiveSummary({
  allMunicipalities,
  selectedEntity,
  onEntityChange,
  sectionsSummary,
}) {
  const [riskFilter, setRiskFilter] = useState("todos");

  // Filter by entity
  const entityMunicipalities = useMemo(() => {
    if (!selectedEntity) return allMunicipalities;
    return allMunicipalities.filter((m) => m.EDONOM === selectedEntity);
  }, [allMunicipalities, selectedEntity]);

  // Filter by risk (for table and drill-down)
  const filteredMunicipalities = useMemo(() => {
    if (riskFilter === "todos") return entityMunicipalities;
    return entityMunicipalities.filter((m) => riskLabel(m) === riskFilter);
  }, [entityMunicipalities, riskFilter]);

  // National / Entity entity-level rankings for Chart C
  // Calculated across allMunicipalities to ensure clean comparison even when an entity is selected
  const entityGroups = useMemo(() => {
    const groups = {};
    allMunicipalities.forEach((row) => {
      const score = riskValue(row);
      const edo = row.EDONOM;
      if (!edo) return;
      groups[edo] ||= { label: edo, scoreSum: 0, countWithScore: 0, total: 0, altoCount: 0 };
      groups[edo].total += 1;
      if (row.risk_level === "alto") groups[edo].altoCount += 1;
      if (score !== null) {
        groups[edo].scoreSum += score;
        groups[edo].countWithScore += 1;
      }
    });

    return Object.values(groups)
      .map((g) => ({
        label: g.label,
        total: g.total,
        countWithScore: g.countWithScore,
        score: g.countWithScore > 0 ? g.scoreSum / g.countWithScore : 0,
        altoPct: (g.altoCount / g.total) * 100,
      }))
      .sort((a, b) => b.score - a.score);
  }, [allMunicipalities]);

  // Top 10 priority municipalities
  const topPriority = useMemo(() => {
    const scored = filteredMunicipalities.filter((r) => riskValue(r) !== null);
    return [...scored].sort((a, b) => (riskValue(b) ?? 0) - (riskValue(a) ?? 0)).slice(0, 10);
  }, [filteredMunicipalities]);

  // Breakdown for Chart A
  const classifiedInScope = useMemo(() => {
    return entityMunicipalities.filter((row) => ["bajo", "medio", "alto"].includes(row.risk_level));
  }, [entityMunicipalities]);

  const withoutHistoryInScope = entityMunicipalities.length - classifiedInScope.length;
  const totalClassified = classifiedInScope.length || 1;

  const distributionCounts = useMemo(() => {
    return ["bajo", "medio", "alto"].map((level) => {
      const value = classifiedInScope.filter((row) => row.risk_level === level).length;
      return {
        label: level,
        value,
        percent: (value / totalClassified) * 100,
      };
    });
  }, [classifiedInScope, totalClassified]);

  // Total sections in current scope (from sectionsSummary JSON or safe fallback)
  const sectionsInScope = useMemo(() => {
    if (!sectionsSummary) return selectedEntity ? "…" : "70,751";
    if (selectedEntity) {
      const count = sectionsSummary.byEntity?.[selectedEntity];
      return count ? fmt(count) : "…";
    }
    return fmt(sectionsSummary.total || 70751);
  }, [sectionsSummary, selectedEntity]);

  // Key KPI values
  const totalEvaluated = entityMunicipalities.length;
  const highRiskCount = entityMunicipalities.filter((r) => r.risk_level === "alto").length;
  const highRiskPercent = classifiedInScope.length
    ? ((highRiskCount / classifiedInScope.length) * 100).toFixed(1)
    : "0.0";
  const recentAbstentionAvg = avg(entityMunicipalities, "latest_abstention");
  const recentParticipationAvg = avg(entityMunicipalities, "latest_participation");
  const riskScoreAvg = avg(entityMunicipalities, "risk_score");
  const decliningCount = entityMunicipalities.filter(
    (r) => numberOrNull(r.declining_participation) !== null && n(r.declining_participation) > 0
  ).length;
  const trendReliableCount = entityMunicipalities.filter(
    (r) => String(r.trend_reliable).toLowerCase() === "true"
  ).length;

  return (
    <div className="executive-summary-wrapper">
      {/* 8 Indicadores Principales */}
      <section className="section-block" id="indicadores-principales">
        <div className="section-header-row">
          <div>
            <div className="section-kicker">01 / Métricas Clave</div>
            <h2 className="section-heading">Indicadores principales</h2>
            <p className="section-subheading">
              {selectedEntity
                ? `Métricas para ${selectedEntity} · Alcance territorial focalizado`
                : "Panorama general a nivel nacional con datos censales del CCPC 2009–2024"}
            </p>
          </div>
          {riskFilter !== "todos" && (
            <div className="filter-badge-banner">
              Filtro activo en tabla: <b>Riesgo {riskDisplayLabel(riskFilter)}</b>
              <button
                type="button"
                className="btn-clear-pill"
                onClick={() => setRiskFilter("todos")}
              >
                ✕ Ver todos
              </button>
            </div>
          )}
        </div>

        <div className="grid kpi-grid">
          <Card
            label="1. Municipios evaluados"
            value={fmt(totalEvaluated)}
            meta={selectedEntity ? selectedEntity : "Total nacional (2,477)"}
            hint="Total de municipios incorporados en el análisis territorial."
          />
          <Card
            label="2. Secciones evaluadas"
            value={sectionsInScope}
            meta={selectedEntity ? `Secciones en ${selectedEntity}` : "Nivel nacional (~71,000)"}
            hint="Granularidad básica de organización electoral de las casillas."
          />
          <Card
            label="3. Municipios en riesgo alto"
            value={fmt(highRiskCount)}
            meta={`${highRiskPercent}% de los evaluados con histórico`}
            hint="Municipios prioritarios con alta abstención y señales de deterioro."
            alertLevel="high"
          />
          <Card
            label="4. Abstención promedio reciente"
            value={recentAbstentionAvg !== null ? pct(recentAbstentionAvg) : "Sin dato"}
            meta="Campo: latest_abstention · Elección 2024"
            hint="Proporción promedio de lista nominal que no acudió a votar en 2024."
          />
          <Card
            label="5. Participación promedio reciente"
            value={recentParticipationAvg !== null ? pct(recentParticipationAvg) : "Sin dato"}
            meta="Campo: latest_participation · Elección 2024"
            hint="Proporción promedio de lista nominal que emitió su voto en 2024."
          />
          <Card
            label="6. Puntaje promedio de riesgo"
            value={riskScoreAvg !== null ? riskScoreAvg.toFixed(1) : "Sin dato"}
            meta="Campo: risk_score · Escala 0 a 100"
            hint="Índice compuesto institucional que pondera abstención, tendencia e inestabilidad."
          />
          <Card
            label="7. Municipios con participación descendente"
            value={fmt(decliningCount)}
            meta="Campo: declining_participation (>0)"
            hint="Municipios donde la participación ha sufrido caída sistemática a lo largo de los ciclos."
            alertLevel={decliningCount > 0 ? "medium" : undefined}
          />
          <Card
            label="8. Municipios con histórico confiable"
            value={fmt(trendReliableCount)}
            meta="Campo: trend_reliable · 3+ elecciones"
            hint="Municipios con suficiente serie temporal para estimar tendencias estadísticas confiables."
          />
        </div>
      </section>

      {/* Gráficas A y C */}
      <section className="section-block" id="graficas-distribucion-entidades">
        <div className="grid two-col">
          {/* Gráfica A */}
          <Panel
            kicker="Gráfica A"
            title="Distribución de municipios por nivel de riesgo"
            description="¿Qué proporción de los municipios presenta cada nivel de riesgo? (Haz clic en una barra para filtrar la tabla)"
          >
            <RiskDistribution
              items={distributionCounts}
              totalClassified={classifiedInScope.length}
              withoutHistoryCount={withoutHistoryInScope}
              totalMunicipalities={entityMunicipalities.length}
              selected={riskFilter}
              onSelect={setRiskFilter}
            />
          </Panel>

          {/* Gráfica C */}
          <Panel
            kicker="Gráfica C"
            title="Riesgo promedio por entidad"
            description="¿Qué entidades concentran los puntajes promedio más altos? Orden descendente de risk_score."
          >
            <EntityRankingChart
              groups={entityGroups}
              selectedEntity={selectedEntity}
              onSelectEntity={onEntityChange}
            />
          </Panel>
        </div>
      </section>

      {/* Gráfica B: Top 10 municipios prioritarios */}
      <section className="section-block" id="top-municipios-prioritarios">
        <Panel
          kicker="Gráfica B"
          title={`Top 10 municipios con mayor riesgo ${selectedEntity ? `en ${selectedEntity}` : "a nivel nacional"}`}
          description={`¿Qué municipios deben considerarse prioritarios? ${
            riskFilter !== "todos"
              ? `Mostrando top con filtro de nivel: ${riskDisplayLabel(riskFilter)}.`
              : "Ordenados por puntaje compuesto de riesgo (risk_score) descendente."
          }`}
          extraAction={
            riskFilter !== "todos" && (
              <button
                type="button"
                className="btn-text-action"
                onClick={() => setRiskFilter("todos")}
              >
                Restablecer a todos los niveles
              </button>
            )
          }
        >
          <PriorityTable rows={topPriority} selectedRiskFilter={riskFilter} />
        </Panel>
      </section>

      {/* Síntesis ejecutiva del proyecto para entender en menos de 1 minuto */}
      <section className="section-block executive-takeaways">
        <div className="takeaways-card">
          <div className="takeaways-header">
            <span className="takeaways-tag">Síntesis Ejecutiva</span>
            <h3>Entendimiento del proyecto en menos de un minuto</h3>
          </div>
          <div className="takeaways-grid">
            <div className="takeaway-item">
              <span className="takeaway-num">01</span>
              <div>
                <strong>¿Dónde se concentra el riesgo?</strong>
                <p>
                  A nivel nacional, 313 municipios (20.0% de los evaluados con histórico) registran riesgo alto. Se concentran fuertemente en entidades del norte y occidente como Baja California (69.2 pts), Durango (66.1 pts), Colima (64.1 pts) y Sinaloa (63.3 pts), junto con focos críticos en Oaxaca y Veracruz.
                </p>
              </div>
            </div>
            <div className="takeaway-item">
              <span className="takeaway-num">02</span>
              <div>
                <strong>¿Qué señales históricas lo explican?</strong>
                <p>
                  Tres componentes convergentes: (a) Abstención reciente superior al 45%, (b) 464 municipios con pendiente negativa persistente en participación, y (c) alta volatilidad electoral entre elecciones presidenciales e intermedias.
                </p>
              </div>
            </div>
            <div className="takeaway-item">
              <span className="takeaway-num">03</span>
              <div>
                <strong>¿Qué valor aporta al INE / DECEYEC?</strong>
                <p>
                  Permite a las Juntas Locales y Distritales dejar de operar con criterios intuitivos y focalizar recursos presupuestales y operativos (ENCÍVICA, módulos móviles, capacitación comunitaria) exactamente en los territorios con mayor riesgo de abstención previo a 2027 y 2030.
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}

function Introduction() {
  return (
    <section id="introduccion" className="intro-section">
      <div className="section-kicker">Reto 2 · INE · Analítica Predictiva</div>
      <div className="intro-grid">
        <div>
          <h1>Riesgo territorial de abstención</h1>
          <p className="intro-question">
            ¿Dónde se concentra el riesgo de abstención, qué señales históricas lo explican y qué podría ocurrir si no se interviene?
          </p>
        </div>
        <div className="intro-copy">
          <p>
            Herramienta analítica operativa diseñada para la Dirección Ejecutiva de Capacitación Electoral y Educación Cívica (DECEYEC) y las Juntas Distritales del INE, sustentada en datos abiertos censales disociados.
          </p>
          <div className="intro-facts">
            <span>
              <b>Periodo analizado</b>2009–2024 (6 ciclos)
            </span>
            <span>
              <b>Fuente oficial</b>CCPC del INE
            </span>
            <span>
              <b>Granularidad</b>Entidad · Municipio · Sección
            </span>
            <span>
              <b>Privacidad</b>100% agregado y disociado
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}

export default function App() {
  const [selectedEntity, setSelectedEntity] = useState("");

  // Municipality dataset (1MB, fast)
  const municipality = useDataset("municipality", true);
  // Lightweight section summary (1KB, instant)
  const sectionsSummary = useDataset("sectionsSummary", false);

  const entities = useMemo(() => {
    return municipality.data ? unique(municipality.data, "EDONOM") : [];
  }, [municipality.data]);

  const hasData = Boolean(municipality.data && municipality.data.length);
  const loading = municipality.loading;
  const error = municipality.error;

  return (
    <div className="app-shell">
      {/* Sidebar de Navegación Institucional */}
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            INE
          </div>
          <div>
            <strong>Riesgo Electoral</strong>
            <small>CCPC 2009–2024</small>
          </div>
        </div>

        <div className="nav-label">Etapa 1 · Web</div>
        <nav className="nav" aria-label="Navegación principal">
          <a href="#introduccion">Introducción</a>
          <a href="#indicadores-principales" className="active">
            Página 1: Resumen ejecutivo
          </a>
          <div className="nav-subitems">
            <a href="#indicadores-principales">Indicadores principales</a>
            <a href="#graficas-distribucion-entidades">Distribución y entidades</a>
            <a href="#top-municipios-prioritarios">Top 10 municipios prioritarios</a>
          </div>
        </nav>

        <div className="sidebar-stages-info">
          <div className="stage-item active-stage">
            <span className="stage-dot ready" />
            <span>Página 1: Resumen ejecutivo</span>
          </div>
          <div className="stage-item future-stage" title="Etapa posterior de desarrollo">
            <span className="stage-dot pending" />
            <span>Pág. 2+: Histórico y Simulación</span>
          </div>
        </div>

        <div className="sidebar-foot">
          <p>
            Información agregada y disociada del INE. Metodología explicable sin datos personales para planeación estratégica y priorización DECEYEC.
          </p>
        </div>
      </aside>

      {/* Contenido Principal */}
      <main className="main">
        {/* Topbar */}
        <header className="topbar">
          <div className="topbar-title">
            <div className="eyebrow">Dirección Ejecutiva de Capacitación Electoral y Educación Cívica</div>
            <p className="topbar-meta">Sistema de Alerta Temprana y Priorización Territorial</p>
          </div>
          <div className="status" aria-live="polite">
            <span className={`status-dot ${error ? "status-error" : loading ? "status-loading" : ""}`} />
            {error
              ? "Error al cargar datos"
              : loading
              ? "Cargando datos…"
              : "Base CCPC lista (2,477 municipios)"}
          </div>
        </header>

        {/* Hero Introducción */}
        <Introduction />

        {/* Barra de Filtro Territorial */}
        <div className="toolbar" role="search" aria-label="Filtro territorial">
          <div className="toolbar-field">
            <label htmlFor="entity-filter">Filtrar por Entidad Federativa:</label>
            <select
              id="entity-filter"
              value={selectedEntity}
              onChange={(e) => setSelectedEntity(e.target.value)}
              disabled={loading || Boolean(error)}
            >
              <option value="">Todo el país (32 entidades federativas)</option>
              {entities.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </div>

          {selectedEntity && (
            <button
              type="button"
              className="btn-reset-entity"
              onClick={() => setSelectedEntity("")}
            >
              ✕ Mostrar todo el país
            </button>
          )}
        </div>

        {/* Contenido de Página 1 */}
        {error ? (
          <div className="card empty-card error-message" role="alert">
            <h3>Error de conexión</h3>
            <p>No se pudieron cargar los datos analíticos del proyecto. {error}</p>
          </div>
        ) : loading ? (
          <div className="card empty-card" role="status">
            <div className="loading-spinner" />
            <p>Cargando información censal e indicadores de riesgo territorial…</p>
          </div>
        ) : hasData ? (
          <ExecutiveSummary
            allMunicipalities={municipality.data}
            selectedEntity={selectedEntity}
            onEntityChange={setSelectedEntity}
            sectionsSummary={sectionsSummary.data}
          />
        ) : null}

        {/* Footer Institucional */}
        <footer className="footer-source">
          Fuente: Instituto Nacional Electoral (INE) · Conteos Censales de Participación Ciudadana (CCPC) 2009–2024 · Procesamiento analítico disociado para el Reto 2.
        </footer>
      </main>
    </div>
  );
}

const rootElement = document.getElementById("root");
if (rootElement) {
  createRoot(rootElement).render(<App />);
}
