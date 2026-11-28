import {useEffect,useRef,useState} from 'react';
import {get,type ConflictGroup,type ConflictPage} from './api';

const predicateLabels:Record<string,string>={NAME:'الاسم',BORN_IN:'مكان الميلاد',LIVED_IN:'الإقامة',LOCATED_IN:'الموقع',GOVERNED_BY:'الحكم',TRADED_WITH:'التجارة',FOUNDED:'التأسيس',CONNECTED_TO:'الاتصال'};
const stanceLabels:Record<string,string>={supports:'مؤيد',contradicts:'معارض',context:'سياق'};

export default function ScientificConflicts({release,entity}:{release:string;entity:string}){
 const [groups,setGroups]=useState<ConflictGroup[]>([]),[next,setNext]=useState<string|null>(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const controller=useRef<AbortController|null>(null);
 useEffect(()=>{
  const c=new AbortController();controller.current=c;
  setGroups([]);setNext(null);setError('');setBusy(true);
  get<ConflictPage>('/api/v1/conflicts',{release,entity_id:entity},c.signal).then(r=>{
   if(!c.signal.aborted){setGroups(r.conflicts);setNext(r.next_after);}
  }).catch(()=>{if(!c.signal.aborted)setError('تعذر تحميل الروايات العلمية.');}).finally(()=>{if(!c.signal.aborted)setBusy(false);});
  return ()=>c.abort();
 },[release,entity]);
 async function more(group?:ConflictGroup){
  const c=controller.current;if(!c||c.signal.aborted||busy)return;
  setBusy(true);setError('');
  try{
   const r=await get<ConflictPage>('/api/v1/conflicts',{release,entity_id:entity,...(group?{group_id:group.group_id,alternative_after:group.next_alternative_after??undefined}:{after:next??undefined})},c.signal);
   if(c.signal.aborted)return;
   if(group){
    const additional=r.conflicts[0];
    if(additional)setGroups(old=>old.map(g=>g.group_id===group.group_id?{...additional,alternatives:[...g.alternatives,...additional.alternatives]}:g));
   }else{setGroups(old=>[...old,...r.conflicts]);setNext(r.next_after);}
  }catch{if(!c.signal.aborted)setError('تعذر تحديث الروايات. أعد فتح بطاقة المعرفة للمحاولة مجددًا.');}
  finally{if(!c.signal.aborted)setBusy(false);}
 }
 if(!groups.length&&!error&&!busy)return null;
 return <section aria-label="التعارض العلمي" data-testid="scientific-conflicts">
  <h3>الروايات العلمية المتعارضة</h3>
  {groups.length>0&&<p className="note">تُعرض الروايات مستقلة مع الأدلة المتاحة، دون ترجيح آلي.</p>}
  {error&&<p role="alert">{error}</p>}
  {busy&&<p role="status">جارٍ تحميل الروايات…</p>}
  {groups.map(g=><section key={g.group_id} data-testid="conflict-group">
   <h4>{predicateLabels[g.alternatives[0]?.predicate]??g.alternatives[0]?.predicate} · {g.alternative_count} روايات</h4>
   {g.alternatives.map(a=><article key={a.version_id} data-testid="conflict-alternative">
    <h5 dir="auto">{a.object_text??a.object_name??a.object_id??'رواية'}</h5>
    {a.temporal&&<p>{a.temporal.original_text} · {a.temporal.precision_label}</p>}
    {a.scientific_note&&<p className="note">{a.scientific_note}</p>}
    {a.geometries?.map((geo,i)=><details key={i}><summary>التمثيل المكاني · {geo.precision}</summary><pre dir="ltr" style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{JSON.stringify(geo.geometry)}</pre></details>)}
    {!!a.references?.length&&<><h6>أدلة الرواية</h6><ul>{a.references.map((r,i)=><li key={r.source_version_id+':'+i}>{r.title}{r.locator&&<small>{r.locator}</small>}{r.stance&&<small>{stanceLabels[r.stance]}</small>}</li>)}</ul></>}
   </article>)}
   {g.next_alternative_after&&<button disabled={busy} onClick={()=>more(g)}>المزيد من روايات المجموعة</button>}
  </section>)}
  {next&&<button disabled={busy} onClick={()=>more()}>المزيد من مجموعات التعارض</button>}
 </section>;
}
