const fs=require("fs");
let s=fs.readFileSync("src/main.jsx","utf8");
const old=`        ) : hasData ? (
          <ExecutiveSummary
            allMunicipalities={municipality.data}
            selectedEntity={selectedEntity}
            onEntityChange={setSelectedEntity}
            sectionsSummary={sectionsSummary.data}
          />
        ) : null}

        {/* Footer Institucional */}`;
const neu=`        ) : hasData ? (
          <ExecutiveSummary
            allMunicipalities={municipality.data}
            selectedEntity={selectedEntity}
            onEntityChange={setSelectedEntity}
            sectionsSummary={sectionsSummary.data}
          />
        ) : null}

        {/* Página 2: Panorama histórico nacional */}
        <HistoricoNacional historico={historico} />

        {/* Footer Institucional */}`;
if(!s.includes(old)){console.log("OLD NOT FOUND");process.exit(1);}
s=s.replace(old,neu);
fs.writeFileSync("src/main.jsx",s);
console.log("OK insert page");
