import {useState} from 'react';
import type {DirectoryEntry} from './api';
export const kindLabels:Record<string,string>={towns:'بلدة',waystations:'محطة طريق',villages:'قرية',regions:'إقليم',sites:'موقع',metropoles:'حاضرة',waters:'معلم مائي',capitals:'عاصمة'};
export function searchKey(s:string){return s.normalize('NFKC').toLowerCase().replace(/[أإآٱ]/g,'ا').replace(/ى/g,'ي').replace(/[ًٌٍَُِّْٰـ]/g,'').trim();}
export default function Directory({entries,collection,onCollection,region,onRegion,q,onQ,selected,onSelect,dated,error,onClose}:{entries:DirectoryEntry[];collection:'historical'|'modern';onCollection:(v:'historical'|'modern')=>void;region:string;onRegion:(v:string)=>void;q:string;onQ:(v:string)=>void;selected:string|null;onSelect:(id:string|null)=>void;dated:boolean;error:string;onClose:()=>void}){
 const [page,setPage]=useState(0);
 const pool=entries.filter(x=>x.collection===collection);
 const regions=[...new Set(pool.map(x=>x.region_label))].sort();
 const rows=pool.filter(x=>(!region||x.region_label===region)&&(!q||searchKey(x.record.name+' '+(x.record.en??'')).includes(searchKey(q))));
 const active=rows.find(x=>x.entity_id===selected);
 const pages=Math.max(1,Math.ceil(rows.length/30)),p=Math.min(page,pages-1);
 return <aside className="encyclopedia floating-panel" aria-label="المعجم الجغرافي"><button className="panel-close" aria-label="إغلاق المعجم" onClick={onClose}>×</button><h2>المعجم الجغرافي</h2>
 <p className="muted">سجلات مرجعية من v0.13؛ لا تعني إثبات وجود الموضع في سنة محددة.</p>{dated&&<p role="status">تُخفى نقاط المعجم عند تحديد سنة دقيقة.</p>}{error&&<p role="alert">{error}</p>}
 <label>المجموعة<select aria-label="مجموعة المعجم" value={collection} onChange={e=>{onCollection(e.target.value as 'historical'|'modern');onRegion('');onSelect(null);setPage(0);}}><option value="historical">المواضع التاريخية</option><option value="modern">المواضع المعاصرة</option></select></label>
 <label>الإقليم أو المنطقة<select aria-label="إقليم المعجم" value={region} onChange={e=>{onRegion(e.target.value);onSelect(null);setPage(0);}}><option value="">الكل</option>{regions.map(r=><option key={r}>{r}</option>)}</select></label>
 <label>البحث في المعجم<input aria-label="البحث في المعجم" value={q} onChange={e=>{onQ(e.target.value);onSelect(null);setPage(0);}} maxLength={120}/></label>
 <p data-testid="directory-count">{rows.length} مواضع</p>
 {active&&<article><h3>{active.record.name}</h3>{active.record.en&&<p lang="en" dir="ltr">{active.record.en}</p>}<p>{active.region_label} · {kindLabels[active.record.kind??'']??'موضع معاصر'}</p><p dir="ltr">{active.record.lat}, {active.record.lon}</p>
 {active.collection==='historical'&&<p>درجة اليقين الواردة في المصدر: {active.record.source_certainty==='certain'?'مؤكد بحسب المصدر':'غير محددة في المصدر'}</p>}
 {active.references.map(r=><p key={r.source_version_id}>{r.title} · {r.locator}</p>)}
 {active.record.source_url?.startsWith('https://')&&<a href={active.record.source_url} target="_blank" rel="noopener noreferrer">السجل الأصلي</a>}
 <button onClick={()=>onSelect(null)}>العودة إلى القائمة</button></article>}
 <ul className="items">{rows.slice(p*30,p*30+30).map(x=><li key={x.entity_id}><button aria-pressed={x.entity_id===selected} onClick={()=>onSelect(x.entity_id)}>{x.record.name}<small>{x.region_label}</small></button></li>)}</ul>
 <div className="network-endpoints"><button disabled={p===0} onClick={()=>setPage(p-1)}>السابق</button><span>{p+1}/{pages}</span><button disabled={p===pages-1} onClick={()=>setPage(p+1)}>التالي</button></div>
 </aside>;
}
