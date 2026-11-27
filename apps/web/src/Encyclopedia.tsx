import {useEffect,useState} from 'react';
import {get,type ArticleSummary,type ArticleDetail} from './api';
export const eraLabels:Record<string,string>={all:'كل الحقب',deep:'الزمن العميق',ancient:'العالم القديم',islamic:'العصور الإسلامية',states:'الدول السعودية',modern:'العصر الحديث'};
export const symbols:Record<string,string>={rock:'◆',oasis:'✿',tomb:'▣',route:'↝',port:'⚓',fort:'▰',globe:'◎',dam:'≋',terrace:'▤',dune:'△',industry:'⚙'};
export default function Encyclopedia({release,selected,onSelect,onClose,onAnchors,dated,showAnchors,setShowAnchors,extendedCount,onExtended}:{release:string;selected:string|null;onSelect:(id:string|null)=>void;onClose:()=>void;onAnchors:(rows:ArticleSummary[])=>void;dated:boolean;showAnchors:boolean;setShowAnchors:(v:boolean)=>void;extendedCount:number;onExtended:()=>void}){
 const [q,setQ]=useState(''),[submitted,setSubmitted]=useState(''),[era,setEra]=useState('all'),[rows,setRows]=useState<ArticleSummary[]>([]),[detail,setDetail]=useState<ArticleDetail|null>(null),[related,setRelated]=useState<{id:string;title:string}[]>([]),[error,setError]=useState(''),[loading,setLoading]=useState(false);
 useEffect(()=>{
 onAnchors([]);setRows([]);setError('');if(!release)return;
 const c=new AbortController();setLoading(true);
 get<{articles:ArticleSummary[]}>('/api/v1/articles',{release,q:submitted||undefined,era},c.signal).then(r=>{if(!c.signal.aborted){setRows(r.articles);onAnchors(r.articles);}}).catch(()=>{if(!c.signal.aborted)setError('تعذر تحميل الموسوعة.');}).finally(()=>{if(!c.signal.aborted)setLoading(false);});
 return ()=>c.abort();
 },[release,submitted,era,onAnchors]);
 useEffect(()=>{
 setDetail(null);setRelated([]);setError('');if(!selected||!release)return;const c=new AbortController();
 get<{article:ArticleDetail;related_topics:{id:string;title:string}[]}>('/api/v1/articles/'+encodeURIComponent(selected),{release},c.signal).then(r=>{if(!c.signal.aborted){setDetail(r.article);setRelated(r.related_topics);}}).catch(()=>{if(!c.signal.aborted)setError('المقال غير متاح في هذا الإصدار.');});
 return ()=>c.abort();
 },[release,selected]);
 return <aside className="encyclopedia floating-panel" aria-label="الموسوعة"><button className="panel-close" aria-label="إغلاق الموسوعة" onClick={onClose}>×</button><h2>الموسوعة</h2><button onClick={onExtended}>الموضوعات الإضافية ({extendedCount})</button>
 <form className="article-search" onSubmit={e=>{e.preventDefault();onSelect(null);setSubmitted(q.trim());}}><label htmlFor="article-search">البحث في المقالات</label><div className="search-row"><input id="article-search" value={q} onChange={e=>setQ(e.target.value)} maxLength={120}/><button>بحث المقالات</button></div></form>
 <label>الحقبة الموضوعية<select aria-label="الحقبة الموضوعية" value={era} onChange={e=>{onSelect(null);setEra(e.target.value);}}>{Object.entries(eraLabels).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
 <label className="article-toggle"><input type="checkbox" checked={showAnchors} onChange={e=>setShowAnchors(e.target.checked)}/> معالم الموسوعة</label>
 {dated&&<p className="muted">المقالات موضوعية؛ تُخفى نقاطها المرجعية عند تحديد سنة دقيقة.</p>}
 {error&&<p role="alert">{error}</p>}
 {selected&&<button className="secondary" onClick={()=>onSelect(null)}>العودة إلى المقالات</button>}
 {detail?<article className="article-reader"><p className="eyebrow">{detail.category} · {detail.eras.map(k=>eraLabels[k]).join(' · ')}</p><h3>{detail.title}</h3><p className="subtitle">{detail.subtitle}</p>{detail.heritage_status&&<p className="note">{detail.heritage_status}</p>}<p>{detail.summary}</p>
 {detail.sections.map((s,i)=><section key={i}><h3>{s.title}</h3><p>{s.text}</p></section>)}
 {!!detail.bibliography.length&&<section><h3>مراجع المقال</h3><ul>{detail.bibliography.map(s=><li key={s.id}>{s.url.startsWith('https://')?<a href={s.url} target="_blank" rel="noopener noreferrer">{s.title}</a>:s.title}</li>)}</ul></section>}
 {!!related.length&&<section><h3>موضوعات مرتبطة</h3><ul className="items">{related.map(r=><li key={r.id}><button onClick={()=>onSelect(r.id)}>{r.title}</button></li>)}</ul></section>}</article>:<><p role="status" data-testid="article-count">{loading?'جارٍ التحميل…':rows.length+' مقالات'}</p><ul className="items">{rows.map(a=><li key={a.id}><button onClick={()=>onSelect(a.id)}><span className="article-sigil">{symbols[a.art]??'◆'}</span> {a.title}<small>{a.category}</small></button></li>)}</ul></>}
 </aside>;
}
