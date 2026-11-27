import type {EditorialNetwork} from './api';
export default function Network({data,journey,step,onJourney,onStep,onArticle,links,onLinks,dated,onClose,error}:{data:EditorialNetwork|null;journey:number|null;step:number;onJourney:(id:number|null)=>void;onStep:(i:number)=>void;onArticle:(id:string)=>void;links:boolean;onLinks:(v:boolean)=>void;dated:boolean;onClose:()=>void;error:string}){
 const active=data?.journeys.find(j=>j.ordinal===journey);
 const titles=new Map(data?.articles.map(a=>[a.id,a.title]));
 return <aside className="encyclopedia floating-panel" aria-label="العلاقات والرحلات"><button className="panel-close" aria-label="إغلاق العلاقات" onClick={onClose}>×</button><h2>العلاقات والرحلات</h2>
 <p className="muted">خطوط ترابط موضوعية ومحطات استكشاف، وليست مسارات سفر تاريخية أو قياسًا للمسافات.</p>
 {dated&&<p role="status">تُخفى الخطوط المرجعية عند تحديد سنة دقيقة.</p>}{error&&<p role="alert">{error}</p>}
 <label className="article-toggle"><input type="checkbox" checked={links} onChange={e=>onLinks(e.target.checked)}/> إظهار العلاقات</label>
 <h3>العلاقات الحضارية</h3><p data-testid="link-count">{data?.links.length??0} علاقة</p>
 <ul className="items">{data?.links.map(l=><li key={l.ordinal}><strong>{l.record[2]}</strong>{l.record[3]&&<small>{l.record[3]}</small>}<div className="network-endpoints">{l.record.slice(0,2).map(id=><button key={id} onClick={()=>onArticle(id)}>{titles.get(id)??id}</button>)}</div></li>)}</ul>
 <h3>الرحلات الموضوعية</h3><p data-testid="journey-count">{data?.journeys.length??0} رحلات</p>
 <label>اختيار الرحلة<select aria-label="اختيار الرحلة" value={journey??''} onChange={e=>onJourney(e.target.value===''?null:Number(e.target.value))}><option value="">اختر رحلة</option>{data?.journeys.map(j=><option key={j.ordinal} value={j.ordinal}>{j.record.title}</option>)}</select></label>
 {active&&<section><h3>{active.record.title}</h3><p>{active.record.subtitle}</p><p data-testid="journey-progress">المحطة {step+1} من {active.record.ids.length}</p>
 <div className="network-endpoints"><button disabled={step===0} onClick={()=>onStep(step-1)}>المحطة السابقة</button><button disabled={step===active.record.ids.length-1} onClick={()=>onStep(step+1)}>المحطة التالية</button></div>
 <ol>{active.record.ids.map((id,i)=><li key={i}><button aria-pressed={step===i} onClick={()=>onStep(i)}>{titles.get(id)??id}</button></li>)}</ol>
 <button onClick={()=>onArticle(active.record.ids[step])}>قراءة مقال المحطة</button></section>}
 </aside>;
}
