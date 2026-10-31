const fs = require("fs");
function parseCsv(text){
  const rows=[]; let row=[]; let cell=""; let q=false;
  for(let i=0;i<text.length;i++){
    const ch=text[i], nx=text[i+1];
    if(ch==='"' && q && nx==='"'){cell+='"';i++;continue;}
    if(ch==='"'){q=!q;continue;}
    if(ch==="," && !q){row.push(cell);cell="";continue;}
    if((ch==="\n"||ch==="\r")&&!q){ if(ch==="\r"&&nx==="\n")i++; row.push(cell); if(row.some(Boolean))rows.push(row); row=[];cell="";continue;}
    cell+=ch;
  }
  if(cell||row.length){row.push(cell); if(row.some(Boolean))rows.push(row);}
  if(!rows.length) return [];
  const headers=rows.shift().map(h=>h.replace(/^\uFEFF/,"").trim());
  return rows.map(v=>Object.fromEntries(headers.map((h,i)=>[h,(v[i]??"").trim()])));
}
const text=fs.readFileSync("outputs/datosAnaliticos/ccpc_municipioAnio.csv","utf8");
const data=parseCsv(text);
const years=[2009,2012,2015,2018,2021,2024];
const nac={};
years.forEach(y=>nac[y]={ln:0,sv:0,nv:0,ns:0});
const ent={};
data.forEach(r=>{
  const y=Number(r.AELEC); const ln=Number(r.LN)||0; const sv=Number(r.SV)||0; const nv=Number(r.NV)||0; const ns=Number(r.NS)||0;
  if(!nac[y]) return;
  nac[y].ln+=ln; nac[y].sv+=sv; nac[y].nv+=nv; nac[y].ns+=ns;
  const edo=r.EDONOM;
  if(!edo) return;
  if(!ent[edo]) ent[edo]={};
  if(!ent[edo][y]) ent[edo][y]={ln:0,sv:0,nv:0,ns:0};
  ent[edo][y].ln+=ln; ent[edo][y].sv+=sv; ent[edo][y].nv+=nv; ent[edo][y].ns+=ns;
});
const out={years:years.map(String), nacional:{}, entidades:{}};
years.forEach(y=>{
  const d=nac[y];
  out.nacional[y]={ln:d.ln,sv:d.sv,nv:d.nv,ns:d.ns,participacion:d.sv/d.ln,abstencion:d.nv/d.ln,no_especificada:d.ns/d.ln};
});
Object.keys(ent).forEach(edo=>{
  out.entidades[edo]={};
  years.forEach(y=>{
    const d=ent[edo][y];
    if(!d||d.ln===0){out.entidades[edo][y]=null;return;}
    out.entidades[edo][y]={ln:d.ln,sv:d.sv,nv:d.nv,ns:d.ns,participacion:d.sv/d.ln,abstencion:d.nv/d.ln,no_especificada:d.ns/d.ln};
  });
});
// periodos
const periodos=[];
for(let i=0;i<years.length-1;i++){
  const a=years[i], b=years[i+1];
  const pa=out.nacional[a].participacion, pb=out.nacional[b].participacion;
  const aa=out.nacional[a].abstencion, ab=out.nacional[b].abstencion;
  periodos.push({desde:a, hasta:b, etiqueta:`${a}–${b}`, cambio_participacion:pb-pa, cambio_abstencion:ab-aa});
}
out.periodos=periodos;
fs.writeFileSync("outputs/resultadosIntegrados/historicoNacional.json", JSON.stringify(out));
console.log("Entidades:", Object.keys(out.entidades).length);
console.log("Periodos:", JSON.stringify(periodos,null,2));
