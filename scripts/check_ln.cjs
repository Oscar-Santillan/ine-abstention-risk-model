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
let mismatch=0, total=0, maxdiff=0;
data.forEach(r=>{
  const ln=Number(r.LN)||0, sv=Number(r.SV)||0, nv=Number(r.NV)||0, ns=Number(r.NS)||0;
  total++;
  const diff=Math.abs(ln-(sv+nv+ns));
  if(diff>1){mismatch++; if(diff>maxdiff)maxdiff=diff;}
});
console.log('total rows', total, 'mismatch LN!=SV+NV+NS:', mismatch, 'maxdiff', maxdiff);
