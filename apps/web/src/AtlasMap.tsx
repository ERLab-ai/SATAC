import {useEffect,useRef,useState} from 'react';
import maplibregl,{type GeoJSONSource} from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type {Features} from './api';
export default function AtlasMap({data,selected,onSelect}:{data:Features;selected:string|null;onSelect:(id:string)=>void}){
 const node=useRef<HTMLDivElement>(null),map=useRef<maplibregl.Map|null>(null),select=useRef(onSelect);
 select.current=onSelect;
 const [ready,setReady]=useState(false),[failed,setFailed]=useState(false);
 useEffect(()=>{
 if(!node.current)return;
 let m:maplibregl.Map;
 try{m=new maplibregl.Map({container:node.current,center:[42,24],zoom:4,minZoom:1,maxZoom:14,renderWorldCopies:false,attributionControl:false,
 style:{version:8,sources:{land:{type:'geojson',data:'/land.geojson'},places:{type:'geojson',data:{type:'FeatureCollection',features:[]}}},
 layers:[
 {id:'water',type:'background',paint:{'background-color':'#193d50'}},
 {id:'land',type:'fill',source:'land',paint:{'fill-color':'#b9a77c','fill-outline-color':'#8b9d85'}},
 {id:'areas',type:'fill',source:'places',filter:['==',['geometry-type'],'Polygon'],paint:{'fill-color':'#b17a3a','fill-opacity':0.35}},
 {id:'lines',type:'line',source:'places',filter:['==',['geometry-type'],'LineString'],paint:{'line-color':'#936629','line-width':3}},
 {id:'points',type:'circle',source:'places',filter:['==',['geometry-type'],'Point'],paint:{'circle-radius':7,'circle-color':'#346b61','circle-stroke-color':'#f0d4a1','circle-stroke-width':2}},
 {id:'selected',type:'circle',source:'places',filter:['all',['==',['geometry-type'],'Point'],['==',['get','subject_id'],'']],paint:{'circle-radius':12,'circle-color':'#e8a547','circle-stroke-color':'#fff','circle-stroke-width':3}}
 ]}});}catch{setFailed(true);return;}
 map.current=m;m.addControl(new maplibregl.NavigationControl({showCompass:false}),'top-left');
 m.addControl(new maplibregl.ScaleControl({unit:'metric'}),'bottom-left');
 m.on('load',()=>setReady(true));m.on('error',()=>setFailed(true));
 for(const layer of ['points','selected','areas','lines']){
 m.on('click',layer,e=>{const id=e.features?.[0]?.properties?.subject_id;if(typeof id==='string')select.current(id);});
 m.on('mouseenter',layer,()=>{m.getCanvas().style.cursor='pointer';});m.on('mouseleave',layer,()=>{m.getCanvas().style.cursor='';});
 }
 return ()=>{m.remove();map.current=null;};
 },[]);
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
 return <section className="map-shell" aria-label="الخريطة الجغرافية"><div ref={node} className="map" data-testid="map" data-ready={ready?'true':'false'} dir="ltr"/>
 {failed&&<p className="map-message" role="alert">تعذر عرض جزء من الخريطة. يمكنك استخدام قائمة المواضع.</p>}
 <div className="map-views"><button onClick={()=>map.current?.jumpTo({center:[42,24],zoom:4})}>الجزيرة</button><button onClick={()=>map.current?.jumpTo({center:[0,20],zoom:1})}>العالم</button></div>
 <div className="map-caption">خلفية جغرافية معاصرة · لا تمثل حدودًا تاريخية</div></section>;
}
