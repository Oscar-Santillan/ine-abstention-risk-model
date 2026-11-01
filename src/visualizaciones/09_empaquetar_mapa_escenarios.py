"""Empaqueta el mapa/tablero de escenarios y bases anonimizadas.

Genera:
  outputs/entregable_escenarios/mapa_escenarios.html
  outputs/entregable_escenarios/municipios_escenarios_anonimizados.csv
  outputs/entregable_escenarios/secciones_escenarios_anonimizados.csv

El HTML es autocontenido y no requiere servidor ni dependencias JavaScript
externas. Como el repositorio no incluye geometrías cartográficas, el mapa
ejecutable se presenta como un tablero territorial por entidad y zona.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs" / "entregable_escenarios"
SCENARIOS = ROOT / "outputs" / "escenarios"


def _zone_id(row: pd.Series, scope: str) -> str:
    parts = [scope, str(row.get("EDOCVE", "")), str(row.get("MPIOCVE", ""))]
    if scope == "secciones":
        parts.append(str(row.get("SECCION", "")))
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def anonymize(df: pd.DataFrame, scope: str) -> pd.DataFrame:
    result = pd.DataFrame(
        {
            "zona_id": df.apply(lambda r: _zone_id(r, scope), axis=1),
            "nivel_territorial": {"municipios": "municipio", "secciones": "seccion"}[scope],
            "entidad_codigo": df["EDOCVE"].astype("string"),
            "municipio_codigo": df["MPIOCVE"].astype("string"),
            "ano_proyectado": df["ano_proyectado"],
            "proyeccion_disponible": df["proyeccion_disponible"],
            "abstencion_sin_intervencion_pct": df["abstencion_proyectada"].mul(100).round(4),
            "abstencion_con_intervencion_pct": df[
                "abstencion_proyectada_intervencion"
            ].mul(100).round(4),
            "reduccion_abstencion_pp": df["reduccion_abstencion_pp"].round(4),
            "nivel_riesgo_base": df["nivel_base_ref"],
            "nivel_riesgo_intervencion": df["nivel_escenario_intervencion"],
            "perfil_intervencion": df["perfil_intervencion"],
            "propuestas_aplicadas": df["propuestas_aplicadas"],
        }
    )
    if scope == "secciones":
        result["seccion_codigo"] = df["SECCION"].astype("string")
    return result


def aggregate(df: pd.DataFrame) -> list[dict]:
    valid = df[df["proyeccion_disponible"].fillna(False)].copy()
    if valid.empty:
        return []
    grouped = (
        valid.groupby("entidad_codigo", dropna=False)
        .agg(
            zonas=("zona_id", "size"),
            abstencion_sin=("abstencion_sin_intervencion_pct", "mean"),
            abstencion_con=("abstencion_con_intervencion_pct", "mean"),
            reduccion_pp=("reduccion_abstencion_pp", "mean"),
            alto_base=("nivel_riesgo_base", lambda x: int((x == "alto").sum())),
            alto_intervencion=("nivel_riesgo_intervencion", lambda x: int((x == "alto").sum())),
        )
        .reset_index()
        .sort_values("reduccion_pp", ascending=False)
    )
    return json.loads(grouped.round(3).to_json(orient="records"))


def build_html(scopes: dict[str, pd.DataFrame], output: Path) -> None:
    payload = {
        scope: {
            "rows": json.loads(df.fillna("").to_json(orient="records")),
            "entities": aggregate(df),
        }
        for scope, df in scopes.items()
    }
    template = r"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Mapa de escenarios de abstención</title>
<style>
:root{--ink:#172033;--muted:#667085;--line:#e6eaf0;--blue:#2457d6;--green:#198754;--red:#d64545;--amber:#c88719}
*{box-sizing:border-box}body{font-family:Inter,Segoe UI,Arial,sans-serif;margin:0;color:var(--ink);background:#f4f7fb}
body:before{content:"";display:block;height:7px;background:#153b8f}
.shell{max-width:1220px;margin:0 auto;padding:34px 22px 60px}
h1{margin:0 0 8px;font-size:34px;letter-spacing:-.8px;color:#14213d}
h1:before{content:"INE  /  TABLERO EJECUTIVO";display:block;margin-bottom:12px;color:var(--blue);font-size:11px;font-weight:800;letter-spacing:1.8px}
.note{color:var(--muted);font-size:14px;line-height:1.65;max-width:900px;margin:0 0 22px}
.toolbar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:20px 0 24px;padding:15px 18px;background:#fff;border:1px solid var(--line);border-radius:14px}
label{color:var(--muted);font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.6px}
select{display:inline-block;margin-left:6px;padding:10px 34px 10px 12px;border:1px solid #d4dbe7;border-radius:9px;background:#fff;color:var(--ink);font-size:14px;outline:none}
select:focus{border-color:var(--blue)}
.toolbar button{border:0;border-radius:9px;padding:10px 14px;background:#edf2ff;color:#2149af;font-weight:700;cursor:pointer}
.toolbar button:hover{background:#dce6ff}
.cards{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin-bottom:22px}
.card{background:#fff;border:1px solid var(--line);border-radius:15px;padding:18px 20px}
.card:first-child{border-top:4px solid var(--blue)}.card:nth-child(2){border-top:4px solid var(--red)}.card:nth-child(3){border-top:4px solid var(--green)}.card:nth-child(4){border-top:4px solid var(--blue)}.card:nth-child(5){border-top:4px solid var(--amber)}
.value{font-size:25px;font-weight:800;letter-spacing:-.5px}.label{margin-top:6px;color:var(--muted);font-size:12px;line-height:1.35}.sub{color:var(--muted);font-size:11px;margin-top:6px}
.grid{display:grid;grid-template-columns:1.1fr .9fr;gap:18px;margin:18px 0}
.panel{background:#fff;border:1px solid var(--line);border-radius:15px;padding:20px}
.panel h2{margin:0 0 3px;font-size:18px;color:#243452}.panel .caption{color:var(--muted);font-size:12px;margin-bottom:16px}
.chart{min-height:230px}.legend{display:flex;gap:18px;color:var(--muted);font-size:12px;margin-top:10px}.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}.red{background:var(--red)}.green{background:var(--green)}.amber{background:var(--amber)}
.bars{display:flex;align-items:flex-end;justify-content:space-around;height:185px;border-bottom:1px solid #ccd5e2;padding:12px 8px 0}
.bar-col{width:17%;height:100%;display:flex;align-items:flex-end;gap:5px;justify-content:center}.bar-col i{display:block;width:42%;min-height:3px;border-radius:5px 5px 0 0}.bar-col span{position:absolute;margin-top:204px;font-size:11px;color:var(--muted)}
.bar-base{background:var(--red)}.bar-int{background:var(--green)}
.donut{width:180px;height:180px;border-radius:50%;margin:12px auto;display:grid;place-items:center;background:conic-gradient(var(--red) 0 34%,var(--amber) 34% 78%,var(--green) 78% 100%);position:relative}.donut:after{content:"";width:112px;height:112px;border-radius:50%;background:#fff;position:absolute}.donut strong{position:relative;z-index:1;font-size:22px;text-align:center}.donut small{display:block;color:var(--muted);font-size:10px;font-weight:400}
.mini-bars{display:grid;gap:10px}.mini-row{display:grid;grid-template-columns:145px 1fr 70px;gap:8px;align-items:center;font-size:12px}.mini-track{height:13px;background:#edf1f7;border-radius:99px;overflow:hidden}.mini-fill{height:100%;border-radius:99px;background:var(--blue)}
.hist{height:170px;display:flex;align-items:flex-end;gap:3px;border-bottom:1px solid #ccd5e2;padding:8px}.hist i{flex:1;background:var(--red);opacity:.75;min-height:2px}.hist i:nth-child(even){background:var(--green);opacity:.75}
.entity-list{max-height:390px;overflow:auto}.entity{background:#fbfcfe;border:1px solid var(--line);border-radius:10px;padding:12px 15px;margin:8px 0}.entity b{display:inline-block;width:125px;color:#243b72;font-size:13px}.entity small{color:var(--muted)}
.bar{height:8px;background:#f0d7d7;margin:10px 0 2px;border-radius:99px;overflow:hidden}.bar span{display:block;height:100%;background:var(--green);border-radius:99px}
.section-title{display:flex;justify-content:space-between;align-items:center;margin:28px 0 12px}.section-title h2{margin:0;font-size:19px;color:#243452}.count{color:var(--muted);font-size:12px}
table{border-collapse:separate;border-spacing:0;overflow:hidden;width:100%;background:#fff;margin-top:12px;margin-bottom:25px;font-size:12px;border:1px solid var(--line);border-radius:12px}
th,td{border-bottom:1px solid var(--line);padding:11px 10px;text-align:right}th{background:#eef3fb;color:#50617b;font-size:11px;text-transform:uppercase;letter-spacing:.4px}tr:last-child td{border-bottom:0}tr:hover td{background:#f7faff}th:first-child,td:first-child{text-align:left}
.alto{color:#c62828;font-weight:800}.medio{color:#bd7411;font-weight:800}.bajo{color:#198754;font-weight:800}.muted{color:var(--muted)}
@media(max-width:950px){.cards{grid-template-columns:repeat(3,1fr)}.grid{grid-template-columns:1fr}}
@media(max-width:650px){.shell{padding:25px 12px 40px}h1{font-size:27px}.cards{grid-template-columns:1fr 1fr}.toolbar{align-items:flex-start;flex-direction:column}.toolbar label{width:100%}.toolbar select{float:right}table{font-size:10px;display:block;overflow-x:auto;white-space:nowrap}}
</style></head><body><div class="shell">
<h1>Mapa de escenarios: sin vs con intervención</h1>
<p class="note">Tablero interactivo para comparar la abstención proyectada a 2030, medir la reducción potencial y priorizar territorios. Los valores con intervención son escenarios simulados, no efectos causales observados. La vista usa códigos anonimizados y no incluye geometrías cartográficas.</p>
<div class="toolbar">
<label>Alcance <select id="scope"><option value="municipios">Municipios</option><option value="secciones">Secciones</option></select></label>
<label>Entidad <select id="entity"><option value="">Todas</option></select></label>
<label>Municipio <select id="municipality"><option value="">Todos</option></select></label>
<label>Sección <select id="section"><option value="">Todas</option></select></label>
<label>Riesgo base <select id="risk"><option value="">Todos</option><option>alto</option><option>medio</option><option>bajo</option><option>sin_historico</option></select></label>
<button id="reset">Restablecer filtros</button>
</div>
<div id="cards" class="cards"></div>
<div class="grid"><section class="panel"><h2>Abstención proyectada: comparación</h2><div class="caption">Promedio de la selección actual · porcentaje</div><div id="comparison" class="chart"></div><div class="legend"><span><i class="dot red"></i>Sin intervención</span><span><i class="dot green"></i>Con intervención</span></div></section><section class="panel"><h2>Nivel de riesgo</h2><div class="caption">Distribución de la selección actual · escenario base</div><div id="riskChart" class="chart"></div></section></div>
<div class="grid"><section class="panel"><h2>Reducción por perfil</h2><div class="caption">Puntos porcentuales promedio</div><div id="profileChart" class="chart"></div></section><section class="panel"><h2>Distribución de abstención</h2><div class="caption">Barras alternadas: sin / con intervención</div><div id="histChart" class="chart"></div></section></div>
<div class="grid"><section class="panel"><h2>Comparación por entidad</h2><div class="caption">Ordenado por reducción media de abstención</div><div id="entities" class="entity-list"></div></section><section class="panel"><h2>Lectura ejecutiva</h2><div id="insight" class="caption" style="line-height:1.8"></div></section></div>
<div class="panel"><h2>Comparador territorial</h2><div class="caption">Selecciona dos entidades o municipios para comparar sus proyecciones.</div><div class="toolbar" style="margin:10px 0 16px;padding:0;border:0"><label>Entidad A <select id="compareEntityA"></select></label><label>Entidad B <select id="compareEntityB"></select></label><label>Municipio A <select id="compareMunicipalityA"></select></label><label>Municipio B <select id="compareMunicipalityB"></select></label></div><div id="compareChart" class="chart"></div></div>
<div class="panel"><h2>Prioridad territorial</h2><div class="caption">Top 10 zonas visibles por abstención sin intervención</div><div id="topChart" class="mini-bars"></div></div>
<div class="section-title"><h2>Detalle territorial</h2><span id="rowCount" class="count"></span></div>
<table><thead><tr><th>Zona anonimizada</th><th>Entidad</th><th>Municipio código</th><th>Sin intervención</th><th>Con intervención</th><th>Reducción pp</th><th>Riesgo base</th><th>Riesgo intervención</th><th>Propuesta</th></tr></thead><tbody id="rows"></tbody></table>
<p class="muted" style="font-size:11px">Fuente: simulación de escenarios INE · horizonte 2030 · la tabla muestra hasta 500 registros visibles por filtro.</p></div>
<script>
const DATA=__DATA__, scope=document.getElementById('scope'), entity=document.getElementById('entity'), municipality=document.getElementById('municipality'), section=document.getElementById('section'), risk=document.getElementById('risk');
const cards=document.getElementById('cards'), entities=document.getElementById('entities'), rows=document.getElementById('rows'), comparison=document.getElementById('comparison'), riskChart=document.getElementById('riskChart'), profileChart=document.getElementById('profileChart'), histChart=document.getElementById('histChart'), topChart=document.getElementById('topChart'), insight=document.getElementById('insight'), rowCount=document.getElementById('rowCount');
const compareEntityA=document.getElementById('compareEntityA'), compareEntityB=document.getElementById('compareEntityB'), compareMunicipalityA=document.getElementById('compareMunicipalityA'), compareMunicipalityB=document.getElementById('compareMunicipalityB'), compareChart=document.getElementById('compareChart');
const pct=x=>x===''||x==null||Number.isNaN(Number(x))?'—':Number(x).toFixed(1)+'%';
const esc=x=>String(x??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
function rowsFor(){return DATA[scope.value].rows}
function fillEntities(){let vals=[...new Set(rowsFor().map(x=>x.entidad_nombre||x.entidad_codigo))].sort();entity.innerHTML='<option value="">Todas las entidades</option>'+vals.map(x=>'<option>'+esc(x)+'</option>').join('');[compareEntityA,compareEntityB].forEach((s,i)=>s.innerHTML='<option value="">Entidad '+(i?'B':'A')+'</option>'+vals.map(x=>'<option>'+esc(x)+'</option>').join(''))}
function fillMunicipalities(){let vals=[...new Set(rowsFor().filter(x=>!entity.value||x.entidad_nombre===entity.value).map(x=>x.municipio_nombre||x.municipio_codigo))].sort();municipality.innerHTML='<option value="">Todos los municipios</option>'+vals.map(x=>'<option>'+esc(x)+'</option>').join('');let all=[...new Set(rowsFor().map(x=>x.municipio_nombre||x.municipio_codigo))].sort();[compareMunicipalityA,compareMunicipalityB].forEach((s,i)=>s.innerHTML='<option value="">Municipio '+(i?'B':'A')+'</option>'+all.map(x=>'<option>'+esc(x)+'</option>').join(''))}
function fillSections(){let vals=[...new Set(rowsFor().filter(x=>(!entity.value||x.entidad_nombre===entity.value)&&(!municipality.value||x.municipio_nombre===municipality.value)).map(x=>x.seccion_numero).filter(x=>x!==''))].sort((a,b)=>Number(a)-Number(b));section.innerHTML='<option value="">Todas las secciones</option>'+vals.map(x=>'<option>'+esc(x)+'</option>').join('')}
function mean(d,key){return d.length?d.reduce((s,x)=>s+Number(x[key]||0),0)/d.length:0}
function renderCharts(valid){let base=mean(valid,'abstencion_sin_intervencion_pct'),intervention=mean(valid,'abstencion_con_intervencion_pct'),max=Math.max(base,intervention,1);
comparison.innerHTML='<div class="bars"><div class="bar-col"><i class="bar-base" style="height:'+base/max*100+'%"></i><i class="bar-int" style="height:'+intervention/max*100+'%"></i><span>Promedio</span></div></div><div style="text-align:center;margin-top:22px;font-size:12px;color:#667085">'+pct(base)+' → '+pct(intervention)+'</div>';
let levels=['alto','medio','bajo'], counts=levels.map(n=>valid.filter(x=>x.nivel_riesgo_base===n).length), total=Math.max(valid.length,1), colors=['var(--red)','var(--amber)','var(--green)'], stops=[], pos=0; counts.forEach((v,i)=>{let next=pos+v/total*100;stops.push(colors[i]+' '+pos+'% '+next+'%');pos=next}); riskChart.innerHTML='<div class="donut" style="background:conic-gradient('+stops.join(',')+')"><strong>'+valid.filter(x=>x.nivel_riesgo_base==='alto').length.toLocaleString()+'<small>zonas en alto</small></strong></div><div class="legend" style="justify-content:center"><span><i class="dot red"></i>Alto '+counts[0].toLocaleString()+'</span><span><i class="dot amber"></i>Medio '+counts[1].toLocaleString()+'</span><span><i class="dot green"></i>Bajo '+counts[2].toLocaleString()+'</span></div>';
let profiles=['A','B','C','sin_perfil'], labels={'A':'A · crítica','B':'B · deterioro','C':'C · inestable','sin_perfil':'Sin perfil'}, profileRows=profiles.map(p=>{let s=valid.filter(x=>x.perfil_intervencion===p);return {p:p,n:s.length,v:mean(s,'reduccion_abstencion_pp')}});let pm=Math.max(...profileRows.map(x=>x.v),.01);profileChart.innerHTML='<div class="mini-bars">'+profileRows.map(x=>'<div class="mini-row"><span>'+labels[x.p]+'</span><div class="mini-track"><div class="mini-fill" style="width:'+x.v/pm*100+'%"></div></div><b>'+x.v.toFixed(2)+' pp</b></div>').join('')+'</div>';
let bins=Array.from({length:10},(_,i)=>({lo:i*10,hi:(i+1)*10,b:0,c:0}));valid.forEach(x=>{let b=Math.min(9,Math.floor(Number(x.abstencion_sin_intervencion_pct||0)/10)),c=Math.min(9,Math.floor(Number(x.abstencion_con_intervencion_pct||0)/10));bins[b].b++;bins[c].c++});let hm=Math.max(...bins.map(x=>Math.max(x.b,x.c)),1);histChart.innerHTML='<div class="hist">'+bins.map(x=>'<i title="'+x.lo+'–'+x.hi+'% · sin '+x.b+' · con '+x.c+'" style="height:'+Math.max(2,x.b/hm*100)+'%"></i><i title="'+x.lo+'–'+x.hi+'% · con '+x.c+'" style="height:'+Math.max(2,x.c/hm*100)+'%"></i>').join('')+'</div><div class="legend"><span><i class="dot red"></i>Sin intervención</span><span><i class="dot green"></i>Con intervención</span></div>';
let top=valid.slice().sort((a,b)=>Number(b.abstencion_sin_intervencion_pct)-Number(a.abstencion_sin_intervencion_pct)).slice(0,10), tm=Math.max(...top.map(x=>Number(x.abstencion_sin_intervencion_pct||0)),1);topChart.innerHTML=top.map(x=>'<div class="mini-row"><span>'+esc(x.zona_id)+'</span><div class="mini-track"><div class="mini-fill" style="width:'+Number(x.abstencion_sin_intervencion_pct)/tm*100+'%"></div></div><b>'+pct(x.abstencion_sin_intervencion_pct)+'</b></div>').join('');}
function compareGroup(label, filter){let d=rowsFor().filter(filter).filter(x=>x.proyeccion_disponible);return {label:label,base:mean(d,'abstencion_sin_intervencion_pct'),intervention:mean(d,'abstencion_con_intervencion_pct'),n:d.length}}
function renderComparator(){let ea=compareEntityA.value,eb=compareEntityB.value,ma=compareMunicipalityA.value,mb=compareMunicipalityB.value,g=[];if(ea)g.push(compareGroup(ea,x=>x.entidad_nombre===ea));if(eb)g.push(compareGroup(eb,x=>x.entidad_nombre===eb));if(ma)g.push(compareGroup(ma,x=>x.municipio_nombre===ma));if(mb)g.push(compareGroup(mb,x=>x.municipio_nombre===mb));if(!g.length){compareChart.innerHTML='<p class="muted">Selecciona al menos dos territorios para comparar.</p>';return}let max=Math.max(...g.flatMap(x=>[x.base,x.intervention]),1);compareChart.innerHTML='<div class="bars">'+g.map(x=>'<div class="bar-col"><i class="bar-base" style="height:'+x.base/max*100+'%" title="Sin intervención '+pct(x.base)+'"></i><i class="bar-int" style="height:'+x.intervention/max*100+'%" title="Con intervención '+pct(x.intervention)+'"></i><span>'+esc(x.label)+'<br>'+x.n.toLocaleString()+' zonas</span></div>').join('')+'</div><div class="legend"><span><i class="dot red"></i>Sin intervención</span><span><i class="dot green"></i>Con intervención</span></div>'}
function render(){let all=DATA[scope.value].rows, filtered=all.filter(x=>(!entity.value||x.entidad_nombre===entity.value)&&(!municipality.value||x.municipio_nombre===municipality.value)&&(!section.value||String(x.seccion_numero)===String(section.value))&&(!risk.value||x.nivel_riesgo_base===risk.value)), valid=filtered.filter(x=>x.proyeccion_disponible);
let base=mean(valid,'abstencion_sin_intervencion_pct'), intervention=mean(valid,'abstencion_con_intervencion_pct'), reduction=mean(valid,'reduccion_abstencion_pp'), high0=valid.filter(x=>x.nivel_riesgo_base==='alto').length, high1=valid.filter(x=>x.nivel_riesgo_intervencion==='alto').length, exited=Math.max(high0-high1,0);
cards.innerHTML=[['Zonas con proyección',valid.length.toLocaleString(),'Registros evaluables'],['Abstención sin intervención',pct(base),'Escenario inercial'],['Abstención con intervención',pct(intervention),'Escenario simulado'],['Reducción media',reduction.toFixed(2)+' pp','Cambio potencial'],['Zonas en alto',high0.toLocaleString()+' → '+high1.toLocaleString(),exited.toLocaleString()+' salen de alto']].map(x=>'<div class="card"><div class="value">'+x[1]+'</div><div class="label">'+x[0]+'</div><div class="sub">'+x[2]+'</div></div>').join('');
renderCharts(valid);
let ents=DATA[scope.value].entities.filter(x=>!entity.value||x.entidad_codigo===entity.value).slice(0,20); entities.innerHTML=ents.length?ents.map(x=>'<div class="entity"><b>'+esc(x.entidad_codigo)+'</b> <strong>'+Number(x.reduccion_pp).toFixed(2)+' pp</strong> <small> · '+Number(x.zonas).toLocaleString()+' zonas · alto '+x.alto_base+' → '+x.alto_intervencion+'</small><div class="bar"><span style="width:'+Math.max(3,100*x.abstencion_con/Math.max(x.abstencion_sin,1))+'%"></span></div></div>').join(''):'<p class="muted">No hay entidades para este filtro.</p>';
let best=ents[0], rate=high0?exited/high0*100:0; insight.innerHTML='<p><strong>Lectura principal:</strong> el escenario con intervención reduce la abstención promedio en <strong>'+reduction.toFixed(2)+' puntos porcentuales</strong> dentro de la selección actual.</p><p><strong>Prioridad:</strong> '+high0.toLocaleString()+' zonas parten en nivel alto; '+exited.toLocaleString()+' ('+rate.toFixed(1)+'%) dejarían esa categoría bajo el escenario simulado.</p>'+(best?'<p><strong>Mayor reducción media entre entidades visibles:</strong> '+esc(best.entidad_codigo)+' con '+Number(best.reduccion_pp).toFixed(2)+' pp.</p>':'');
rowCount.textContent='Mostrando '+Math.min(filtered.length,500).toLocaleString()+' de '+filtered.length.toLocaleString()+' zonas';
rows.innerHTML=filtered.slice(0,500).map(x=>'<tr><td>'+esc(x.zona_id)+'</td><td>'+esc(x.entidad_codigo)+'</td><td>'+esc(x.municipio_codigo)+'</td><td>'+pct(x.abstencion_sin_intervencion_pct)+'</td><td>'+pct(x.abstencion_con_intervencion_pct)+'</td><td>'+Number(x.reduccion_abstencion_pp||0).toFixed(2)+'</td><td class="'+x.nivel_riesgo_base+'">'+esc(x.nivel_riesgo_base||'—')+'</td><td class="'+x.nivel_riesgo_intervencion+'">'+esc(x.nivel_riesgo_intervencion||'—')+'</td><td>'+esc(x.propuestas_aplicadas)+'</td></tr>').join('')}
document.getElementById('reset').onclick=()=>{scope.value='municipios';entity.value='';municipality.value='';section.value='';risk.value='';fillEntities();fillMunicipalities();fillSections();render()}; scope.onchange=()=>{fillEntities();fillMunicipalities();fillSections();render()};entity.onchange=()=>{municipality.value='';section.value='';fillMunicipalities();fillSections();render()};municipality.onchange=()=>{section.value='';fillSections();render()};section.onchange=render;risk.onchange=render;[compareEntityA,compareEntityB,compareMunicipalityA,compareMunicipalityB].forEach(x=>x.onchange=renderComparator);fillEntities();fillMunicipalities();fillSections();render();renderComparator();
</script></body></html>"""
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(template.replace("__DATA__", json.dumps(payload, ensure_ascii=False)), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera tablero y CSV anonimizados de escenarios")
    parser.add_argument("--scenarios-dir", type=Path, default=SCENARIOS)
    parser.add_argument("--output-dir", type=Path, default=OUT)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    scopes = {}
    for scope, filename in {
        "municipios": "ccpc_municipioEscenarioConIntervencion.csv",
        "secciones": "ccpc_seccionEscenarioConIntervencion.csv",
    }.items():
        source = args.scenarios_dir / filename
        if not source.exists():
            continue
        frame = pd.read_csv(source, low_memory=False)
        clean = anonymize(frame, scope)
        clean.to_csv(args.output_dir / f"{scope}_escenarios_anonimizados.csv", index=False, encoding="utf-8")
        dashboard = clean.copy()
        dashboard["entidad_nombre"] = frame["EDONOM"].fillna("").astype(str).values
        dashboard["municipio_nombre"] = frame["MPIONOM"].fillna("").astype(str).values
        dashboard["seccion_numero"] = (
            frame["SECCION"].fillna("").astype(str).values if "SECCION" in frame else ""
        )
        scopes[scope] = dashboard
    if not scopes:
        raise SystemExit("No se encontraron CSV de escenarios con intervención.")
    build_html(scopes, args.output_dir / "mapa_escenarios.html")

if __name__ == "__main__":
    main()
