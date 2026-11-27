import type {GeologyData,GeologyRecord} from './api';
export const geoKinds={shield:['الدرع والصخور القاعدية','#ab78a5'],basin:['الأحواض والمنخفضات','#c2aa64'],volcanic:['الأقاليم البركانية','#cc754c'],structure:['البنى والمرتفعات','#67ada5'],other:['أقاليم أخرى','#8a9fa8']} as const;
export const geoId=(r:GeologyRecord)=>r.type+':'+r.record.id;
export type GeoFilter={provinces:boolean;volcanoes:boolean;labels:boolean;kind:string;period:string;q:string};
export const defaultGeoFilter:GeoFilter={provinces:true,volcanoes:true,labels:true,kind:'all',period:'all',q:''};
import {searchKey} from './Directory';
export function filterGeology(data:GeologyData|null,f:GeoFilter){
 return (data?.records??[]).filter(r=>(r.type==='province'?f.provinces&&(f.kind==='all'||r.record.kind===f.kind):f.volcanoes&&(f.period==='all'||r.record.period===f.period))&&(!f.q||(!!searchKey(f.q)&&searchKey(r.record.name+' '+r.record.en).includes(searchKey(f.q)))));
}
export default function Geology({data,filter,onFilter,selected,onSelect,onClose,error}:{data:GeologyData|null;filter:GeoFilter;onFilter:(v:GeoFilter)=>void;selected:string|null;onSelect:(id:string|null)=>void;onClose:()=>void;error:string}){
 const rows=filterGeology(data,filter),active=data?.records.find(r=>geoId(r)===selected);
 function update(p:Partial<GeoFilter>){onFilter({...filter,...p});onSelect(null);}
 const links=active?.type==='volcano'?(data?.volcano_provinces[active.record.id]??[]).map(id=>'province:'+id):active?.type==='province'?Object.entries(data?.volcano_provinces??{}).filter(([,ids])=>ids.includes(active.record.id)).map(([id])=>'volcano:'+id):[];
 return <aside className="encyclopedia floating-panel" aria-label="جيولوجيا الأرض"><button className="panel-close" aria-label="إغلاق الجيولوجيا" onClick={onClose}>×</button><h2>جيولوجيا الأرض</h2>
 <p className="muted">جغرافيا مرجعية معاصرة عبر العصور، لا إعادة بناء للماضي ولا خريطة مكامن أو تقييم خطر بركاني.</p>{error&&<p role="alert">{error}</p>}
 <label className="article-toggle"><input type="checkbox" checked={filter.provinces} onChange={e=>update({provinces:e.target.checked})}/> الأقاليم الجيولوجية</label>
 <label>فئة الإقليم<select aria-label="فئة الإقليم" value={filter.kind} onChange={e=>update({kind:e.target.value})}><option value="all">الكل</option>{Object.entries(geoKinds).map(([k,v])=><option key={k} value={k}>{v[0]}</option>)}</select></label>
 <label className="article-toggle"><input type="checkbox" checked={filter.labels} onChange={e=>update({labels:e.target.checked})}/> أسماء الأقاليم</label>
 <label className="article-toggle"><input type="checkbox" checked={filter.volcanoes} onChange={e=>update({volcanoes:e.target.checked})}/> المواضع البركانية</label>
 <label>الفترة البركانية<select aria-label="الفترة البركانية" value={filter.period} onChange={e=>update({period:e.target.value})}><option value="all">الكل</option><option value="holocene">الهولوسين</option><option value="pleistocene">البليستوسين</option></select></label>
 <label>البحث في الجيولوجيا<input aria-label="البحث في الجيولوجيا" value={filter.q} onChange={e=>update({q:e.target.value})} maxLength={120}/></label>
 <p data-testid="geology-count">{rows.filter(r=>r.type==='province').length} إقليمًا · {rows.filter(r=>r.type==='volcano').length} موضعًا بركانيًا</p>
 <div className="geo-key">{Object.entries(geoKinds).filter(([k])=>rows.some(r=>r.type==='province'&&r.record.kind===k)).map(([k,v])=><span key={k}><i style={{background:v[1]}}/>{v[0]}</span>)}</div>
 {active&&<article><h3>{active.record.name}</h3><p lang="en" dir="ltr">{active.record.en}</p>{active.type==='province'?<><p>{geoKinds[active.record.kind][0]} · خريطة إقليمية مبسطة ({active.simplification_deg} درجة).</p><a href={active.reference} target="_blank" rel="noopener noreferrer">USGS — الخرائط الجيولوجية</a></>:<><p>{active.record.summary}</p><p>الارتفاع المرجعي: {active.record.elevation===null?'غير متاح':active.record.elevation+' متر'}</p><p>آخر ثوران معروف في المصدر: {active.record.last}</p><p>تصنيف المصدر: {active.record.period==='holocene'?'الهولوسين':'البليستوسين'}</p><a href={active.record.source} target="_blank" rel="noopener noreferrer">Smithsonian — Global Volcanism Program</a></>}
 <h3>ارتباطات مكانية مرجعية</h3>{links.length?links.map(id=><button key={id} onClick={()=>{const target=data?.records.find(r=>geoId(r)===id);if(target){onFilter({...filter,provinces:true,volcanoes:true,kind:'all',period:'all',q:''});onSelect(id);}}}>{data?.records.find(r=>geoId(r)===id)?.record.name??id}</button>):<p>لا يوجد تطابق في العينة المرسومة.</p>}<p className="muted">تقاطع النقطة مع المضلع المبسط، لا علاقة سببية أو إثبات احتياطيات.</p></article>}
 <ul className="items">{rows.map(r=><li key={geoId(r)}><button aria-pressed={selected===geoId(r)} onClick={()=>onSelect(geoId(r))}>{r.record.name}<small>{r.type==='province'?geoKinds[r.record.kind][0]:r.record.period==='holocene'?'الهولوسين':'البليستوسين'}</small></button></li>)}</ul>
 </aside>;
}
