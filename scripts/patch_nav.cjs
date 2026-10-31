const fs=require("fs");
let s=fs.readFileSync("src/main.jsx","utf8");
const old=`        <a href="#indicadores-principales" className="active">
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
        </div>`;
const neu=`        <a href="#indicadores-principales">
            Página 1: Resumen ejecutivo
          </a>
          <a href="#panoramahistorico" className="nav-page">
            Página 2: Panorama histórico
          </a>
          <div className="nav-subitems">
            <a href="#indicadores-principales">Indicadores principales</a>
            <a href="#graficas-distribucion-entidades">Distribución y entidades</a>
            <a href="#top-municipios-prioritarios">Top 10 municipios prioritarios</a>
            <a href="#panoramahistorico">Panorama histórico nacional</a>
          </div>
        </nav>

        <div className="sidebar-stages-info">
          <div className="stage-item active-stage">
            <span className="stage-dot ready" />
            <span>Página 1: Resumen ejecutivo</span>
          </div>
          <div className="stage-item active-stage">
            <span className="stage-dot ready" />
            <span>Página 2: Panorama histórico</span>
          </div>
          <div className="stage-item future-stage" title="Etapa posterior de desarrollo">
            <span className="stage-dot pending" />
            <span>Pág. 3: Simulación y escenarios</span>
          </div>
        </div>`;
if(!s.includes(old)){console.log("OLD NOT FOUND");process.exit(1);}
s=s.replace(old,neu);
fs.writeFileSync("src/main.jsx",s);
console.log("OK nav");
