const fs=require("fs");
let s=fs.readFileSync("scripts/copy-dashboard-data.mjs","utf8");
const old=`  "outputs/resultadosIntegrados/ccpc_municipioResultadosIntegrados.csv",
  "outputs/resultadosIntegrados/ccpc_seccionResultadosIntegrados.csv",
  "outputs/resultadosIntegrados/seccionesPorEntidad.json",
];`;
const neu=`  "outputs/resultadosIntegrados/ccpc_municipioResultadosIntegrados.csv",
  "outputs/resultadosIntegrados/ccpc_seccionResultadosIntegrados.csv",
  "outputs/resultadosIntegrados/seccionesPorEntidad.json",
  "outputs/resultadosIntegrados/historicoNacional.json",
];`;
if(!s.includes(old)){console.log("OLD NOT FOUND");process.exit(1);}
s=s.replace(old,neu);
fs.writeFileSync("scripts/copy-dashboard-data.mjs",s);
console.log("OK copy-dashboard");
