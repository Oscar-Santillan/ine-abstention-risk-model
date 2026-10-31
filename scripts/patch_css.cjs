const fs=require("fs");
let s=fs.readFileSync("src/styles.css","utf8");
const css = `
/* HistoricoNacional Component Styles */
.historico-wrapper {
  scroll-margin-top: 20px;
}

.historico-bars-chart {
  display: flex;
  gap: 12px;
  padding: 20px 0;
}

.hist-bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.hist-bar-val {
  font-family: var(--font-mono);
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
}

.hist-bar-track {
  width: 100%;
  height: 160px;
  background: var(--rule-light);
  position: relative;
  display: flex;
  align-items: flex-end;
}

.hist-bar-fill {
  width: 60%;
  transition: height 0.3s ease;
}

.hist-bar-year {
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
}

.hist-bar-tag {
  font-size: 11px;
  color: var(--muted);
}

.combined-lines-chart {
  width: 100%;
  height: auto;
}

.periodos-bars-chart {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 16px;
}

.period-col {
  text-align: center;
}
`;
if(s.includes(css)){console.log("CSS already exists");process.exit(0);}
fs.writeFileSync("src/styles.css", s + "\n" + css);
console.log("OK added CSS");
