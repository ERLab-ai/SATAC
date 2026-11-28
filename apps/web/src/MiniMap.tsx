import {useEffect,useState,type MouseEvent} from 'react';
import type {Feature,MultiPolygon} from 'geojson';
export type Extent={west:number;east:number;south:number;north:number};
export default function MiniMap({extent,onNavigate,onWorld}:{extent:Extent;onNavigate:(lon:number,lat:number)=>void;onWorld:()=>void}){
 const [land,setLand]=useState('');
 useEffect(()=>{
 const c=new AbortController();
 fetch('/land.geojson',{signal:c.signal}).then(r=>{if(!r.ok)throw Error('land');return r.json() as Promise<Feature<MultiPolygon>>;}).then(f=>{
 if(c.signal.aborted)return;
 setLand(f.geometry.coordinates.map(poly=>poly.map(ring=>ring.map(([lon,lat],i)=>(i?'L':'M')+(lon+180).toFixed(3)+','+(90-lat).toFixed(3)).join('')+'Z').join('')).join(''));
 }).catch(()=>{});return ()=>c.abort();
 },[]);
 const width=Math.min(360,Math.max(0,extent.east-extent.west));
 const left=((extent.west+180)%360+360)%360;
 const top=90-Math.min(90,extent.north),height=Math.max(0,Math.min(90,extent.north)-Math.max(-90,extent.south));
 const parts=width>=360?[[0,360]]:[[left,Math.min(width,360-left)],...(left+width>360?[[0,left+width-360]]:[])];
 function navigate(e:MouseEvent<SVGSVGElement>){
 const r=e.currentTarget.getBoundingClientRect();
 onNavigate((e.clientX-r.left)/r.width*360-180,Math.max(-85,Math.min(85,90-(e.clientY-r.top)/r.height*180)));
 }
 return <div className="minimap" aria-label="الخريطة المصغرة">
 <svg role="img" aria-label="نطاق عرض الخريطة الحالية" viewBox="0 0 360 180" preserveAspectRatio="none" onClick={navigate}>
 <rect width="360" height="180" fill="#193d50"/><path d={land} fill="#8f9b7b" fillRule="evenodd"/>
 {parts.map(([x,w],i)=><rect key={i} data-testid="mini-extent" x={x} y={top} width={w} height={height} fill="#d1af7240" stroke="#ffe0a1" strokeWidth="2"/>)}</svg>
 <button onClick={onWorld}>عرض العالم</button>
 </div>;
}
