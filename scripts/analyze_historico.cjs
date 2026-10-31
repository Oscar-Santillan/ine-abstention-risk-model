const fs = require('fs');
function parseCsv(text){
  const rows=[]; let row=[]; let cell=''; let q=false;
  for(let i=0;i<text.length;i++){
    const ch=text[i], nx=text[i+1];
    if(ch==='"' && q && nx==='"'){cell+='"';i++;continue;}
    if(ch==='"'){q=!q;continue;}
    if(ch===',' && !q){row.push(cell);cell='';continue;}
    if((ch==='\n'||ch==='\r')&&!q){ if(ch==='\r'&&nx==='\n')i++; row.push(cell); if(row.some(Boolean))rows.push(row); row=[];cell='';continue;}
    cell+=ch;
  }
  if(cell||row.length){row.push(cell); if(row.some(Boolean))rows.push(row);}
  if(!rows.length) return [];
  const headers=rows.shift().map(h=>h.replace(/^\uFEFF/,'').trim());
  return rows.map(v=>Object.fromEntries(headers.map((h,i)=>[h,(v[i]??'').trim()])));
}
const text=fs.readFileSync('outputs/datosAnaliticos/ccpc_municipioAnio.csv','utf8');
const data=parseCsv(text);
console.log('rows', data.length);
const byYear={};
data.forEach(r=>{
  const ae=r.AELEC; const ln=Number(r.LN)||0; const sv=Number(r.SV)||0; const nv=Number(r.NV)||0; const ns=Number(r.NS)||0;
  if(!byYear[ae]) byYear[ae]={ln:0,sv:0,nv:0,ns:0,n:0};
  byYear[ae].ln+=ln; byYear[ae].sv+=sv; byYear[ae].nv+=nv; byYear[ae].ns+=ns; byYear[ae].n++;
});
console.log('Year | LN | SV | NV | NS | PartPond% | AbstPond% | NS%');
Object.keys(byYear).sort().forEach(y=>{
  const d=byYear[y];
  console.log(y, d.ln, d.sv, d.nv, d.ns, (d.sv/d.ln*100).toFixed(2)+'%', (d.nv/d.ln*100).toFixed(2)+'%', (d.ns/d.ln*100).toFixed(2)+'%');
});
