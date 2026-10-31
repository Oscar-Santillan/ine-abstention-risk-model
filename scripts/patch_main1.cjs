const fs=require("fs");
let s=fs.readFileSync("src/main.jsx","utf8");
const old=`const DATA_PATHS = {
  municipality: "/outputs/resultadosIntegrados/ccpc_municipioResultadosIntegrados.csv",
  sectionsSummary: "/outputs/resultadosIntegrados/seccionesPorEntidad.json",
};`;
const neu=`const DATA_PATHS = {
  municipality: "/outputs/resultadosIntegrados/ccpc_municipioResultadosIntegrados.csv",
  sectionsSummary: "/outputs/resultadosIntegrados/seccionesPorEntidad.json",
  historico: "/outputs/resultadosIntegrados/historicoNacional.json",
};`;
if(!s.includes(old)){console.log("OLD NOT FOUND");process.exit(1);}
s=s.replace(old,neu);
fs.writeFileSync("src/main.jsx",s);
console.log("OK DATA_PATHS");
