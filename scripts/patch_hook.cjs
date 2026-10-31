const fs=require("fs");
let s=fs.readFileSync("src/main.jsx","utf8");
const old=`  const municipality = useDataset("municipality", true);
  // Lightweight section summary (1KB, instant)
  const sectionsSummary = useDataset("sectionsSummary", false);`;
const neu=`  const municipality = useDataset("municipality", true);
  // Lightweight section summary (1KB, instant)
  const sectionsSummary = useDataset("sectionsSummary", false);
  // Historical national series (small JSON)
  const historico = useDataset("historico", false);`;
if(!s.includes(old)){console.log("OLD NOT FOUND");process.exit(1);}
s=s.replace(old,neu);
fs.writeFileSync("src/main.jsx",s);
console.log("OK hook");
