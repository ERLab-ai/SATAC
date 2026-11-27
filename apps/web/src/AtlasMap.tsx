import {useEffect,useRef,useState} from 'react';
import maplibregl,{type GeoJSONSource} from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type {Features,ArticleSummary} from './api';
import {symbols} from './Encyclopedia';
import MiniMap,{type Extent} from './MiniMap';
type GeoLabel=[string,number,number,'water'|'land'|'city',number];
export default function AtlasMap({data,selected,onSelect,physical,geoLabels,dated,articles,selectedArticle,onArticleSelect}:{data:Features;selected:string|null;onSelect:(id:string)=>void;physical:'relief'|'etopo'|'flat'|'hex';geoLabels:boolean;dated:boolean;articles:ArticleSummary[];selectedArticle:string|null;onArticleSelect:(id:string)=>void}){
 const node=useRef<HTMLDivElement>(null),map=useRef<maplibregl.Map|null>(null),select=useRef(onSelect);
 select.current=onSelect;
 const articleSelect=useRef(onArticleSelect);articleSelect.current=onArticleSelect;
 const [rivers,setRivers]=useState(false),[mini,setMini]=useState(true),[extent,setExtent]=useState<Extent>({west:30,east:55,south:10,north:40});
 const [ready,setReady]=useState(false),[failed,setFailed]=useState(false),[labels,setLabels]=useState<GeoLabel[]>([]);
 useEffect(()=>{const c=new AbortController();fetch('/physical/labels.json',{signal:c.signal}).then(r=>{if(!r.ok)throw Error('labels');return r.json();}).then(setLabels).catch(()=>{if(!c.signal.aborted)setFailed(true);});return ()=>c.abort();},[]);
 useEffect(()=>{
 if(!node.current)return;
 let m:maplibregl.Map;
 try{m=new maplibregl.Map({container:node.current,center:[42,24],zoom:4,minZoom:1,maxZoom:14,renderWorldCopies:false,attributionControl:false,
 style:{version:8,sources:{land:{type:'geojson',data:'/land.geojson'},relief:{type:'raster',tiles:[location.origin+'/physical/relief/{z}/{x}/{y}.webp'],tileSize:512,maxzoom:2},etopo:{type:'raster',tiles:[location.origin+'/physical/etopo/{z}/{x}/{y}.webp'],tileSize:512,maxzoom:2},hex:{type:'geojson',data:{type:'FeatureCollection',features:[]}},worldRivers:{type:'geojson',data:{type:'FeatureCollection',features:[]}},regionalRivers:{type:'geojson',data:{type:'FeatureCollection',features:[]}},outsideRivers:{type:'geojson',data:{type:'FeatureCollection',features:[]}},places:{type:'geojson',data:{type:'FeatureCollection',features:[]}}},
 layers:[
 {id:'water',type:'background',paint:{'background-color':'#193d50'}},
 {id:'land',type:'fill',source:'land',paint:{'fill-color':'#b9a77c','fill-outline-color':'#8b9d85'}},
 {id:'relief',type:'raster',source:'relief',layout:{visibility:'visible'},paint:{'raster-opacity':1,'raster-fade-duration':0}},
 {id:'etopo',type:'raster',source:'etopo',layout:{visibility:'none'},paint:{'raster-opacity':1,'raster-fade-duration':0}},
 {id:'hex',type:'fill',source:'hex',layout:{visibility:'none'},paint:{'fill-color':['get','color'],'fill-outline-color':'#394e4655'}},
 {id:'world-rivers',type:'line',source:'worldRivers',maxzoom:5,layout:{visibility:'none'},paint:{'line-color':'#76bbcf','line-width':0.8}},
 {id:'outside-rivers',type:'line',source:'outsideRivers',minzoom:5,layout:{visibility:'none'},paint:{'line-color':'#76bbcf','line-width':0.8}},
 {id:'regional-rivers',type:'line',source:'regionalRivers',minzoom:5,layout:{visibility:'none'},paint:{'line-color':'#76bbcf','line-width':1.2}},
 {id:'areas',type:'fill',source:'places',filter:['==',['geometry-type'],'Polygon'],paint:{'fill-color':'#b17a3a','fill-opacity':0.35}},
 {id:'lines',type:'line',source:'places',filter:['==',['geometry-type'],'LineString'],paint:{'line-color':'#936629','line-width':3}},
 {id:'points',type:'circle',source:'places',filter:['==',['geometry-type'],'Point'],paint:{'circle-radius':7,'circle-color':'#346b61','circle-stroke-color':'#f0d4a1','circle-stroke-width':2}},
 {id:'selected',type:'circle',source:'places',filter:['all',['==',['geometry-type'],'Point'],['==',['get','subject_id'],'']],paint:{'circle-radius':12,'circle-color':'#e8a547','circle-stroke-color':'#fff','circle-stroke-width':3}}
 ]}});}catch{setFailed(true);return;}
 map.current=m;m.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-left');
 m.addControl(new maplibregl.ScaleControl({unit:'metric'}),'bottom-left');
 const updateExtent=()=>{const b=m.getBounds();setExtent({west:b.getWest(),east:b.getEast(),south:b.getSouth(),north:b.getNorth()});};
 m.on('moveend',updateExtent);m.on('resize',updateExtent);
 m.on('load',()=>{setReady(true);updateExtent();});m.on('error',()=>setFailed(true));
 for(const layer of ['points','selected','areas','lines']){
 m.on('click',layer,e=>{const id=e.features?.[0]?.properties?.subject_id;if(typeof id==='string')select.current(id);});
 m.on('mouseenter',layer,()=>{m.getCanvas().style.cursor='pointer';});m.on('mouseleave',layer,()=>{m.getCanvas().style.cursor='';});
 }
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
 return <section className="map-shell" aria-label="الخريطة الجغرافية"><div ref={node} className="map" data-testid="map" data-ready={ready?'true':'false'} dir="ltr"/>
 {failed&&<p className="map-message" role="alert">تعذر عرض جزء من الخريطة. يمكنك استخدام قائمة المواضع.</p>}
 <div className="map-views"><button onClick={()=>map.current?.jumpTo({center:[42,24],zoom:4})}>الجزيرة</button><button onClick={()=>map.current?.jumpTo({center:[0,20],zoom:1})}>العالم</button></div>
 <div className="reference-controls"><button aria-pressed={rivers} onClick={()=>setRivers(v=>!v)}>المجاري المائية</button><button aria-pressed={mini} onClick={()=>setMini(v=>!v)}>الخريطة المصغرة</button></div>
 {mini&&<MiniMap extent={extent} onNavigate={(lon,lat)=>map.current?.jumpTo({center:[lon,lat]})} onWorld={()=>map.current?.jumpTo({center:[0,20],zoom:1})}/>}
 <div className="map-caption">خلفية جغرافية معاصرة · {physical==='relief'?'تظليل التضاريس':physical==='etopo'?'ألوان الارتفاعات والأعماق':physical==='hex'?'شبكة سداسية إقليمية غير متساوية المساحة':'يابسة ومياه'} · لا تمثل حدودًا تاريخية</div></section>;
}
