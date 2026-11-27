import type {Snapshot} from './api';
export const yearText=(y:number)=>y<0?(-y)+' ق.م':y+' م';
export default function Territories({records,year,compare,onYear,onCompare,selected,onSelect,onClose,error}:{records:Snapshot[];year:number|null;compare:number|null;onYear:(v:number|null)=>void;onCompare:(v:number|null)=>void;selected:string|null;onSelect:(v:string|null)=>void;onClose:()=>void;error:string}){
 const years=[...new Set(records.map(r=>r.year))].sort((a,b)=>a-b);
 const polygonYears=[...new Set(records.filter(r=>r.type==='territory').map(r=>r.year))].sort((a,b)=>a-b);
 const rows=records.filter(r=>r.year===year);
 const active=rows.find(r=>snapshotId(r)===selected);
 return <aside className="encyclopedia floating-panel" aria-label="الجغرافيا السياسية"><button className="panel-close" aria-label="إغلاق النطاقات" onClick={onClose}>×</button><h2>الجغرافيا السياسية التاريخية</h2>
 <p className="muted">لقطات إقليمية تقريبية من المصدر؛ فراغ الخريطة لا يعني غياب الحكم. لا استيفاء زمني بين اللقطات.</p>{error&&<p role="alert">{error}</p>}
 <label>اللقطة<select aria-label="اللقطة التاريخية" value={year??''} onChange={e=>onYear(e.target.value?Number(e.target.value):null)}><option value="">اختر لقطة</option>{years.map(y=><option key={y} value={y}>{yearText(y)}</option>)}</select></label>
 <label>سنة المقارنة<select aria-label="سنة المقارنة" value={compare??''} disabled={!year||!polygonYears.includes(year)} onChange={e=>onCompare(e.target.value?Number(e.target.value):null)}><option value="">بلا مقارنة</option>{polygonYears.filter(y=>y!==year).map(y=><option key={y} value={y}>{yearText(y)}</option>)}</select></label>
 <p data-testid="territory-count">{rows.filter(r=>r.type==='territory').length} نطاقات · {rows.filter(r=>r.type==='milestone').length} محطات</p>
 {compare!==null&&<p data-testid="comparison-count">{records.filter(r=>r.type==='territory'&&r.year===compare).length} نطاقات للمقارنة · {yearText(compare)}</p>}
 {active&&<article>{active.type==='territory'?<><h3>{active.record.name}</h3><p>{{polity:'كيان سياسي',region:'إقليم تاريخي',dependency:'مجال تابع في المصدر'}[active.record.kind]} · {yearText(active.year)}</p><p>نطاق تقريبي معاد البناء؛ لا يثبت سيادة دقيقة.</p><a href={active.record.browse_url} target="_blank" rel="noopener noreferrer">Historical Basemaps — المصدر الأصلي</a></>:<><h3>{active.record.title}</h3><p>{active.record.text}</p><p>المركز التاريخي: {active.record.place} · علامة حدث لا حدود دولة.</p><a href="https://saudipedia.com/en/history-of-saudi-arabia" target="_blank" rel="noopener noreferrer">سعوديبيديا — تاريخ السعودية</a><p><a href="https://www.mofa.gov.sa/en/ksa/Pages/history.aspx" target="_blank" rel="noopener noreferrer">وزارة الخارجية — تاريخ المملكة</a></p></>}</article>}
 <ul className="items">{rows.map(r=><li key={snapshotId(r)}><button aria-pressed={selected===snapshotId(r)} onClick={()=>onSelect(snapshotId(r))}>{r.type==='territory'?r.record.name:r.record.title}</button></li>)}</ul>
 </aside>;
}
export function snapshotId(r:Snapshot){return r.type==='territory'?r.record.id:'milestone:'+r.year;}
