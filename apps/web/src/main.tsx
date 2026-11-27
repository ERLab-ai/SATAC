import {useEffect,useMemo,useRef,useState,type FormEvent} from 'react';
import {createRoot} from 'react-dom/client';
import AtlasMap from './AtlasMap';
import LayerPanel,{type ReferenceSettings,type LayerItem} from './LayerPanel';
import Encyclopedia from './Encyclopedia';
import ExtendedTopics from './ExtendedTopics';
import Network from './Network';
import Routes from './Routes';
import Territories from './Territories';
import Cells,{stats,type Lens} from './Cells';
import Geology,{defaultGeoFilter,filterGeology} from './Geology';
import Directory,{searchKey} from './Directory';
import {get,releases,mapFeatures,emptyFeatures,type Release,type Features,type TimeFilter,type SearchResult,type Entity,type Claim,type ArticleSummary,type EditorialNetwork,type DirectoryEntry,type RouteNetwork,type RoutePath,type Snapshot,type GeologyData,type CellData,type ExtendedTopic,type ExploreHit} from './api';
import {eraLabels,thematicEras,sourceEraAllows} from './legacyVisuals';
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
const YEAR_LIMIT=10n**30n;
function displayYear(a:bigint){return a<=0n?{year:(1n-a).toString(),era:'BCE'}:{year:a.toString(),era:'CE'};}
function App(){
 const appRef=useRef<HTMLDivElement>(null);
 const [full,setFull]=useState(false),[fullError,setFullError]=useState('');
 useEffect(()=>{const sync=()=>setFull(document.fullscreenElement===appRef.current);document.addEventListener('fullscreenchange',sync);return ()=>document.removeEventListener('fullscreenchange',sync);},[]);
 async function toggleFull(){setFullError('');try{if(document.fullscreenElement===appRef.current){await document.exitFullscreen();}else if(appRef.current?.requestFullscreen&&document.fullscreenEnabled){await appRef.current.requestFullscreen();}else{setFullError('ملء الشاشة غير متاح في هذا المتصفح.');}}catch{setFullError('تعذر تفعيل ملء الشاشة في هذا المتصفح.');}}

 const [allReleases,setAllReleases]=useState<Release[]>([]),[release,setRelease]=useState(''),[releaseError,setReleaseError]=useState('');
 const [panel,setPanel]=useState<'search'|'detail'|'encyclopedia'|'network'|'directory'|'routes'|'territories'|'geology'|'cells'|'extended'|'layers'|null>(null);
 const previousPanel=useRef<string|null>(null),returnFocus=useRef<HTMLElement|null>(null);
 useEffect(()=>{
  if(previousPanel.current===panel)return;
  if(panel){
   if(previousPanel.current===null) returnFocus.current=document.activeElement instanceof HTMLElement?document.activeElement:null;
   const heading=Array.from(appRef.current?.querySelectorAll<HTMLElement>('aside.floating-panel h2')??[]).find(el=>!el.closest('[hidden]'));
   if(heading){heading.tabIndex=-1;heading.focus({preventScroll:true});}
  }else{
   const target=returnFocus.current;
   if(target?.isConnected&&!target.closest('[hidden]')&&target.getClientRects().length&&target!==document.body)target.focus({preventScroll:true});
   else appRef.current?.querySelector<HTMLElement>('.header-actions button')?.focus({preventScroll:true});
   returnFocus.current=null;
  }
  previousPanel.current=panel;
 },[panel]);
 const [theme,setTheme]=useState('all');
 const [articleRows,setArticleRows]=useState<ArticleSummary[]>([]),[articleSelected,setArticleSelected]=useState<string|null>(null),[articleLayer,setArticleLayer]=useState(false);
 const [network,setNetwork]=useState<EditorialNetwork|null>(null),[networkError,setNetworkError]=useState(''),[showLinks,setShowLinks]=useState(false),[journey,setJourney]=useState<number|null>(null),[journeyStep,setJourneyStep]=useState(0);
 const [directory,setDirectory]=useState<DirectoryEntry[]>([]),[directoryError,setDirectoryError]=useState(''),[directoryCollection,setDirectoryCollection]=useState<'historical'|'modern'>('historical'),[directoryRegion,setDirectoryRegion]=useState(''),[directoryQuery,setDirectoryQuery]=useState(''),[directorySelected,setDirectorySelected]=useState<string|null>(null),[directoryLayer,setDirectoryLayer]=useState(false);
 const [routes,setRoutes]=useState<RouteNetwork|null>(null),[routePath,setRoutePath]=useState<RoutePath|null>(null),[routeLayer,setRouteLayer]=useState(false),[routeError,setRouteError]=useState('');
 useEffect(()=>{setRoutes(null);setRoutePath(null);setRouteError('');if(!release)return;const c=new AbortController();get<RouteNetwork>('/api/v1/routes',{release},c.signal).then(r=>{if(!c.signal.aborted)setRoutes(r);}).catch(()=>{if(!c.signal.aborted)setRouteError('تعذر تحميل شبكة الطرق.');});return ()=>c.abort();},[release]);
 const [snapshots,setSnapshots]=useState<Snapshot[]>([]),[snapshotError,setSnapshotError]=useState(''),[territoryLayer,setTerritoryLayer]=useState(false),[compare,setCompare]=useState<number|null>(null),[territorySelected,setTerritorySelected]=useState<string|null>(null);
 useEffect(()=>{setSnapshots([]);setCompare(null);setTerritorySelected(null);setSnapshotError('');if(!release)return;const c=new AbortController();get<{snapshots:Snapshot[]}>('/api/v1/snapshots',{release},c.signal).then(r=>{if(!c.signal.aborted)setSnapshots(r.snapshots);}).catch(()=>{if(!c.signal.aborted)setSnapshotError('تعذر تحميل اللقطات التاريخية.');});return ()=>c.abort();},[release]);
 const [geology,setGeology]=useState<GeologyData|null>(null),[geoError,setGeoError]=useState(''),[geoLayer,setGeoLayer]=useState(false),[geoFilter,setGeoFilter]=useState(defaultGeoFilter),[geoSelected,setGeoSelected]=useState<string|null>(null);
 useEffect(()=>{setGeology(null);setGeoError('');if(!release||!geoLayer)return;const c=new AbortController();get<GeologyData>('/api/v1/geology',{release},c.signal).then(r=>{if(!c.signal.aborted)setGeology(r);}).catch(()=>{if(!c.signal.aborted)setGeoError('تعذر تحميل الجيولوجيا.');});return ()=>c.abort();},[release,geoLayer]);
 const geoRows=useMemo(()=>geoLayer?filterGeology(geology,geoFilter):[],[geoLayer,geology,geoFilter]);
 function chooseGeology(id:string|null){setGeoSelected(id);setPanel('geology');}
 const [cellData,setCellData]=useState<CellData|null>(null),[cellError,setCellError]=useState(''),[cellLayer,setCellLayer]=useState(false),[cellLens,setCellLens]=useState<Lens>('water'),[cellSelected,setCellSelected]=useState<string|null>(null);
 useEffect(()=>{setCellData(null);setCellSelected(null);setCellError('');if(!release||!cellLayer)return;const c=new AbortController();get<CellData>('/api/v1/cells',{release},c.signal).then(r=>{if(!c.signal.aborted){setCellData(r);if(r.truncated)setCellError('توجد خلايا إضافية غير معروضة.');}}).catch(()=>{if(!c.signal.aborted)setCellError('تعذر تحميل الخلايا.');});return ()=>c.abort();},[release,cellLayer]);
 function chooseCell(id:string|null){setCellSelected(id);setPanel('cells');}
 function cellProvince(id:number){setGeoFilter(defaultGeoFilter);setGeoLayer(true);chooseGeology('province:'+id);}
 const [topics,setTopics]=useState<ExtendedTopic[]>([]),[topicSelected,setTopicSelected]=useState<string|null>(null),[topicLayer,setTopicLayer]=useState(false),[topicError,setTopicError]=useState('');
 useEffect(()=>{setTopics([]);setTopicSelected(null);setTopicError('');if(!release)return;const c=new AbortController();get<{topics:ExtendedTopic[]}>('/api/v1/extended-topics',{release},c.signal).then(r=>{if(!c.signal.aborted)setTopics(r.topics);}).catch(()=>{if(!c.signal.aborted)setTopicError('تعذر تحميل الموضوعات الإضافية.');});return ()=>c.abort();},[release]);
 function chooseTopic(id:string|null){setTopicSelected(id);setTopicLayer(true);setPanel('extended');}
 const [playing,setPlaying]=useState(false),[step,setStep]=useState('100');
 const [showLocations,setShowLocations]=useState(true);
 const [physical,setPhysical]=useState<'relief'|'etopo'|'flat'|'hex'>('relief');
 const [geoLabels,setGeoLabels]=useState(true);
 const [reference,setReference]=useState<ReferenceSettings>({rivers:false,borders:false,grid:false,texture:true,mini:true});
 const [refHits,setRefHits]=useState<ExploreHit[]>([]),[refTruncated,setRefTruncated]=useState(false),[refKind,setRefKind]=useState('all');
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
 setResults([]);setRefHits([]);setRefTruncated(false);setNext(null);setSearchError('');
 if(!release||!submitted.trim()){setSearchLoading(false);return;}
 const c=new AbortController();setSearchLoading(true);
 get<{results:SearchResult[];next_after:string|null;references:ExploreHit[];references_truncated:boolean}>('/api/v1/explore',{q:submitted,release,limit:'25',after,...time},c.signal).then(r=>{if(!c.signal.aborted){setResults(r.results);setNext(r.next_after);setRefHits(r.references);setRefTruncated(r.references_truncated);}}).catch(()=>{if(!c.signal.aborted)setSearchError('تعذر إكمال البحث.');}).finally(()=>{if(!c.signal.aborted)setSearchLoading(false);});
 return ()=>c.abort();
 },[release,time,submitted,after]);
 useEffect(()=>{
 setEntity(null);setClaim(null);setDetailError('');
 if(!release||!selected){setDetailLoading(false);return;}
 const c=new AbortController();setDetailLoading(true);
 (async()=>{const e=await get<Entity>('/api/v1/entities/'+selected,{release},c.signal);const n=e.names.find(n=>n.lang==='ar')??e.names[0];const d=n?(await get<{claim:Claim}>('/api/v1/claims/'+n.claim_id,{release},c.signal)).claim:null;if(!c.signal.aborted){setEntity(e);setClaim(d);}})().catch(()=>{if(!c.signal.aborted)setDetailError('لا تتوفر تفاصيل هذا الكيان في الإصدار المحدد.');}).finally(()=>{if(!c.signal.aborted)setDetailLoading(false);});
 return ()=>c.abort();
 },[release,selected]);
 useEffect(()=>{
 setNetwork(null);setNetworkError('');setJourney(null);setJourneyStep(0);
 if(!release)return;
 const c=new AbortController();
 get<EditorialNetwork>('/api/v1/editorial-network',{release},c.signal).then(r=>{if(!c.signal.aborted)setNetwork(r);}).catch(()=>{if(!c.signal.aborted)setNetworkError('تعذر تحميل العلاقات والرحلات.');});
 return ()=>c.abort();
 },[release]);
 useEffect(()=>{
 setDirectory([]);setDirectorySelected(null);setDirectoryError('');setDirectoryRegion('');
 if(!release)return;const c=new AbortController();
 get<{entries:DirectoryEntry[];truncated:boolean}>('/api/v1/directory',{release},c.signal).then(r=>{if(!c.signal.aborted){setDirectory(r.entries);if(r.truncated)setDirectoryError('توجد سجلات إضافية غير معروضة.');}}).catch(()=>{if(!c.signal.aborted)setDirectoryError('تعذر تحميل المعجم.');});
 return ()=>c.abort();
 },[release]);
 const directoryRows=useMemo(()=>directory.filter(x=>x.collection===directoryCollection&&(!directoryRegion||x.region_label===directoryRegion)&&(!directoryQuery||(!!searchKey(directoryQuery)&&searchKey(x.record.name+' '+(x.record.en??'')).includes(searchKey(directoryQuery))))),[directory,directoryCollection,directoryRegion,directoryQuery]);
 function chooseDirectory(id:string|null){setDirectorySelected(id);setPanel('directory');}
 function resetSelection(){setSelected(null);setEntity(null);setClaim(null);setAfter(undefined);setArticleSelected(null);setDirectorySelected(null);setPanel(p=>p==='detail'?null:p);}
 function choose(id:string){setSelected(id);setPanel('detail');}
 function chooseArticle(id:string|null){setArticleSelected(id);setPanel('encyclopedia');setArticleLayer(true);}
 function selectJourney(id:number|null){setJourney(id);setJourneyStep(0);}
 const activeJourney=network?.journeys.find(j=>j.ordinal===journey);
 const focus=activeJourney?network?.articles.find(a=>a.id===activeJourney.record.ids[journeyStep])?.location:undefined;
 function applyTime(e:FormEvent){e.preventDefault();setPlaying(false);try{const as_of=yearValue(year,era);setTheme('all');setTime({as_of,certainty});setTimeLabel(year.trim()+(era==='BCE'?' ق.م':' م'));setTimeError('');resetSelection();}catch(err){setTimeError((err as Error).message);}}
 function clearTime(){setTheme('all');setPlaying(false);setTime({});setYear('');setTimeLabel('');setTimeError('');resetSelection();}
 function moveTime(delta:bigint){
 if(!time.as_of)return;
 const a=BigInt(time.as_of)+delta;
 if(a>YEAR_LIMIT||a< -YEAR_LIMIT){setPlaying(false);setTimeError('السنة خارج نطاق التخزين.');return;}
 const d=displayYear(a);setYear(d.year);setEra(d.era);setTimeLabel(d.year+(d.era==='BCE'?' ق.م':' م'));setTimeError('');
 setTime({as_of:a.toString(),certainty:time.certainty??'any'});resetSelection();
 }
 useEffect(()=>{
 if(!playing||!time.as_of||mapLoading)return;
 const timer=window.setTimeout(()=>moveTime(BigInt(step)),1800);
 return ()=>window.clearTimeout(timer);
 },[playing,time,step,mapLoading]);
 useEffect(()=>{
 const close=(e:KeyboardEvent)=>{if(e.key==='Escape'){setPanel(null);setPlaying(false);}};
 window.addEventListener('keydown',close);return ()=>window.removeEventListener('keydown',close);
 },[]);
 function chooseTheme(v:string){clearTime();setTheme(v);setJourney(null);setJourneyStep(0);setRoutePath(null);setTopicSelected(null);setCompare(null);}
 const snapshotYear=time.as_of?snapshots.find(s=>(s.year<0?s.year+1:s.year).toString()===time.as_of)?.year??null:null;
 const primary=useMemo(()=>territoryLayer?snapshots.filter(s=>s.year===snapshotYear):[],[territoryLayer,snapshots,snapshotYear]);
 const comparison=useMemo(()=>primary.some(s=>s.type==='territory')&&compare!==snapshotYear?snapshots.filter(s=>s.type==='territory'&&s.year===compare):[],[primary,compare,snapshotYear,snapshots]);
 function chooseSnapshot(y:number|null){setTheme('all');setCompare(null);setTerritorySelected(null);setPlaying(false);resetSelection();if(y===null){clearTime();return;}const d=displayYear(BigInt(y<0?y+1:y));setYear(d.year);setEra(d.era);setTimeLabel(d.year+(d.era==='BCE'?' ق.م':' م'));setTime({as_of:(y<0?y+1:y).toString(),certainty:'any'});setCertainty('any');}
 function chooseTerritory(id:string|null){setTerritorySelected(id);setPanel('territories');}
 useEffect(()=>{setTerritorySelected(id=>id&&snapshots.some(s=>s.year===snapshotYear&&(s.type==='territory'?s.record.id:'milestone:'+s.year)===id)?id:null);if(snapshotYear===null||!snapshots.some(s=>s.year===snapshotYear&&s.type==='territory'))setCompare(null);else if(compare===snapshotYear)setCompare(null);},[snapshotYear,snapshots,compare]);
 const visibleTopics=useMemo(()=>topicLayer&&!time.as_of?topics.filter(t=>theme==='all'||(t.type==='story'?theme==='islamic':theme==='modern')):[],[topicLayer,time.as_of,topics,theme]);
 const visibleDirectory=useMemo(()=>directoryLayer&&!time.as_of&&sourceEraAllows(directoryCollection,theme)?directoryRows:[],[directoryLayer,time.as_of,directoryCollection,theme,directoryRows]);
 const visibleArticles=useMemo(()=>articleLayer&&!time.as_of?articleRows.filter(a=>theme==='all'||a.eras.includes(theme)):[],[articleLayer,time.as_of,articleRows,theme]);
 const thematicNetwork=useMemo(()=>{if(!network||theme==='all')return network;const nodes=network.articles.filter(a=>a.eras.includes(theme));const ids=new Set(nodes.map(a=>a.id));return {...network,articles:nodes,links:network.links.filter(l=>ids.has(l.record[0])&&ids.has(l.record[1])),journeys:network.journeys.filter(j=>j.record.ids.every(id=>ids.has(id)))};},[network,theme]);
 const cellStats=useMemo(()=>stats(cellData?.cells??[],visibleArticles,visibleDirectory,visibleTopics),[cellData,visibleArticles,visibleDirectory,visibleTopics]);
 const referenceLabels:Record<ExploreHit['kind'],string>={article:'الموسوعة',historical:'المعجم التاريخي',modern:'المواضع المعاصرة',geology:'الجيولوجيا',topic:'الموضوعات الإضافية',snapshot:'لقطة تاريخية'};
 function openReference(hit:ExploreHit){
 setPlaying(false);
 if(hit.kind==='article'){chooseArticle(hit.id);return;}
 if(hit.kind==='topic'){chooseTopic(hit.id);return;}
 if(hit.kind==='geology'){setGeoFilter(defaultGeoFilter);setGeoLayer(true);chooseGeology(hit.id);return;}
 if(hit.kind==='historical'||hit.kind==='modern'){setDirectoryCollection(hit.kind);setDirectoryRegion('');setDirectoryQuery('');setDirectoryLayer(true);chooseDirectory(hit.id);return;}
 if(hit.kind==='snapshot'&&hit.year!==null){setTerritoryLayer(true);chooseSnapshot(hit.year);setTerritorySelected(hit.id);setPanel('territories');return;}
 }
 const undated=time.as_of?'محجوبة في السنة الدقيقة؛ سجلات مرجعية غير مؤرخة.':undefined;
 const modernAllowed=!time.as_of&&(theme==='all'||theme==='modern');
 const dirAllowed=sourceEraAllows(directoryCollection,theme);
 const layerItems:LayerItem[]=[
 {id:'locations',label:'المواضع المعرفية',checked:showLocations,onChange:setShowLocations},
 {id:'labels',label:'أسماء الجغرافيا',checked:geoLabels,onChange:setGeoLabels},
 {id:'articles',label:'علامات الموسوعة',checked:articleLayer,onChange:setArticleLayer,suppressed:undated},
 {id:'topics',label:'علامات الموضوعات الموسعة',checked:topicLayer,onChange:setTopicLayer,suppressed:undated},
 {id:'directory',label:'مواضع المعجم',checked:directoryLayer,onChange:setDirectoryLayer,suppressed:undated??(!dirAllowed?'محجوبة في الحقبة المختارة.':undefined)},
 {id:'links',label:'خطوط العلاقات',checked:showLinks,onChange:setShowLinks,suppressed:undated},
 {id:'routes',label:'مقاطع الطرق التاريخية',checked:routeLayer,onChange:setRouteLayer,suppressed:undated??(!sourceEraAllows('historical',theme)?'محجوبة في الحقبة المختارة.':undefined)},
 {id:'territory',label:'اللقطات السياسية',checked:territoryLayer,onChange:setTerritoryLayer,suppressed:snapshotYear===null?'اختر سنة لقطة أصلية من لوحة النطاقات.':undefined},
 {id:'geology',label:'الجيولوجيا المرجعية',checked:geoLayer,onChange:setGeoLayer},
 {id:'cells',label:'الخلايا التحليلية',checked:cellLayer,onChange:setCellLayer},
 ...([{id:'rivers',label:'خطوط المجاري المائية'},{id:'borders',label:'حدود الدول المرجعية'},{id:'grid',label:'خطوط شبكة الإحداثيات'},{id:'texture',label:'نسيج تظليل الشبكة'},{id:'mini',label:'نافذة الخريطة المصغرة'}] as const).map(item=>({...item,checked:reference[item.id],onChange:(v:boolean)=>setReference(r=>({...r,[item.id]:v})),suppressed:item.id==='borders'&&!modernAllowed?'محجوبة في العرض التاريخي.':item.id==='texture'&&physical!=='hex'?'تظهر في الخلفية السداسية فقط.':undefined}))
 ];
 function resetLayers(){setShowLocations(true);setGeoLabels(true);setArticleLayer(false);setTopicLayer(false);setDirectoryLayer(false);setShowLinks(false);setJourney(null);setRouteLayer(false);setRoutePath(null);setTerritoryLayer(false);setCompare(null);setGeoLayer(false);setCellLayer(false);setPhysical('relief');setReference({rivers:false,borders:false,grid:false,texture:true,mini:true});}
 const visibleData=useMemo(()=>showLocations?data:{...data,features:data.features.filter(f=>f.properties.role!=='location')},[data,showLocations]);
 const places=[...new Map(visibleData.features.map(f=>[f.properties.subject_id,f.properties])).values()];
 const currentName=entity?.names.find(n=>n.lang==='ar')?.name??entity?.names[0]?.name;
 return <div ref={appRef} className="app">
 <a className="skip-link" href="#atlas-search" onClick={e=>{e.preventDefault();document.getElementById('search')?.focus();}}>انتقل إلى البحث</a>
 <header className="masthead"><div className="brand"><span className="mark">S</span><div><span className="eyebrow">SATAC · نموذج تأسيسي v0.14</span><h1>السعودية عبر الزمن، عبر القارات</h1></div></div><button className="fullscreen-toggle" aria-label={full?'إنهاء ملء الشاشة':'ملء الشاشة'} aria-pressed={full} onClick={toggleFull}>{full?'↙':'⛶'}</button><nav className="header-actions" aria-label="أدوات الأطلس"><button aria-expanded={panel==='search'} onClick={()=>setPanel(p=>p==='search'?null:'search')}>استكشف</button><button aria-expanded={panel==='detail'} onClick={()=>setPanel(p=>p==='detail'?null:'detail')}>المعرفة</button><button aria-expanded={panel==='encyclopedia'} onClick={()=>{setPanel(p=>p==='encyclopedia'?null:'encyclopedia');setArticleLayer(true);}}>الموسوعة</button><button aria-expanded={panel==='network'} onClick={()=>{setPanel(p=>p==='network'?null:'network');setShowLinks(true);}}>العلاقات</button><button aria-expanded={panel==='directory'} onClick={()=>{setPanel(p=>p==='directory'?null:'directory');setDirectoryLayer(true);}}>المعجم</button><button aria-expanded={panel==='routes'} onClick={()=>{setPanel(p=>p==='routes'?null:'routes');setRouteLayer(true);}}>الطرق</button><button aria-expanded={panel==='territories'} onClick={()=>{setPanel(p=>p==='territories'?null:'territories');setTerritoryLayer(true);}}>النطاقات</button><button aria-expanded={panel==='geology'} onClick={()=>{setPanel(p=>p==='geology'?null:'geology');setGeoLayer(true);}}>الجيولوجيا</button><button aria-expanded={panel==='cells'} onClick={()=>{setPanel(p=>p==='cells'?null:'cells');setCellLayer(true);}}>التحليل</button><button aria-expanded={panel==='layers'} onClick={()=>setPanel(p=>p==='layers'?null:'layers')}>الطبقات</button><button onClick={()=>setPanel(null)}>الخريطة</button></nav></header>
 <main data-panel={panel??'none'}><section id="atlas-search" className="toolbar" aria-label="أدوات البحث والإصدار">
 <label>الإصدار المعرفي<select aria-label="الإصدار المعرفي" value={release} onChange={e=>{setRelease(e.target.value);setGeoSelected(null);resetSelection();}}>{!release&&<option value="">تحميل الإصدارات</option>}{allReleases.map(r=><option key={r.release_id} value={r.release_id}>{r.is_current?'الإصدار الحالي':r.created_at.slice(0,10)} · {r.release_id.slice(0,8)}</option>)}</select></label>
 <form className="search" onSubmit={e=>{e.preventDefault();setAfter(undefined);setSubmitted(q.trim());setRefKind('all');setPanel('search');}}><label htmlFor="search">البحث عن موضع أو اسم</label><div className="search-row"><input id="search" value={q} onChange={e=>setQ(e.target.value)} placeholder="موضع، مقال، جيولوجيا..." maxLength={120}/><button disabled={!release}>بحث</button></div></form>
 <label>الخلفية<select aria-label="الخلفية الجغرافية" value={physical} onChange={e=>setPhysical(e.target.value as 'relief'|'etopo'|'flat'|'hex')}><option value="relief">التضاريس</option><option value="etopo">الارتفاعات والأعماق</option><option value="flat">الخريطة المبسطة</option><option value="hex">الشبكة السداسية</option></select></label>
 <label className="layer-toggle"><input type="checkbox" checked={geoLabels} onChange={e=>setGeoLabels(e.target.checked)}/> التسميات الجغرافية</label>
 <label className="layer-toggle"><input type="checkbox" checked={showLocations} onChange={e=>setShowLocations(e.target.checked)}/> المواضع</label>
 {releaseError&&<p role="alert">{releaseError}</p>}{fullError&&<p role="status">{fullError}</p>}</section>
 <section className="main-map"><AtlasMap data={visibleData} selected={selected} onSelect={choose} physical={physical} geoLabels={geoLabels} dated={!!time.as_of} modernReference={modernAllowed} reference={reference} onReference={setReference} articles={visibleArticles} selectedArticle={articleSelected} onArticleSelect={chooseArticle} network={!time.as_of?thematicNetwork:null} showLinks={showLinks} journey={journey} focus={panel==='network'?focus:undefined} directory={visibleDirectory} directorySelected={panel==='directory'?directorySelected:null} onDirectorySelect={chooseDirectory} routes={routeLayer&&!time.as_of&&sourceEraAllows('historical',theme)?routes:null} routePath={routePath?.release_id===release?routePath:null} snapshots={primary} comparison={comparison} territorySelected={territorySelected} onTerritorySelect={chooseTerritory} geology={geoRows} geoLabelsEnabled={geoFilter.labels} geoSelected={panel==='geology'?geoSelected:null} onGeoSelect={chooseGeology} cells={cellLayer?cellData:null} cellLens={cellLens} cellStats={cellStats} cellSelected={panel==='cells'?cellSelected:null} onCellSelect={chooseCell} topics={visibleTopics} topicSelected={panel==='extended'?topicSelected:null} onTopicSelect={chooseTopic}/></section>
 <section className="map-status" aria-label="حالة الخريطة"><p role="status" data-testid="feature-count">{mapLoading?'جارٍ تحميل المعالم…':places.length+' مواضع'}</p>
 {mapError&&<p role="alert">{mapError}</p>}{truncated&&<p>عُرضت أول 2000 سجل؛ نتائج إضافية غير معروضة.</p>}{time.as_of&&<p>التأريخ: {timeLabel} · لا تظهر السجلات غير المؤرخة.</p>}
 {!mapLoading&&!mapError&&!places.length&&<p>لا توجد مواضع مطابقة.</p>}</section>
 <section className="timeline" aria-label="الشريط الزمني">
 <div className="thematic-strip" aria-label="الحقب الموضوعية">{thematicEras.map(v=><button key={v} aria-pressed={!time.as_of&&theme===v} onClick={()=>chooseTheme(v)}>{eraLabels[v]}</button>)}</div><div className="time-heading"><strong>{timeLabel||(theme==='all'?'كل الأزمنة':eraLabels[theme]+' · تصنيف موضوعي')}</strong><div className="time-navigation"><button aria-label="الزمن السابق" disabled={!time.as_of||mapLoading} onClick={()=>{setPlaying(false);moveTime(-BigInt(step));}}>←</button><button disabled={!time.as_of} aria-pressed={playing} onClick={()=>setPlaying(p=>!p)}>{playing?'إيقاف':'تشغيل'}</button><button aria-label="الزمن التالي" disabled={!time.as_of||mapLoading} onClick={()=>{setPlaying(false);moveTime(BigInt(step));}}>→</button><label>الخطوة<select aria-label="الخطوة" value={step} onChange={e=>setStep(e.target.value)}><option value="1">سنة</option><option value="10">10 سنوات</option><option value="100">100 سنة</option><option value="1000">1000 سنة</option></select></label></div></div>
 <form className="time-form" onSubmit={applyTime}><label>السنة التاريخية<input aria-label="السنة التاريخية" inputMode="numeric" value={year} onChange={e=>setYear(e.target.value)} placeholder="مثال: 550"/></label>
 <label>التقويم<select aria-label="التقويم" value={era} onChange={e=>setEra(e.target.value)}><option value="CE">ميلادي</option><option value="BCE">قبل الميلاد</option></select></label>
 <label>التطابق<select value={certainty} onChange={e=>setCertainty(e.target.value)}><option value="any">مؤكد ومحتمل</option><option value="certain">مؤكد فقط</option><option value="possible">محتمل فقط</option></select></label>
 <button type="submit" disabled={!release}>تطبيق الزمن</button><button className="secondary" type="button" onClick={clearTime}>كل الأزمنة</button></form>
 <p className="theme-note">الحقبة الموضوعية ليست نطاقًا زمنيًا مثبتًا؛ اختيارها يلغي السنة الدقيقة.</p>{timeError&&<p role="alert">{timeError}</p>}</section>
 <aside aria-label="البحث والمواضع" className="sidebar floating-panel" hidden={panel!=='search'}><button className="panel-close" aria-label="إغلاق البحث" onClick={()=>setPanel(null)}>×</button><h2>استكشف المعرفة</h2>
 {submitted&&<section aria-label="نتائج البحث"><h3>نتائج البحث</h3><p role="status">{searchLoading?'جارٍ البحث…':results.length+' نتائج'}</p>{searchError&&<p role="alert">{searchError}</p>}
 <ul className="items">{results.map(r=><li key={r.version_id}><button aria-pressed={selected===r.entity_id} onClick={()=>choose(r.entity_id)}>{r.name}<small>{r.lang==='ar'?'العربية':'English'}</small></button></li>)}</ul>
 {next&&<button className="secondary" onClick={()=>setAfter(next)}>الصفحة التالية</button>}{after&&<button className="secondary" onClick={()=>setAfter(undefined)}>الصفحة الأولى</button>}</section>}
 {submitted&&<section aria-label="نتائج المحتوى المرجعي"><h3>المحتوى المرجعي</h3><p className="muted">نتائج سياقية من الإصدار نفسه، وليست مطابقة زمنية. فتح لقطة تاريخية ينقل إلى سنتها.</p><label>نوع النتيجة<select aria-label="نوع نتيجة الاستكشاف" value={refKind} onChange={e=>setRefKind(e.target.value)}><option value="all">الكل</option>{Object.entries(referenceLabels).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label>
 <p role="status" data-testid="reference-hit-count">{refHits.filter(h=>refKind==='all'||h.kind===refKind).length} نتائج مرجعية{refTruncated?' · أول 100 نتيجة':''}</p>
 <ul className="items">{refHits.filter(h=>refKind==='all'||h.kind===refKind).map(h=><li key={h.kind+':'+h.id}><button onClick={()=>openReference(h)}>{h.title}<small>{referenceLabels[h.kind]}{h.subtitle?' · '+h.subtitle:''}{h.kind==='snapshot'?' · الانتقال إلى السنة':''}</small></button></li>)}</ul></section>}
 <section aria-label="المواضع الظاهرة"><h3>المواضع الظاهرة على الخريطة</h3>
 <ul className="items">{places.map(p=><li key={p.subject_id}><button aria-pressed={selected===p.subject_id} onClick={()=>choose(p.subject_id)}>{p.name??p.subject_id}<small>{p.precision}</small></button></li>)}</ul></section></aside>
 <aside className="detail floating-panel" hidden={panel!=='detail'} aria-label="تفاصيل الكيان"><button className="panel-close" aria-label="إغلاق المعرفة" onClick={()=>setPanel(null)}>×</button><h2>بطاقة المعرفة</h2>
 {!selected&&<p className="muted">اختر موضعًا من الخريطة أو نتائج البحث لاستعراض أسمائه ومراجعه المتاحة.</p>}
 {detailLoading&&<p role="status">جارٍ تحميل التفاصيل…</p>}{detailError&&<p role="alert">{detailError}</p>}
 {entity&&<article><p className="eyebrow">أسماء منشورة في الإصدار</p><h3>{currentName}</h3><ul className="names">{entity.names.map(n=><li key={n.version_id} lang={n.lang} dir="auto">{n.name}</li>)}</ul>
 {claim?.scientific_note&&<p className="note">{claim.scientific_note}</p>}
 {!!claim?.references?.length&&<section><h3>المراجع المتاحة</h3><ul>{claim.references.map((r,i)=><li key={r.source_version_id+i}>{r.title}{r.locator&&<small>{r.locator}</small>}</li>)}</ul></section>}</article>}</aside><div hidden={panel!=='encyclopedia'}><Encyclopedia era={theme} onEra={chooseTheme} extendedCount={topics.length} onExtended={()=>chooseTopic(null)} release={release} selected={articleSelected} onSelect={setArticleSelected} onClose={()=>setPanel(null)} onAnchors={setArticleRows} dated={!!time.as_of} showAnchors={articleLayer} setShowAnchors={setArticleLayer}/></div><div hidden={panel!=='network'}><Network data={thematicNetwork} journey={journey} step={journeyStep} onJourney={selectJourney} onStep={setJourneyStep} onArticle={chooseArticle} links={showLinks} onLinks={setShowLinks} dated={!!time.as_of} onClose={()=>setPanel(null)} error={networkError}/></div><div hidden={panel!=='directory'}><Directory thematicEligible={sourceEraAllows(directoryCollection,theme)} topics={topics} onTopic={chooseTopic} entries={directory} collection={directoryCollection} onCollection={setDirectoryCollection} region={directoryRegion} onRegion={setDirectoryRegion} q={directoryQuery} onQ={setDirectoryQuery} selected={directorySelected} onSelect={chooseDirectory} dated={!!time.as_of} error={directoryError} onClose={()=>{setPanel(null);setDirectoryLayer(false);}}/></div><div hidden={panel!=='routes'}><Routes thematicEligible={sourceEraAllows('historical',theme)} errorMessage={routeError} network={routes} release={release} show={routeLayer} onShow={setRouteLayer} path={routePath} onPath={setRoutePath} dated={!!time.as_of} onClose={()=>{setPanel(null);setRouteLayer(false);}}/></div><div hidden={panel!=='territories'}><Territories records={snapshots} year={snapshotYear} compare={compare} onYear={chooseSnapshot} onCompare={setCompare} selected={territorySelected} onSelect={chooseTerritory} error={snapshotError} onClose={()=>{setPanel(null);setTerritoryLayer(false);setCompare(null);}}/></div><div hidden={panel!=='geology'}><Geology data={geology} filter={geoFilter} onFilter={setGeoFilter} selected={geoSelected} onSelect={chooseGeology} error={geoError} onClose={()=>{setPanel(null);setGeoLayer(false);}}/></div><div hidden={panel!=='cells'}><Cells data={cellData} lens={cellLens} onLens={setCellLens} selected={cellSelected} onSelect={chooseCell} stats={cellStats} dated={!!time.as_of} error={cellError} onClose={()=>{setPanel(null);setCellLayer(false);}} onArticle={chooseArticle} onDirectory={chooseDirectory} onProvince={cellProvince} onTopic={chooseTopic}/></div><div hidden={panel!=='extended'}><ExtendedTopics topics={topics} selected={topicSelected} onSelect={setTopicSelected} show={topicLayer} onShow={setTopicLayer} dated={!!time.as_of} onClose={()=>{setTopicLayer(false);setPanel(null);}} onBack={()=>setPanel('encyclopedia')} error={topicError}/></div><div hidden={panel!=='layers'}><LayerPanel items={layerItems} onClose={()=>setPanel(null)} onReset={resetLayers} collection={directoryCollection} onCollection={v=>{setDirectoryCollection(v);setDirectoryRegion('');setDirectoryQuery('');setDirectorySelected(null);}}/></div></main></div>;
}
createRoot(document.getElementById('root')!).render(<App/>);
