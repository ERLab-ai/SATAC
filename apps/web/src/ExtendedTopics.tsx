import {useState} from 'react';
import type {ExtendedTopic} from './api';
import {artwork} from './legacyVisuals';
import {searchKey} from './Directory';
export const topicKey=(t:ExtendedTopic)=>t.type+':'+t.id;
export const topicTitle=(t:ExtendedTopic)=>t.type==='story'?t.record.title:t.record.name;
export default function ExtendedTopics({topics,selected,onSelect,show,onShow,dated,onClose,onBack,error}:{topics:ExtendedTopic[];selected:string|null;onSelect:(id:string|null)=>void;show:boolean;onShow:(v:boolean)=>void;dated:boolean;onClose:()=>void;onBack:()=>void;error:string}){
 const [q,setQ]=useState(''),[kind,setKind]=useState('all');
 const rows=topics.filter(t=>(kind==='all'||t.type===kind)&&(!q||(!!searchKey(q)&&searchKey(topicTitle(t)+' '+JSON.stringify(t.record)).includes(searchKey(q)))));
 const active=topics.find(t=>topicKey(t)===selected);
 return <aside className="encyclopedia floating-panel" aria-label="الموضوعات الإضافية"><button className="panel-close" aria-label="إغلاق الموضوعات" onClick={onClose}>×</button><h2>الموضوعات الإضافية</h2><button onClick={onBack}>الموسوعة الرئيسية</button>
 <p className="muted">مقالات سياقية من المعجم والتراث الجيولوجي؛ لا تعني إثبات وجود المعلم في سنة مختارة.</p>
 {error&&<p role="alert">{error}</p>}{dated&&<p>تُخفى العلامات المرجعية في العرض المؤرخ؛ تبقى النصوص متاحة للقراءة.</p>}
 <label className="article-toggle"><input type="checkbox" checked={show} onChange={e=>onShow(e.target.checked)}/> علامات الموضوعات الإضافية</label>
 <label>نوع الموضوع<select aria-label="نوع الموضوع الإضافي" value={kind} onChange={e=>{setKind(e.target.value);onSelect(null);}}><option value="all">الكل</option><option value="story">المعجم التاريخي</option><option value="geosite">التراث الجيولوجي</option></select></label>
 <label>البحث<input aria-label="البحث في الموضوعات الإضافية" value={q} onChange={e=>{setQ(e.target.value);onSelect(null);}} maxLength={120}/></label>
 <p data-testid="extended-count">{rows.length} موضوعات</p>
 {active&&<article className="article-reader"><h3>{topicTitle(active)}</h3>{active.type==='story'?<><p>{active.record.lead}</p>{active.record.sections.map(([title,body],i)=><section key={i}><h3>{title}</h3><p>{body}</p></section>)}<h3>مراجع المقال</h3>{active.record.sources.map(([title,url],i)=><p key={i}><a href={url} target="_blank" rel="noopener noreferrer">{title}</a></p>)}</>:<><p>التراث الجيولوجي · اليونسكو 2025 (بحسب إصدار المصدر)</p><figure className="legacy-artwork"><img src={artwork('dune')} alt="رسم توضيحي رمزي من الإصدار الأصلي"/><figcaption>رسم رمزي من v0.13، لا إعادة بناء جيولوجية</figcaption></figure><p>{active.record.age}</p><p>{active.record.summary}</p><h3>الأرض والإنسان</h3><p>{active.record.context}</p><h3>مساحة المنتزه</h3><p>{active.record.area.toLocaleString('ar-SA')} هكتارًا</p><p>علامة الخريطة عند {active.record.anchor}، مركز مرتبط بالمنتزه، لا تمثل حدوده.</p><a href={active.record.source} target="_blank" rel="noopener noreferrer">اليونسكو — المنتزه الجيولوجي العالمي</a></>}
 <button onClick={()=>onSelect(null)}>العودة إلى الموضوعات</button></article>}
 <ul className="items">{rows.map(t=><li key={topicKey(t)}><button aria-pressed={selected===topicKey(t)} onClick={()=>onSelect(topicKey(t))}>{topicTitle(t)}<small>{t.type==='story'?'المعجم التاريخي':'التراث الجيولوجي'}</small></button></li>)}</ul>
 </aside>;
}
