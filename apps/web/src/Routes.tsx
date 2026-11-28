import {useState,useEffect,useRef} from 'react';
import {get,type RouteNetwork,type RoutePath} from './api';
export default function Routes({network,release,show,onShow,path,onPath,dated,onClose,errorMessage,thematicEligible}:{network:RouteNetwork|null;release:string;show:boolean;onShow:(v:boolean)=>void;path:RoutePath|null;onPath:(v:RoutePath|null)=>void;dated:boolean;onClose:()=>void;errorMessage:string;thematicEligible:boolean}){
 const [start,setStart]=useState(''),[end,setEnd]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const request=useRef<AbortController|null>(null);
 function clearPath(){request.current?.abort();request.current=null;setBusy(false);setError('');onPath(null);}
 useEffect(()=>{setStart('');setEnd('');clearPath();return ()=>request.current?.abort();},[release,onPath]);
 async function calculate(){clearPath();const c=new AbortController();request.current=c;setBusy(true);try{const r=await get<RoutePath>('/api/v1/routes/path',{release,start,end},c.signal);if(!c.signal.aborted&&r.release_id===release)onPath(r);}catch{if(!c.signal.aborted)setError('تعذر حساب مسار بين العقدتين.');}finally{if(!c.signal.aborted)setBusy(false);}}
 return <aside className="encyclopedia floating-panel" aria-label="الطرق التاريخية"><button className="panel-close" aria-label="إغلاق الطرق" onClick={onClose}>×</button><h2>الطرق التاريخية</h2>
 <p className="muted">شبكة المصدر الأصلية؛ المسار المحسوب هو الأقل وزنًا بحسب المسافات المسجلة، وليس رحلة تاريخية مثبتة.</p>
 {errorMessage&&<p role="alert">{errorMessage}</p>}<p data-testid="route-count">{network?.segments.length??0} مقطع · {network?.nodes.length??0} عقدة</p>
 <label className="article-toggle"><input type="checkbox" checked={show} onChange={e=>onShow(e.target.checked)}/> إظهار الطرق</label>
 {!thematicEligible&&<p>الشبكة غير معروضة في الحقبة الموضوعية المختارة. اختر كل العصور أو العصور الإسلامية.</p>}{dated&&<p>تُخفى الشبكة عند اختيار سنة دقيقة لغياب تأريخ المقاطع.</p>}
 <label>البداية<select aria-label="بداية الطريق" value={start} onChange={e=>{setStart(e.target.value);clearPath();}}><option value="">اختر محطة</option>{network?.nodes.map(n=><option key={n.id} value={n.id}>{n.name} · {n.id}</option>)}</select></label>
 <label>النهاية<select aria-label="نهاية الطريق" value={end} onChange={e=>{setEnd(e.target.value);clearPath();}}><option value="">اختر محطة</option>{network?.nodes.map(n=><option key={n.id} value={n.id}>{n.name} · {n.id}</option>)}</select></label>
 <button disabled={!start||!end||busy||dated||!thematicEligible} onClick={calculate}>احسب المسار</button>
 {error&&<p role="alert">{error}</p>}
 {path&&path.release_id===release&&<section><h3>المسار المحسوب</h3><p data-testid="route-distance">{(path.meters/1000).toFixed(2)} كم وفق المصدر</p><p>{path.steps.length} مقطع</p><ol>{path.steps.map((s,i)=><li key={i}>{network?.nodes.find(n=>n.id===s.from_id)?.name??s.from_id} ← {network?.nodes.find(n=>n.id===s.to_id)?.name??s.to_id}</li>)}</ol><button onClick={clearPath}>مسح المسار</button></section>}
 </aside>;
}
