import type {CellData,CellMetric,ArticleSummary,DirectoryEntry} from './api';
export type Lens='water'|'articles'|'historical'|'modern';
export const lensNames:Record<Lens,string>={water:'أطوال المجاري المائية',articles:'الموضوعات الموسوعية',historical:'المواضع التاريخية',modern:'المواضع المعاصرة'};
export type CellStats=Map<string,{articles:ArticleSummary[];historical:DirectoryEntry[];modern:DirectoryEntry[]}>;
export function center(c:CellMetric):[number,number]{return [c.c*1.5*c.radius*.36-180,90-(c.t+(c.c%2)*.5)*Math.sqrt(3)*c.radius*.36];}
export function ring(c:CellMetric):[number,number][]{const [x,y]=center(c);const p=Array.from({length:6},(_,i)=>[x+c.radius*.36*Math.cos(i*Math.PI/3),y-c.radius*.36*Math.sin(i*Math.PI/3)] as [number,number]);return [...p,p[0]];}
export function atCell(lon:number,lat:number,rows:CellMetric[]):CellMetric|undefined{
 const r=.72,dy=Math.sqrt(3)*r,x=(lon+180)/.36,y=(90-lat)/.36,c=Math.round(x/(1.5*r));let id='',best=Infinity;
 for(let i=c-1;i<=c+1;i++){const j=Math.round(y/dy-(i%2)*.5);for(let k=j-1;k<=j+1;k++){const d=Math.hypot(x-i*1.5*r,y-(k+(i%2)*.5)*dy);if(d<best){best=d;id=i+','+k;}}}
 return rows.find(row=>row.id===id);
}
export function stats(rows:CellMetric[],articles:ArticleSummary[],directory:DirectoryEntry[]):CellStats{
 const m:CellStats=new Map();const bucket=(x:number,y:number)=>{const c=atCell(x,y,rows);if(!c)return;let s=m.get(c.id);if(!s){s={articles:[],historical:[],modern:[]};m.set(c.id,s);}return s;};
 for(const a of articles)bucket(...a.location)?.articles.push(a);
 for(const d of directory)bucket(d.record.lon,d.record.lat)?.[d.collection].push(d);
 return m;
}
export function cellBin(c:CellMetric,lens:Lens,s:CellStats){const n=lens==='water'?c.water_km:s.get(c.id)?.[lens].length??0;return lens==='water'?(n===0?0:n<25?1:n<75?2:3):(n===0?0:n===1?1:n<4?2:3);}
export const colors=(lens:Lens)=>lens==='water'?['#657466','#507e91','#3c9aaf','#8dd6d8']:['#657466','#9c8654','#d7a657','#ffe09a'];
export default function Cells({data,lens,onLens,selected,onSelect,stats:counts,dated,onClose,error,onArticle,onDirectory,onProvince}:{data:CellData|null;lens:Lens;onLens:(v:Lens)=>void;selected:string|null;onSelect:(v:string|null)=>void;stats:CellStats;dated:boolean;onClose:()=>void;error:string;onArticle:(id:string)=>void;onDirectory:(id:string)=>void;onProvince:(id:number)=>void}){
 const row=data?.cells.find(x=>x.id===selected),s=row?counts.get(row.id):undefined;
 return <aside className="encyclopedia floating-panel" aria-label="التحليل المكاني"><button className="panel-close" aria-label="إغلاق التحليل" onClick={onClose}>×</button><h2>الأرض والماء والعمران</h2>
 <p className="muted">خلايا إقليمية غير متساوية المساحة؛ جغرافيا مرجعية معاصرة. لا تقيس توفر الماء أو السكان أو الاحتياطيات.</p>{error&&<p role="alert">{error}</p>}
 <p data-testid="cell-count">{data?.cells.length??0} خلية</p><label>عدسة التحليل<select aria-label="عدسة التحليل" value={lens} onChange={e=>onLens(e.target.value as Lens)}>{Object.entries(lensNames).map(([k,v])=><option value={k} key={k}>{v}</option>)}</select></label>
 <div className="geo-key">{(lens==='water'?['0','أقل من 25 كم','25–أقل من 75 كم','75+ كم']:['0','1','2–3','4+']).map((v,i)=><span key={v}><i style={{background:colors(lens)[i]}}/>{v}</span>)}</div>
 {lens!=='water'&&<p>عدد سجلات الطبقات المعروضة فقط. فعّل الموسوعة أو مجموعة المعجم المطلوبة لإظهار سجلاتها.</p>}{dated&&<p>لا تظهر سجلات المعرفة غير المؤرخة في عدسات السنة الدقيقة.</p>}
 <label>اختيار خلية<select aria-label="معرف الخلية" value={selected??''} onChange={e=>onSelect(e.target.value||null)}><option value="">اختر خلية أو انقر الخريطة</option>{data?.cells.map(c=><option key={c.id}>{c.id}</option>)}</select></label>
 {row&&<article><h3>الخلية {row.id}</h3><p dir="ltr">{center(row).map(x=>x.toFixed(2)).join(', ')}</p><p data-testid="cell-area">{row.area_km2} كم² · مساحة الخلية الكاملة</p><p data-testid="cell-water">{row.water_km} كم · مجارٍ مرسومة</p>
 <p className="muted">قياسات WGS84 الموروثة؛ لا تعني جريان الماء أو توفره. قد تشمل الخلية جزءًا من البحر.</p>
 <h3>السجلات المعروضة داخل الخلية</h3><p>{s?.articles.length??0} موضوعات · {s?.historical.length??0} مواضع تاريخية · {s?.modern.length??0} مواضع معاصرة</p>
 {s?.articles.map(a=><button key={a.id} onClick={()=>onArticle(a.id)}>{a.title}</button>)}
 {[...(s?.historical??[]),...(s?.modern??[])].map(a=><button key={a.entity_id} onClick={()=>onDirectory(a.entity_id)}>{a.record.name}</button>)}
 <h3>الأقاليم الجيولوجية المتقاطعة</h3>{row.province_ids.map(id=><button key={id} onClick={()=>onProvince(id)}>{data?.provinces.find(p=>p.id===id)?.name??id}</button>)}
 {!row.province_ids.length&&<p>لا توجد ارتباطات منشورة في العينة.</p>}<p>ارتباطات هندسية من المصدر الأصلي، لا تقدير لمساحة الموارد.</p><a href="https://www.soest.hawaii.edu/pwessel/gshhg/" target="_blank" rel="noopener noreferrer">GSHHG — المصدر الجغرافي</a></article>}
 </aside>;
}
