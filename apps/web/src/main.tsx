import {useEffect,useState,type FormEvent} from 'react';
import {createRoot} from 'react-dom/client';
import AtlasMap from './AtlasMap';
import {get,releases,mapFeatures,emptyFeatures,type Release,type Features,type TimeFilter,type SearchResult,type Entity,type Claim} from './api';
import './style.css';

function yearValue(value:string,era:string){
 const normalized=value.trim().replace(/[٠-٩]/g,c=>String(c.charCodeAt(0)-1632)).replace(/[۰-۹]/g,c=>String(c.charCodeAt(0)-1776));
 if(!/^[0-9]{1,31}$/.test(normalized))throw new Error('أدخل سنة تاريخية صحيحة.');
 const n=BigInt(normalized);
 if(n===0n)throw new Error('لا توجد سنة صفر في التأريخ التاريخي.');
 const a=era==='BCE'?1n-n:n;
 if(a>10n**30n||a<-(10n**30n))throw new Error('السنة خارج نطاق التخزين.');
 return a.toString();
}
function App(){
 const [allReleases,setAllReleases]=useState<Release[]>([]),[release,setRelease]=useState(''),[releaseError,setReleaseError]=useState('');
 const [year,setYear]=useState(''),[era,setEra]=useState('CE'),[certainty,setCertainty]=useState('any'),[time,setTime]=useState<TimeFilter>({}),[timeLabel,setTimeLabel]=useState(''),[timeError,setTimeError]=useState('');
 const [data,setData]=useState<Features>(emptyFeatures),[mapLoading,setMapLoading]=useState(false),[mapError,setMapError]=useState(''),[truncated,setTruncated]=useState(false);
 const [q,setQ]=useState(''),[submitted,setSubmitted]=useState(''),[results,setResults]=useState<SearchResult[]>([]),[searchLoading,setSearchLoading]=useState(false),[searchError,setSearchError]=useState(''),[next,setNext]=useState<string|null>(null),[after,setAfter]=useState<string|undefined>();
 const [selected,setSelected]=useState<string|null>(null),[entity,setEntity]=useState<Entity|null>(null),[claim,setClaim]=useState<Claim|null>(null),[detailLoading,setDetailLoading]=useState(false),[detailError,setDetailError]=useState('');
 useEffect(()=>{
 const c=new AbortController();
 releases(c.signal).then(rows=>{if(c.signal.aborted)return;setAllReleases(rows);setRelease(rows.find(r=>r.is_current)?.release_id??rows[0]?.release_id??'');if(!rows.length)setReleaseError('لا توجد إصدارات معرفية متاحة.');}).catch(()=>{if(!c.signal.aborted)setReleaseError('تعذر الاتصال بقاعدة المعرفة.');});
 return ()=>c.abort();
 },[]);
 useEffect(()=>{
 if(!release)return;const c=new AbortController();
 setMapLoading(true);setData(emptyFeatures());setMapError('');setTruncated(false);
 mapFeatures(release,time,c.signal).then(r=>{if(!c.signal.aborted){setData(r.data);setTruncated(r.truncated);}}).catch(()=>{if(!c.signal.aborted)setMapError('تعذر تحميل المعالم.');}).finally(()=>{if(!c.signal.aborted)setMapLoading(false);});
 return ()=>c.abort();
 },[release,time]);
 useEffect(()=>{
 setResults([]);setNext(null);setSearchError('');
 if(!release||!submitted.trim()){setSearchLoading(false);return;}
 const c=new AbortController();setSearchLoading(true);
 get<{results:SearchResult[];next_after:string|null}>('/api/v1/search',{q:submitted,release,limit:'25',after,...time},c.signal).then(r=>{if(!c.signal.aborted){setResults(r.results);setNext(r.next_after);}}).catch(()=>{if(!c.signal.aborted)setSearchError('تعذر إكمال البحث.');}).finally(()=>{if(!c.signal.aborted)setSearchLoading(false);});
 return ()=>c.abort();
 },[release,time,submitted,after]);
 useEffect(()=>{
 setEntity(null);setClaim(null);setDetailError('');
 if(!release||!selected){setDetailLoading(false);return;}
 const c=new AbortController();setDetailLoading(true);
 (async()=>{const e=await get<Entity>('/api/v1/entities/'+selected,{release},c.signal);const n=e.names.find(n=>n.lang==='ar')??e.names[0];const d=n?(await get<{claim:Claim}>('/api/v1/claims/'+n.claim_id,{release},c.signal)).claim:null;if(!c.signal.aborted){setEntity(e);setClaim(d);}})().catch(()=>{if(!c.signal.aborted)setDetailError('لا تتوفر تفاصيل هذا الكيان في الإصدار المحدد.');}).finally(()=>{if(!c.signal.aborted)setDetailLoading(false);});
 return ()=>c.abort();
 },[release,selected]);
 function resetSelection(){setSelected(null);setEntity(null);setClaim(null);setAfter(undefined);}
 function applyTime(e:FormEvent){e.preventDefault();try{const as_of=yearValue(year,era);setTime({as_of,certainty});setTimeLabel(year.trim()+(era==='BCE'?' ق.م':' م'));setTimeError('');resetSelection();}catch(err){setTimeError((err as Error).message);}}
 function clearTime(){setTime({});setYear('');setTimeLabel('');setTimeError('');resetSelection();}
 const places=[...new Map(data.features.map(f=>[f.properties.subject_id,f.properties])).values()];
 const currentName=entity?.names.find(n=>n.lang==='ar')?.name??entity?.names[0]?.name;
 return <div className="app">
 <header className="masthead"><div className="brand"><span className="mark">S</span><div><span className="eyebrow">SATAC · نموذج تأسيسي v0.14</span><h1>السعودية عبر الزمن، عبر القارات</h1></div></div><span className="edition">الأطلس المعرفي</span></header>
 <main><section className="filters" aria-label="مرشحات الأطلس">
 <label>الإصدار المعرفي<select aria-label="الإصدار المعرفي" value={release} onChange={e=>{setRelease(e.target.value);resetSelection();}}>{!release&&<option value="">تحميل الإصدارات</option>}{allReleases.map(r=><option key={r.release_id} value={r.release_id}>{r.is_current?'الإصدار الحالي':r.created_at.slice(0,10)} · {r.release_id.slice(0,8)}</option>)}</select></label>
 <form className="time-form" onSubmit={applyTime}><label>السنة التاريخية<input aria-label="السنة التاريخية" inputMode="numeric" value={year} onChange={e=>setYear(e.target.value)} placeholder="مثال: 550"/></label>
 <label>التقويم<select aria-label="التقويم" value={era} onChange={e=>setEra(e.target.value)}><option value="CE">ميلادي</option><option value="BCE">قبل الميلاد</option></select></label>
 <label>التطابق<select value={certainty} onChange={e=>setCertainty(e.target.value)}><option value="any">مؤكد ومحتمل</option><option value="certain">مؤكد فقط</option><option value="possible">محتمل فقط</option></select></label>
 <button type="submit" disabled={!release}>تطبيق الزمن</button><button className="secondary" type="button" onClick={clearTime}>كل الأزمنة</button></form>
 {timeError&&<p role="alert">{timeError}</p>}{releaseError&&<p role="alert">{releaseError}</p>}</section>
 <div className="workspace">
 <aside aria-label="البحث والمواضع" className="sidebar"><h2>استكشف المعرفة</h2>
 <form className="search" onSubmit={e=>{e.preventDefault();setAfter(undefined);setSubmitted(q.trim());}}><label htmlFor="search">البحث عن موضع أو اسم</label><div className="search-row"><input id="search" value={q} onChange={e=>setQ(e.target.value)} placeholder="الحِجر، البتراء..." maxLength={120}/><button disabled={!release}>بحث</button></div></form>
 {submitted&&<section aria-label="نتائج البحث"><h3>نتائج البحث</h3><p role="status">{searchLoading?'جارٍ البحث…':results.length+' نتائج'}</p>{searchError&&<p role="alert">{searchError}</p>}
 <ul className="items">{results.map(r=><li key={r.version_id}><button aria-pressed={selected===r.entity_id} onClick={()=>setSelected(r.entity_id)}>{r.name}<small>{r.lang==='ar'?'العربية':'English'}</small></button></li>)}</ul>
 {next&&<button className="secondary" onClick={()=>setAfter(next)}>الصفحة التالية</button>}{after&&<button className="secondary" onClick={()=>setAfter(undefined)}>الصفحة الأولى</button>}</section>}
 <section aria-label="المواضع الظاهرة"><h3>المواضع الظاهرة على الخريطة</h3><p role="status" data-testid="feature-count">{mapLoading?'جارٍ تحميل المعالم…':places.length+' مواضع'}</p>
 {mapError&&<p role="alert">{mapError}</p>}{truncated&&<p>عُرضت أول 2000 سجل؛ نتائج إضافية غير معروضة.</p>}{time.as_of&&<p className="muted">التأريخ: {timeLabel} · لا تظهر السجلات غير المؤرخة.</p>}
 {!mapLoading&&!mapError&&!places.length&&<p>لا توجد مواضع مطابقة.</p>}
 <ul className="items">{places.map(p=><li key={p.subject_id}><button aria-pressed={selected===p.subject_id} onClick={()=>setSelected(p.subject_id)}>{p.name??p.subject_id}<small>{p.precision}</small></button></li>)}</ul></section></aside>
 <section className="main-map"><AtlasMap data={data} selected={selected} onSelect={setSelected}/></section>
 <aside className="detail" aria-label="تفاصيل الكيان"><h2>بطاقة المعرفة</h2>
 {!selected&&<p className="muted">اختر موضعًا من الخريطة أو نتائج البحث لاستعراض أسمائه ومراجعه المتاحة.</p>}
 {detailLoading&&<p role="status">جارٍ تحميل التفاصيل…</p>}{detailError&&<p role="alert">{detailError}</p>}
 {entity&&<article><p className="eyebrow">أسماء منشورة في الإصدار</p><h3>{currentName}</h3><ul className="names">{entity.names.map(n=><li key={n.version_id} lang={n.lang} dir="auto">{n.name}</li>)}</ul>
 {claim?.scientific_note&&<p className="note">{claim.scientific_note}</p>}
 {!!claim?.references?.length&&<section><h3>المراجع المتاحة</h3><ul>{claim.references.map((r,i)=><li key={r.source_version_id+i}>{r.title}{r.locator&&<small>{r.locator}</small>}</li>)}</ul></section>}</article>}</aside></div></main>
 <footer>أطلس تأسيسي · المحتوى الحالي من الإصدار المعرفي المحدد · الإحداثيات بحسب دقتها المسجلة.</footer></div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
