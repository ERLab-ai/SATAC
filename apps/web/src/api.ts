import type {FeatureCollection, Geometry} from 'geojson';
export type Release={release_id:string;created_at:string;is_current:boolean};
export type Name={claim_id:string;version_id:string;name:string;lang:string};
export type SearchResult=Name & {entity_id:string;kind:string};
export type Entity={entity_id:string;release_id:string;kind:string;names:Name[]};
export type Claim={scientific_note?:string;references?:{source_version_id:string;title:string;locator?:string}[]};
export type Props={claim_id:string;version_id:string;subject_id:string;name?:string;role:string;precision:string};
export type Features=FeatureCollection<Geometry,Props>;
export type TimeFilter={as_of?:string;certainty?:string};
export const emptyFeatures=():Features=>({type:'FeatureCollection',features:[]});
export async function get<T>(path:string,params:Record<string,string|undefined>={},signal?:AbortSignal):Promise<T>{
 const query=new URLSearchParams();
 for(const [key,value] of Object.entries(params)) if(value!==undefined) query.set(key,value);
 const response=await fetch(path+(query.size?'?'+query.toString():''),{signal,cache:'no-store'});
 if(!response.ok) throw new Error('HTTP '+response.status);
 return response.json() as Promise<T>;
}
export async function releases(signal:AbortSignal){
 const result:Release[]=[];let after:string|undefined;
 do{const page:{releases:Release[];next_after:string|null}=await get('/api/v1/releases',{limit:'200',after},signal);
 result.push(...page.releases);after=page.next_after??undefined;}while(after);
 return result;
}
export async function mapFeatures(release:string,time:TimeFilter,signal:AbortSignal){
 const data=emptyFeatures();let after:string|undefined;
 for(let page=0;page<10;page++){
 const response:Features & {next_after:string|null}=await get('/api/v1/map/features',{release,bbox:'-180,-85,180,85',limit:'200',after,...time},signal);
 data.features.push(...response.features);after=response.next_after??undefined;
 if(!after)return {data,truncated:false};
 }
 return {data,truncated:true};
}
