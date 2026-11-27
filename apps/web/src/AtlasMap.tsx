import {useEffect,useRef,useState} from 'react';
import maplibregl,{type GeoJSONSource} from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type {Features,ArticleSummary,EditorialNetwork,DirectoryEntry,RouteNetwork,RoutePath,Snapshot,GeologyRecord,CellData} from './api';
import type {FeatureCollection,LineString} from 'geojson';
import {snapshotId,yearText} from './Territories';
import {geoId,geoKinds} from './Geology';
import {atCell,ring,center,cellBin,colors,lensNames,type Lens,type CellStats} from './Cells';
import {symbols} from './Encyclopedia';
import MiniMap,{type Extent} from './MiniMap';
type GeoLabel=[string,number,number,'water'|'land'|'city',number];
export default function AtlasMap({data,selected,onSelect,physical,geoLabels,dated,articles,selectedArticle,onArticleSelect,network,showLinks,journey,focus,directory,directorySelected,onDirectorySelect,routes,routePath,snapshots,comparison,territorySelected,onTerritorySelect,geology,geoLabelsEnabled,geoSelected,onGeoSelect,cells,cellLens,cellStats,cellSelected,onCellSelect}:{data:Features;selected:string|null;onSelect:(id:string)=>void;physical:'relief'|'etopo'|'flat'|'hex';geoLabels:boolean;dated:boolean;articles:ArticleSummary[];selectedArticle:string|null;onArticleSelect:(id:string)=>void;network:EditorialNetwork|null;showLinks:boolean;journey:number|null;focus:[number,number]|undefined;directory:DirectoryEntry[];directorySelected:string|null;onDirectorySelect:(id:string)=>void;routes:RouteNetwork|null;routePath:RoutePath|null;snapshots:Snapshot[];comparison:Snapshot[];territorySelected:string|null;onTerritorySelect:(id:string)=>void;geology:GeologyRecord[];geoLabelsEnabled:boolean;geoSelected:string|null;onGeoSelect:(id:string)=>void;cells:CellData|null;cellLens:Lens;cellStats:CellStats;cellSelected:string|null;onCellSelect:(id:string)=>void}){
 const node=useRef<HTMLDivElement>(null),map=useRef<maplibregl.Map|null>(null),select=useRef(onSelect);
 select.current=onSelect;
 const cellSelect=useRef(onCellSelect);cellSelect.current=onCellSelect;
 const geoSelect=useRef(onGeoSelect);geoSelect.current=onGeoSelect;
 const territorySelect=useRef(onTerritorySelect);territorySelect.current=onTerritorySelect;
 const directorySelect=useRef(onDirectorySelect);directorySelect.current=onDirectorySelect;
 const articleSelect=useRef(onArticleSelect);articleSelect.current=onArticleSelect;
 const [rivers,setRivers]=useState(false),[mini,setMini]=useState(true),[extent,setExtent]=useState<Extent>({west:30,east:55,south:10,north:40});
 const [ready,setReady]=useState(false),[failed,setFailed]=useState(false),[labels,setLabels]=useState<GeoLabel[]>([]);
 useEffect(()=>{const c=new AbortController();fetch('/physical/labels.json',{signal:c.signal}).then(r=>{if(!r.ok)throw Error('labels');return r.json();}).then(setLabels).catch(()=>{if(!c.signal.aborted)setFailed(true);});return ()=>c.abort();},[]);
 useEffect(()=>{
 if(!node.current)return;
 let m:maplibregl.Map;
 try{m=new maplibregl.Map({container:node.current,center:[42,24],zoom:4,minZoom:1,maxZoom:14,renderWorldCopies:false,attributionControl:false,
 style:{version:8,sources:{land:{type:'geojson',data:'/land.geojson'},relief:{type:'raster',tiles:[location.origin+'/physical/relief/{z}/{x}/{y}.webp'],tileSize:512,maxzoom:2},etopo:{type:'raster',tiles:[location.origin+'/physical/etopo/{z}/{x}/{y}.webp'],tileSize:512,maxzoom:2},hex:{type:'geojson',data:{type:'FeatureCollection',features:[]}},worldRivers:{type:'geojson',data:{type:'FeatureCollection',features:[]}},regionalRivers:{type:'geojson',data:{type:'FeatureCollection',features:[]}},outsideRivers:{type:'geojson',data:{type:'FeatureCollection',features:[]}},editorial:{type:'geojson',data:{type:'FeatureCollection',features:[]}},directory:{type:'geojson',data:{type:'FeatureCollection',features:[]}},routes:{type:'geojson',data:{type:'FeatureCollection',features:[]}},territories:{type:'geojson',data:{type:'FeatureCollection',features:[]}},geology:{type:'geojson',data:{type:'FeatureCollection',features:[]}},cells:{type:'geojson',data:{type:'FeatureCollection',features:[]}},places:{type:'geojson',data:{type:'FeatureCollection',features:[]}}},
 layers:[
 {id:'water',type:'background',paint:{'background-color':'#193d50'}},
 {id:'land',type:'fill',source:'land',paint:{'fill-color':'#b9a77c','fill-outline-color':'#8b9d85'}},
 {id:'relief',type:'raster',source:'relief',layout:{visibility:'visible'},paint:{'raster-opacity':1,'raster-fade-duration':0}},
 {id:'etopo',type:'raster',source:'etopo',layout:{visibility:'none'},paint:{'raster-opacity':1,'raster-fade-duration':0}},
 {id:'hex',type:'fill',source:'hex',layout:{visibility:'none'},paint:{'fill-color':['get','color'],'fill-outline-color':'#394e4655'}},
 {id:'world-rivers',type:'line',source:'worldRivers',maxzoom:5,layout:{visibility:'none'},paint:{'line-color':'#76bbcf','line-width':0.8}},
 {id:'outside-rivers',type:'line',source:'outsideRivers',minzoom:5,layout:{visibility:'none'},paint:{'line-color':'#76bbcf','line-width':0.8}},
 {id:'regional-rivers',type:'line',source:'regionalRivers',minzoom:5,layout:{visibility:'none'},paint:{'line-color':'#76bbcf','line-width':1.2}},
 {id:'cell-fill',type:'fill',source:'cells',paint:{'fill-color':['get','color'],'fill-opacity':['get','opacity']}},
 {id:'cell-border',type:'line',source:'cells',paint:{'line-color':'#a6b7a0','line-opacity':0.32,'line-width':0.6}},
 {id:'cell-selected',type:'line',source:'cells',filter:['==',['get','selected'],true],paint:{'line-color':'#fff4b8','line-width':3}},
 {id:'geology-fill',type:'fill',source:'geology',paint:{'fill-color':['get','color'],'fill-opacity':['case',['==',['get','selected'],true],0.84,0.55]}},
 {id:'geology-outline',type:'line',source:'geology',paint:{'line-color':['case',['==',['get','selected'],true],'#fff0ba',['get','color']],'line-width':['case',['==',['get','selected'],true],3,1]}},
 {id:'territory-fill',type:'fill',source:'territories',filter:['==',['get','mode'],'primary'],paint:{'fill-color':['match',['get','kind'],'polity','#a68c50','region','#598f85','dependency','#a36f9b','#a68c50'],'fill-opacity':0.36}},
 {id:'territory-border',type:'line',source:'territories',filter:['==',['get','mode'],'primary'],paint:{'line-color':'#e3c98c','line-width':2,'line-dasharray':[2,2]}},
 {id:'territory-comparison',type:'line',source:'territories',filter:['==',['get','mode'],'comparison'],paint:{'line-color':'#a7e3ef','line-width':2.5,'line-dasharray':[4,3]}},
 {id:'editorial-links',type:'line',source:'editorial',filter:['==',['get','kind'],'link'],paint:{'line-color':'#efd394','line-width':2,'line-opacity':0.85,'line-dasharray':[2,3]}},
 {id:'editorial-journey',type:'line',source:'editorial',filter:['==',['get','kind'],'journey'],paint:{'line-color':'#ff9b58','line-width':4,'line-dasharray':[2,2]}},
 {id:'editorial-stops',type:'circle',source:'editorial',filter:['==',['geometry-type'],'Point'],paint:{'circle-radius':6,'circle-color':'#ff9b58','circle-stroke-color':'#fff1d0','circle-stroke-width':2}},
 {id:'route-lines',type:'line',source:'routes',paint:{'line-color':'#bb9460','line-width':2}},
 {id:'route-selected',type:'line',source:'routes',filter:['==',['get','selected'],true],paint:{'line-color':'#ffdb75','line-width':5}},
 {id:'directory-points',type:'circle',source:'directory',paint:{'circle-radius':['interpolate',['linear'],['zoom'],2,3,7,7],'circle-color':['match',['get','collection'],'historical','#e2b77c','#83cadd'],'circle-stroke-color':'#173d50','circle-stroke-width':1.2}},
 {id:'areas',type:'fill',source:'places',filter:['==',['geometry-type'],'Polygon'],paint:{'fill-color':'#b17a3a','fill-opacity':0.35}},
 {id:'lines',type:'line',source:'places',filter:['==',['geometry-type'],'LineString'],paint:{'line-color':'#936629','line-width':3}},
 {id:'points',type:'circle',source:'places',filter:['==',['geometry-type'],'Point'],paint:{'circle-radius':7,'circle-color':'#346b61','circle-stroke-color':'#f0d4a1','circle-stroke-width':2}},
 {id:'selected',type:'circle',source:'places',filter:['all',['==',['geometry-type'],'Point'],['==',['get','subject_id'],'']],paint:{'circle-radius':12,'circle-color':'#e8a547','circle-stroke-color':'#fff','circle-stroke-width':3}}
 ]}});}catch(e){console.error('Map initialization:',e);setFailed(true);return;}
 map.current=m;m.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-left');
 m.addControl(new maplibregl.ScaleControl({unit:'metric'}),'bottom-left');
 const updateExtent=()=>{const b=m.getBounds();setExtent({west:b.getWest(),east:b.getEast(),south:b.getSouth(),north:b.getNorth()});};
 m.on('moveend',updateExtent);m.on('resize',updateExtent);
 m.on('load',()=>{setReady(true);updateExtent();});m.on('error',e=>{console.error('Map error:',e.error);setFailed(true);});
 for(const layer of ['points','selected','areas','lines']){
 m.on('click',layer,e=>{const id=e.features?.[0]?.properties?.subject_id;if(typeof id==='string')select.current(id);});
 m.on('mouseenter',layer,()=>{m.getCanvas().style.cursor='pointer';});m.on('mouseleave',layer,()=>{m.getCanvas().style.cursor='';});
 }
 m.on('click','directory-points',e=>{const id=e.features?.[0]?.properties?.entity_id;if(typeof id==='string')directorySelect.current(id);});
 m.on('mouseenter','directory-points',()=>{m.getCanvas().style.cursor='pointer';});m.on('mouseleave','directory-points',()=>{m.getCanvas().style.cursor='';});
 m.on('click','territory-fill',e=>{const id=e.features?.[0]?.properties?.id;if(typeof id==='string')territorySelect.current(id);});
 m.on('click','geology-fill',e=>{const id=e.features?.[0]?.properties?.id;if(typeof id==='string')geoSelect.current(id);});
 m.on('click','cell-fill',e=>{const id=e.features?.[0]?.properties?.id;if(typeof id==='string')cellSelect.current(id);});
 return ()=>{m.remove();map.current=null;};
 },[]);
 useEffect(()=>{
 if(!ready||!map.current)return;
 for(const id of ['relief','etopo','hex'])map.current.setLayoutProperty(id,'visibility',id===physical?'visible':'none');
 },[ready,physical]);
 const loaded=useRef(new Set<string>());
 useEffect(()=>{
 if(!ready||!map.current)return;
 const m=map.current;
 const load=(id:string,path:string)=>{if(!loaded.current.has(id)){(m.getSource(id) as GeoJSONSource).setData(path);loaded.current.add(id);}};
 if(physical==='hex')load('hex','/physical/hex.geojson');
 if(rivers){load('worldRivers','/physical/worldRivers.geojson');load('regionalRivers','/physical/regionalRivers.geojson');load('outsideRivers','/physical/outsideRivers.geojson');}
 for(const id of ['world-rivers','regional-rivers','outside-rivers'])m.setLayoutProperty(id,'visibility',rivers?'visible':'none');
 },[ready,physical,rivers]);
 useEffect(()=>{
 if(!ready||!map.current||!geoLabels)return;
 const m=map.current;
 let markers:maplibregl.Marker[]=[];
 const draw=()=>{
 markers.forEach(x=>x.remove());markers=[];
 const zoom=m.getZoom(),bounds=m.getBounds(),rects:{x:number;y:number;w:number;h:number}[]=[];
 for(const [name,lon,lat,kind,rank] of [...labels].sort((a,b)=>a[4]-b[4])){
 if((kind==='city'&&dated)||zoom<[1,3,5,7][rank]||!bounds.contains([lon,lat]))continue;
 const pt=m.project([lon,lat]),w=Math.max(40,name.length*8),h=18;
 if(rects.some(r=>Math.abs(r.x-pt.x)<(r.w+w)/2+4&&Math.abs(r.y-pt.y)<h))continue;
 if(data.features.some(f=>{if(f.geometry.type!=='Point')return false;const [x,y]=f.geometry.coordinates,p=m.project([x,y]);return Math.abs(p.x-pt.x)<w/2+45&&Math.abs(p.y-pt.y)<30;}))continue;
 rects.push({x:pt.x,y:pt.y,w,h});
 const el=document.createElement('span');el.className='geo-reference-label '+kind;el.textContent=name;
 el.dataset.kind=kind;
 markers.push(new maplibregl.Marker({element:el,anchor:'center'}).setLngLat([lon,lat]).addTo(m));
 }
 };
 draw();m.on('moveend',draw);m.on('resize',draw);
 return ()=>{m.off('moveend',draw);m.off('resize',draw);markers.forEach(x=>x.remove());};
 },[ready,geoLabels,dated,labels,data]);
 useEffect(()=>{if(ready&&map.current)(map.current.getSource('places') as GeoJSONSource).setData(data);},[data,ready]);
 useEffect(()=>{
 if(!ready||!map.current)return;
 map.current.setFilter('selected',['all',['==',['geometry-type'],'Point'],['==',['get','subject_id'],selected??'']]);
 const f=data.features.find(f=>f.properties.subject_id===selected&&f.geometry.type==='Point');
 if(f?.geometry.type==='Point'){const [lon,lat]=f.geometry.coordinates;map.current.easeTo({center:[lon,lat],zoom:Math.max(5,map.current.getZoom()),duration:0});}
 },[selected,ready,data]);
 useEffect(()=>{
 if(!ready||!map.current||data.features.length>100)return;
 const m=map.current;
 const labels=data.features.flatMap(f=>{
 if(f.geometry.type!=='Point'||!f.properties.name)return [];
 const el=document.createElement('button');el.type='button';el.className='map-label';el.textContent=f.properties.name;
 el.setAttribute('aria-label','موضع '+f.properties.name);
 el.addEventListener('click',e=>{e.stopPropagation();select.current(f.properties.subject_id);});
 const [lon,lat]=f.geometry.coordinates;
 return [new maplibregl.Marker({element:el,anchor:'bottom',offset:[0,-10]}).setLngLat([lon,lat]).addTo(m)];
 });
 return ()=>labels.forEach(l=>l.remove());
 },[data,ready]);
 useEffect(()=>{
 if(!ready||!map.current)return;
 const m=map.current;
 const markers=articles.map(a=>{
 const el=document.createElement('button');el.type='button';el.className='article-marker';el.textContent=symbols[a.art]??'◆';el.title=a.title;el.setAttribute('aria-label','مقال '+a.title);
 el.addEventListener('click',e=>{e.stopPropagation();articleSelect.current(a.id);});
 return new maplibregl.Marker({element:el,anchor:'center'}).setLngLat(a.location).addTo(m);
 });
 return ()=>markers.forEach(x=>x.remove());
 },[ready,articles]);
 useEffect(()=>{
 if(!ready||!map.current)return;const a=articles.find(x=>x.id===selectedArticle);
 if(a)map.current.easeTo({center:a.location,zoom:Math.max(5,map.current.getZoom()),duration:0});
 },[ready,selectedArticle,articles]);
 useEffect(()=>{
 if(!ready||!map.current)return;
 const nodes=new Map(network?.articles.map(a=>[a.id,a.location]));
 const features:FeatureCollection={type:'FeatureCollection',features:[]};
 function line(a:string,b:string,kind:string){const x=nodes.get(a),y=nodes.get(b);if(!x||!y)return;
 const geometry:LineString={type:'LineString',coordinates:[x,y]};
 features.features.push({type:'Feature',geometry,properties:{kind}});}
 if(network&&showLinks)network.links.forEach(l=>line(l.record[0],l.record[1],'link'));
 const j=network?.journeys.find(j=>j.ordinal===journey);
 if(j){j.record.ids.slice(1).forEach((id,i)=>line(j.record.ids[i],id,'journey'));j.record.ids.forEach(id=>{const p=nodes.get(id);if(p)features.features.push({type:'Feature',geometry:{type:'Point',coordinates:p},properties:{kind:'stop'}});});}
 (map.current.getSource('editorial') as GeoJSONSource).setData(features);
 },[ready,network,showLinks,journey]);
 useEffect(()=>{if(ready&&map.current&&network&&focus)map.current.easeTo({center:focus,zoom:Math.max(5,map.current.getZoom()),duration:0});},[ready,network,focus]);
 useEffect(()=>{
 if(!ready||!map.current)return;
 const features:FeatureCollection={type:'FeatureCollection',features:directory.map(x=>({type:'Feature',geometry:{type:'Point',coordinates:[x.record.lon,x.record.lat]},properties:{entity_id:x.entity_id,collection:x.collection}}))};
 (map.current.getSource('directory') as GeoJSONSource).setData(features);
 },[ready,directory]);
 useEffect(()=>{if(!ready||!map.current)return;const x=directory.find(r=>r.entity_id===directorySelected);if(x)map.current.easeTo({center:[x.record.lon,x.record.lat],zoom:Math.max(5,map.current.getZoom()),duration:0});},[ready,directory,directorySelected]);
 useEffect(()=>{
 if(!ready||!map.current)return;
 const chosen=new Set(routePath?.steps.map(s=>s.id));
 const features:FeatureCollection={type:'FeatureCollection',features:(routes?.segments??[]).map(e=>({type:'Feature',geometry:{type:'LineString',coordinates:e.coordinates},properties:{selected:chosen.has(e.id)}}))};
 (map.current.getSource('routes') as GeoJSONSource).setData(features);
 },[ready,routes,routePath]);
 useEffect(()=>{if(!ready||!map.current||!routes||!routePath?.steps.length)return;const ids=new Set(routePath.steps.map(s=>s.id));const points=routes.segments.filter(s=>ids.has(s.id)).flatMap(s=>s.coordinates);if(points.length){const bounds=new maplibregl.LngLatBounds();points.forEach(p=>bounds.extend(p));map.current.fitBounds(bounds,{padding:70,maxZoom:8,duration:0});}},[ready,routes,routePath]);
 useEffect(()=>{
 if(!ready||!map.current)return;const m=map.current;
 const features:FeatureCollection={type:'FeatureCollection',features:[]};
 for(const [rows,mode] of [[snapshots,'primary'],[comparison,'comparison']] as const){for(const s of rows)if(s.type==='territory')features.features.push({type:'Feature',geometry:s.record.geometry,properties:{id:s.record.id,kind:s.record.kind,mode}});}
 (m.getSource('territories') as GeoJSONSource).setData(features);
 const markers=snapshots.map(s=>{const el=document.createElement('button');el.type='button';el.className='territory-label';el.textContent=s.type==='territory'?s.record.name:s.record.place+' · '+yearText(s.year);el.setAttribute('aria-label','لقطة '+(s.type==='territory'?s.record.name:s.record.title));el.addEventListener('click',e=>{e.stopPropagation();territorySelect.current(snapshotId(s));});return new maplibregl.Marker({element:el,anchor:'center'}).setLngLat(s.type==='territory'?s.record.label:s.record.p).addTo(m);});
 return ()=>markers.forEach(x=>x.remove());
 },[ready,snapshots,comparison]);
 useEffect(()=>{if(!ready||!map.current)return;const s=snapshots.find(x=>snapshotId(x)===territorySelected);if(!s)return;
 if(s.type==='milestone'){map.current.easeTo({center:s.record.p,zoom:6,duration:0});return;}
 const g=s.record.geometry,polys=g.type==='Polygon'?[g.coordinates]:g.coordinates;const bounds=new maplibregl.LngLatBounds();for(const poly of polys)for(const ring of poly)for(const p of ring)bounds.extend([p[0],p[1]]);if(!bounds.isEmpty())map.current.fitBounds(bounds,{padding:65,maxZoom:7,duration:0});
 },[ready,territorySelected,snapshots]);
 useEffect(()=>{
 if(!ready||!map.current)return;const m=map.current;
 const features:FeatureCollection={type:'FeatureCollection',features:[]};
 for(const s of geology)if(s.type==='province')features.features.push({type:'Feature',geometry:{type:'Polygon',coordinates:[s.record.ring]},properties:{id:geoId(s),color:geoKinds[s.record.kind][1],selected:geoId(s)===geoSelected}});
 (m.getSource('geology') as GeoJSONSource).setData(features);
 let markers:maplibregl.Marker[]=[];
 const draw=()=>{markers.forEach(x=>x.remove());markers=[];
 const occupied:{x:number;y:number;w:number}[]=[];
 for(const s of geology){
 if(s.type==='province'&&(!geoLabelsEnabled||m.getZoom()<3))continue;
 const p:[number,number]=s.type==='province'?s.record.anchor:[s.record.lon,s.record.lat];
 if(!m.getBounds().contains(p))continue;
 const pt=m.project(p),w=Math.max(40,s.record.name.length*7);
 if(s.type==='province'&&occupied.some(x=>Math.abs(x.x-pt.x)<(x.w+w)/2&&Math.abs(x.y-pt.y)<20))continue;
 occupied.push({x:pt.x,y:pt.y,w});
 const el=document.createElement('button');el.type='button';el.className=s.type==='province'?'geology-label':'volcano-marker '+s.record.period;
 el.textContent=s.type==='province'?s.record.name:'▲ '+s.record.name;el.setAttribute('aria-label','جيولوجيا '+s.record.name);
 el.addEventListener('click',e=>{e.stopPropagation();geoSelect.current(geoId(s));});
 markers.push(new maplibregl.Marker({element:el,anchor:'center'}).setLngLat(p).addTo(m));
 }};
 draw();m.on('moveend',draw);m.on('resize',draw);
 return ()=>{m.off('moveend',draw);m.off('resize',draw);markers.forEach(x=>x.remove());};
 },[ready,geology,geoLabelsEnabled,geoSelected]);
 useEffect(()=>{if(!ready||!map.current)return;const s=geology.find(x=>geoId(x)===geoSelected);if(!s)return;if(s.type==='volcano'){map.current.easeTo({center:[s.record.lon,s.record.lat],zoom:6,duration:0});return;}const bounds=new maplibregl.LngLatBounds();s.record.ring.forEach(p=>bounds.extend(p));if(!bounds.isEmpty())map.current.fitBounds(bounds,{padding:65,maxZoom:7,duration:0});},[ready,geology,geoSelected]);
 useEffect(()=>{
 if(!ready||!map.current)return;
 const features:FeatureCollection={type:'FeatureCollection',features:(cells?.cells??[]).map(c=>{const b=cellBin(c,cellLens,cellStats);return {type:'Feature',geometry:{type:'Polygon',coordinates:[ring(c)]},properties:{id:c.id,color:colors(cellLens)[b],opacity:b===0?.23:.75,selected:c.id===cellSelected}};})};
 (map.current.getSource('cells') as GeoJSONSource).setData(features);
 },[ready,cells,cellLens,cellStats,cellSelected]);
 useEffect(()=>{if(!ready||!map.current)return;const c=cells?.cells.find(x=>x.id===cellSelected);if(c)map.current.easeTo({center:center(c),zoom:Math.max(5,map.current.getZoom()),duration:0});},[ready,cells,cellSelected]);
 return <section className="map-shell" aria-label="الخريطة الجغرافية"><div ref={node} className="map" data-testid="map" data-ready={ready?'true':'false'} dir="ltr"/>
 {failed&&<p className="map-message" role="alert">تعذر عرض جزء من الخريطة. يمكنك استخدام قائمة المواضع.</p>}
 <div className="map-views"><button onClick={()=>map.current?.jumpTo({center:[42,24],zoom:4})}>الجزيرة</button><button onClick={()=>map.current?.jumpTo({center:[0,20],zoom:1})}>العالم</button></div>
 <div className="reference-controls"><button aria-pressed={rivers} onClick={()=>setRivers(v=>!v)}>المجاري المائية</button><button aria-pressed={mini} onClick={()=>setMini(v=>!v)}>الخريطة المصغرة</button></div>
 {mini&&<MiniMap extent={extent} onNavigate={(lon,lat)=>map.current?.jumpTo({center:[lon,lat]})} onWorld={()=>map.current?.jumpTo({center:[0,20],zoom:1})}/>}
 {network&&(showLinks||journey!==null)&&<div className="editorial-legend" data-testid="editorial-legend">خطوط موضوعية · ليست مسارات تاريخية</div>}
 {directory.length>0&&<div className="directory-legend" data-testid="directory-map-count">{directory.length} مواضع مرجعية · {directory[0].collection==='historical'?'المعجم التاريخي':'العينة المعاصرة'}</div>}
 {routes&&<div className="route-legend" data-testid="route-map-count">{routes.segments.length} مقطع من شبكة المصدر</div>}
 {snapshots.length>0&&<div className="territory-legend" data-testid="territory-map-legend">{yearText(snapshots[0].year)} · {snapshots[0].type==='milestone'?'موضع حدث لا حدود دولة':'نطاقات تقريبية من المصدر'}{comparison.length>0&&` · الخط السماوي: ${yearText(comparison[0].year)}`}</div>}
 {geology.length>0&&<div className="geology-legend" data-testid="geology-map-legend">جيولوجيا مرجعية معاصرة · USGS / Smithsonian</div>}
 {cells&&<div className="cell-legend" data-testid="cell-map-legend">{lensNames[cellLens]} · {cells.cells.length} خلية <button onClick={()=>{const m=map.current;if(!m)return;const p=m.getCenter(),c=atCell(p.lng,p.lat,cells.cells);if(c)cellSelect.current(c.id);}}>خلية مركز الخريطة</button></div>}
 <div className="map-caption">خلفية جغرافية معاصرة · {physical==='relief'?'تظليل التضاريس':physical==='etopo'?'ألوان الارتفاعات والأعماق':physical==='hex'?'شبكة سداسية إقليمية غير متساوية المساحة':'يابسة ومياه'} · لا تمثل حدودًا تاريخية</div></section>;
}
