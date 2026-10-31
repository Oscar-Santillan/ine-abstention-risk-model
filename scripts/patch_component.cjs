const fs=require("fs");
let s=fs.readFileSync("src/main.jsx","utf8");

const component = `
function HistoricoNacional({ historico }) {
  if (!historico || !historico.data) {
    return (
      <section className="section-block" id="panoramahistorico">
        <Panel kicker="Página 2 · Panorama Histórico" title="Panorama histórico nacional (2009–2024)">
          <p className="text-muted">Cargando datos del panorama histórico nacional…</p>
        </Panel>
      </section>
    );
  }

  const { years, nacional, periodos } = historico.data;

  // Gráfica A: Participación Ponderada
  const partMax = Math.max(...years.map((y) => (nacional[y]?.participacion || 0) * 100));

  // Gráfica B: Abstención Ponderada
  const abstMax = Math.max(...years.map((y) => (nacional[y]?.abstencion || 0) * 100));

  // Gráfica D: Periodos
  const periodosData = periodos || [
    { etiqueta: "2009–2012", cambio_participacion: 0.1895 },
    { etiqueta: "2012–2015", cambio_participacion: -0.1776 },
    { etiqueta: "2015–2018", cambio_participacion: 0.1391 },
    { etiqueta: "2018–2021", cambio_participacion: -0.0851 },
    { etiqueta: "2021–2024", cambio_participacion: 0.0623 },
  ];

  return (
    <div className="historico-wrapper" id="panoramahistorico">
      <section className="section-block">
        <div className="section-header-row">
          <div>
            <div className="section-kicker">02 / Panorama Histórico Nacional</div>
            <h2 className="section-heading">Panorama histórico nacional (2009–2024)</h2>
            <p className="section-subheading">
              Evolución de la participación y abstención ponderada basada en Conteos Censales (CCPC). Cálculo ponderado exacto: SUM(SV) / SUM(LN) y SUM(NV) / SUM(LN).
            </p>
          </div>
        </div>

        {/* Banner Metodológico */}
        <div className="card memo-card" style={{ marginBottom: "24px" }}>
          <div style={{ display: "flex", gap: "12px", alignItems: "flex-start" }}>
            <span style={{ fontSize: "20px" }}>💡</span>
            <div>
              <strong style={{ fontSize: "15px" }}>Recomendación Metodológica Ponderada Aplicada</strong>
              <p style={{ margin: "4px 0 0", color: "var(--muted)", fontSize: "13px" }}>
                Para evitar distorsiones por el tamaño de los municipios, la participación y la abstención agregadas se calcularon con la suma nacional total de la Lista Nominal (LN), Votos/Votantes (SV) y No Votantes/Abstención (NV). No se usaron promedios simples.
              </p>
            </div>
          </div>
        </div>

        {/* Gráficas A y B */}
        <div className="grid two-col" style={{ marginBottom: "24px" }}>
          {/* Gráfica A */}
          <Panel
            kicker="Gráfica A"
            title="A. Participación agregada por año"
            description="Participación ponderada nacional = SUM(SV) / SUM(LN)"
          >
            <div className="chart-container">
              <div className="historico-bars-chart">
                {years.map((year) => {
                  const val = (nacional[year]?.participacion || 0) * 100;
                  const isPresidential = year === "2012" || year === "2018" || year === "2024";
                  return (
                    <div key={year} className="hist-bar-col">
                      <span className="hist-bar-val">{val.toFixed(1)}%</span>
                      <div className="hist-bar-track">
                        <div
                          className="hist-bar-fill"
                          style={{
                            height: \`\${(val / 70) * 100}%\`,
                            backgroundColor: isPresidential ? "var(--safe)" : "var(--azulClaro, #76A5C3)",
                          }}
                        />
                      </div>
                      <span className="hist-bar-year">{year}</span>
                      <small className="hist-bar-tag">{isPresidential ? "Presidente" : "Intermedia"}</small>
                    </div>
                  );
                })}
              </div>

              <div className="qa-box" style={{ marginTop: "16px" }}>
                <strong>Pregunta: ¿La participación agregada ha aumentado o disminuido con el tiempo?</strong>
                <p>
                  <strong>Respuesta:</strong> No sigue una tendencia lineal única, sino un patrón marcadamente ciclico. La participación oscila fuertemente entre elecciones presidenciales (55% - 62%) y elecciones intermedias (43% - 49%). Al comparar elecciones homologables, la participación en intermedias creció de 43.0% (2009) a 49.6% (2021), y en presidenciales se ha mantenido alta pero con leve caída en 2024 (55.8%) comparado con 2012 (61.9%) y 2018 (58.1%).
                </p>
              </div>
            </div>
          </Panel>

          {/* Gráfica B */}
          <Panel
            kicker="Gráfica B"
            title="B. Abstención agregada por año"
            description="Abstención ponderada nacional = SUM(NV) / SUM(LN)"
          >
            <div className="chart-container">
              <div className="historico-bars-chart">
                {years.map((year) => {
                  const val = (nacional[year]?.abstencion || 0) * 100;
                  const isHigh = val > 45;
                  return (
                    <div key={year} className="hist-bar-col">
                      <span className="hist-bar-val">{val.toFixed(1)}%</span>
                      <div className="hist-bar-track">
                        <div
                          className="hist-bar-fill"
                          style={{
                            height: \`\${(val / 70) * 100}%\`,
                            backgroundColor: isHigh ? "var(--alarm)" : "var(--warm)",
                          }}
                        />
                      </div>
                      <span className="hist-bar-year">{year}</span>
                      <small className="hist-bar-tag">{isHigh ? "Elevada" : "Moderada"}</small>
                    </div>
                  );
                })}
              </div>

              <div className="qa-box" style={{ marginTop: "16px" }}>
                <strong>Pregunta: ¿Cómo ha evolucionado la abstención desde 2009?</strong>
                <p>
                  <strong>Respuesta:</strong> Tuvo su nivel más alto en 2009 (54.6% en elección intermedia) y su punto más bajo en 2018 (35.1% en elección presidencial). La abstención aumenta de forma sistemática en cada elección intermedia (2009: 54.6%, 2015: 49.7%, 2021: 46.1%) y disminuye sustancialmente en elecciones presidenciales.
                </p>
              </div>
            </div>
          </Panel>
        </div>

        {/* Gráfica C: Ambas en el mismo gráfico */}
        <div className="grid" style={{ marginBottom: "24px" }}>
          <Panel
            kicker="Gráfica C"
            title="C. Participación y abstención en el mismo gráfico"
            description="Comparación temporal directa · Eje X: Año (2009–2024) · Eje Y: Porcentaje (%)"
          >
            <div className="chart-container">
              <div className="combined-lines-chart" style={{ padding: "20px 0" }}>
                <div style={{ display: "flex", gap: "24px", justifyContent: "center", marginBottom: "16px" }}>
                  <span style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 600 }}>
                    <span style={{ width: 16, height: 4, backgroundColor: "var(--safe)" }} /> Línea de Participación
                  </span>
                  <span style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 600 }}>
                    <span style={{ width: 16, height: 4, backgroundColor: "var(--alarm)" }} /> Línea de Abstención
                  </span>
                </div>

                {/* SVG Line Chart */}
                <svg viewBox="0 0 600 220" style={{ width: "100%", height: "auto", overflow: "visible" }}>
                  {/* Grid Lines */}
                  {[0, 20, 40, 60, 80].map((tick) => {
                    const y = 180 - (tick / 80) * 160;
                    return (
                      <g key={tick}>
                        <line x1="40" y1={y} x2="580" y2={y} stroke="var(--rule-light)" strokeDasharray="3 3" />
                        <text x="32" y={y + 4} fill="var(--faint)" fontSize="10" textAnchor="end">
                          {tick}%
                        </text>
                      </g>
                    );
                  })}

                  {/* Draw Lines */}
                  {(() => {
                    const pointsP = years.map((y, i) => {
                      const val = (nacional[y]?.participacion || 0) * 100;
                      const x = 60 + i * 100;
                      const yPos = 180 - (val / 80) * 160;
                      return { x, y: yPos, val, year: y };
                    });
                    const pointsA = years.map((y, i) => {
                      const val = (nacional[y]?.abstencion || 0) * 100;
                      const x = 60 + i * 100;
                      const yPos = 180 - (val / 80) * 160;
                      return { x, y: yPos, val, year: y };
                    });

                    const pathP = pointsP.map((p, i) => \`\${i === 0 ? "M" : "L"} \${p.x} \${p.y}\`).join(" ");
                    const pathA = pointsA.map((p, i) => \`\${i === 0 ? "M" : "L"} \${p.x} \${p.y}\`).join(" ");

                    return (
                      <>
                        <path d={pathP} fill="none" stroke="var(--safe)" strokeWidth="3" />
                        <path d={pathA} fill="none" stroke="var(--alarm)" strokeWidth="3" />

                        {pointsP.map((p) => (
                          <g key={"p-" + p.year}>
                            <circle cx={p.x} cy={p.y} r="5" fill="var(--safe)" />
                            <text x={p.x} y={p.y - 10} fill="var(--safe)" fontSize="11" fontWeight="bold" textAnchor="middle">
                              {p.val.toFixed(1)}%
                            </text>
                            <text x={p.x} y="200" fill="var(--ink)" fontSize="11" fontWeight="600" textAnchor="middle">
                              {p.year}
                            </text>
                          </g>
                        ))}

                        {pointsA.map((p) => (
                          <g key={"a-" + p.year}>
                            <circle cx={p.x} cy={p.y} r="5" fill="var(--alarm)" />
                            <text x={p.x} y={p.y + 18} fill="var(--alarm)" fontSize="11" fontWeight="bold" textAnchor="middle">
                              {p.val.toFixed(1)}%
                            </text>
                          </g>
                        ))}
                      </>
                    );
                  })()}
                </svg>
              </div>

              <div className="qa-box" style={{ marginTop: "16px" }}>
                <strong>Pregunta: ¿Cómo se relacionan ambas tendencias históricas?</strong>
                <p>
                  <strong>Respuesta:</strong> Muestran un comportamiento en espejo o simetría inversa perfecto. En cada ciclo con elección presidencial (2012, 2018, 2024), la participación repunta hacia el rango del 55% - 62% mientras la abstención cae al 35% - 38%. En elecciones intermedias (2009, 2015, 2021), la abstención supera a la participación, alcanzando su pico máximo en 2009 (54.6%). La brecha restante respecto al 100% corresponde al porcentaje no especificado o sin registro completo en el conteo censal.
                </p>
              </div>
            </div>
          </Panel>
        </div>

        {/* Gráfica D: Cambio entre elecciones */}
        <div className="grid">
          <Panel
            kicker="Gráfica D"
            title="D. Cambio entre elecciones (puntos porcentuales)"
            description="Variación neta en la tasa de participación entre periodos electorales consecutivos"
          >
            <div className="chart-container">
              <div className="periodos-bars-chart" style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: "16px", padding: "20px 0" }}>
                {periodosData.map((p) => {
                  const pts = p.cambio_participacion * 100;
                  const isPositive = pts >= 0;
                  const absPts = Math.abs(pts);
                  return (
                    <div key={p.etiqueta} className="period-col" style={{ textAlign: "center" }}>
                      <strong style={{ display: "block", color: isPositive ? "var(--safe)" : "var(--alarm)", fontSize: "16px", marginBottom: "8px" }}>
                        {isPositive ? "+" : ""}{pts.toFixed(1)} pts
                      </strong>
                      <div style={{ height: "120px", background: "var(--rule-light)", display: "flex", flexDirection: "column", justifyContent: "center", alignItems: "center", position: "relative" }}>
                        <div
                          style={{
                            width: "60%",
                            height: \`\${Math.min(100, (absPts / 20) * 100)}%\`,
                            backgroundColor: isPositive ? "var(--safe)" : "var(--alarm)",
                            borderRadius: "2px",
                          }}
                        />
                      </div>
                      <span style={{ display: "block", marginTop: "8px", fontWeight: "600", fontSize: "13px" }}>{p.etiqueta}</span>
                      <small style={{ color: "var(--muted)", fontSize: "11px" }}>
                        {isPositive ? "Recuperación" : "Caída"}
                      </small>
                    </div>
                  );
                })}
              </div>

              <div className="qa-box" style={{ marginTop: "16px" }}>
                <strong>Pregunta: ¿En qué periodo se produjo la mayor caída o recuperación?</strong>
                <p>
                  <strong>Respuesta:</strong>
                  <br />
                  • <strong>Mayor recuperación:</strong> El periodo <strong>2009–2012</strong>, con un incremento de <strong>+18.9 puntos porcentuales</strong> en la participación (de 43.0% a 61.9%), impulsado por la transición hacia la elección presidencial de 2012.
                  <br />
                  • <strong>Mayor caída:</strong> El periodo <strong>2012–2015</strong>, con una reducción de <strong>-17.8 puntos porcentuales</strong> (de 61.9% a 44.2%), al pasar de una elección presidencial a una elección intermedia.
                </p>
              </div>
            </div>
          </Panel>
        </div>
      </section>
    </div>
  );
}
`;

const oldMarker = "function Introduction() {";
s = s.replace(oldMarker, component + "\n" + oldMarker);
fs.writeFileSync("src/main.jsx", s);
console.log("OK added component");
