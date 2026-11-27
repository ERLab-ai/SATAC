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

export type ArticleSummary={id:string;title:string;subtitle:string;category:string;art:string;eras:string[];location:[number,number];summary:string;short_name?:string;heritage_status?:string};
export type ArticleDetail=ArticleSummary & {sections:{title:string;text:string}[];bibliography:{id:string;title:string;url:string}[];related:string[]};

export type EditorialNetwork={release_id:string;geometry_semantics:'editorial_connections_not_routes';articles:Pick<ArticleSummary,'id'|'title'|'location'|'art'|'eras'>[];links:{ordinal:number;record:[string,string,string,string?]}[];journeys:{ordinal:number;record:{title:string;subtitle:string;art:string;ids:string[]}}[]};

export type DirectoryEntry={entity_id:string;collection:'historical'|'modern';region_label:string;record:{id:string|number;name:string;en?:string;lon:number;lat:number;region:string|number;kind?:string;source_certainty?:string;source_url?:string;source_uri?:string;source_blob_sha?:string;rank?:number};references:{source_version_id:string;title:string;locator?:string}[]};

export type RouteNetwork={release_id:string;segments:{id:string;from_id:string;to_id:string;meters:number;coordinates:[number,number][]}[];nodes:{id:string;name:string}[]};
export type RoutePath={release_id:string;meters:number;steps:{id:string;from_id:string;to_id:string;reversed:boolean}[]};

export type Snapshot={type:'territory';year:number;record:{id:string;name:string;source_name:string;subject:string;kind:'polity'|'region'|'dependency';border_precision:number;geometry:import('geojson').Polygon|import('geojson').MultiPolygon;label:[number,number];browse_url:string;source_blob_sha:string}}|{type:'milestone';year:number;record:{title:string;place:string;p:[number,number];article:string;text:string}};

export type GeologyRecord={type:'province';reference:string;simplification_deg:number;record:{id:number;name:string;en:string;kind:'shield'|'basin'|'volcanic'|'structure'|'other';ring:[number,number][];anchor:[number,number]}}|{type:'volcano';record:{id:string;name:string;en:string;lon:number;lat:number;elevation:number|null;period:'holocene'|'pleistocene';last:string;summary:string;source:string}};
export type GeologyData={release_id:string;records:GeologyRecord[];volcano_provinces:Record<string,number[]>};

export type CellMetric={id:string;c:number;t:number;radius:number;area_km2:number;water_km:number;province_ids:number[]};
export type CellData={release_id:string;cells:CellMetric[];provinces:{id:number;name:string}[];truncated:boolean};

export type ExtendedTopic=({type:'story';record:{title:string;lead:string;sections:[string,string][];sources:[string,string][]}}|{type:'geosite';record:{id:string;name:string;anchor:string;lon:number;lat:number;area:number;age:string;summary:string;context:string;source:string}})&{id:string;location:[number,number]|null;directory_entity_id:string|null};

export type ExploreHit={kind:'article'|'historical'|'modern'|'geology'|'topic'|'snapshot';id:string;title:string;subtitle:string|null;year:number|null};
