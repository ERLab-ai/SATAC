"""Derive regional visual hex tiles from Basemap rasters & land mask.
Colors are cartographic styling of imagery, not numerical DEM or historical land cover.
Grid uses the existing equirectangular display projection; not equal area.
"""
from pathlib import Path
from PIL import Image
import numpy as np, json, math, base64, io
from PIL import ImageFilter
from mpl_toolkits.basemap import basemap_datadir,_readlsmask
P=Path(__file__).parent
root=Path(basemap_datadir)
relief=np.asarray(Image.open(root/'shadedrelief.jpg').resize((5400,2700))).astype(float)
sat=np.asarray(Image.open(root/'bmng.jpg')).astype(float)
_,_,mask=_readlsmask(grid=5,resolution='l')
# Pointy? flat top layout; 1.0 display units radius (~40 km radius at equator).
r=.72; dy=math.sqrt(3)*r
palette=np.array([[204,180,122],[192,159,105],[174,143,93],[154,124,86],[126,105,78],[106,91,72],[217,194,143],[223,208,162],[173,174,112],[137,155,91],[104,137,88],[76,116,83],[64,100,79],[191,173,145],[157,152,128],[120,126,110],[91,109,100]])
water=['#173d50','#1e4a5e','#2b6475','#488a97']
from collections import defaultdict
paths=defaultdict(list); count=0; landcount=0; tiles=[]
# 18–78 E / 0–46 N. Center-of-cell water mask, so coast is intentionally generalized.
for col in range(math.floor(510/(1.5*r)),math.ceil(765/(1.5*r))):
 x=col*1.5*r
 for row in range(math.floor(95/dy),math.ceil(290/dy)):
  y=(row+(col%2)*.5)*dy
  lon=x*360/1000-180;lat=90-y*180/500
  ix=int((lon+180)*12);iy=int((lat+90)*12)
  if not(0<=ix<4320 and 0<=iy<2160):continue
  land=mask[iy,ix]==1
  ri=int(y*2700/500);ci=int(x*5400/1000)
  a=relief[max(0,ri-2):ri+3,max(0,ci-2):ci+3].mean(axis=(0,1)); b=sat[max(0,ri-2):ri+3,max(0,ci-2):ci+3].mean(axis=(0,1))
  if land:
   # Earth-tone stylization of source pixels, with greens driven by observed color, not inferred vegetation type.
   v=.62*a+.38*b
   v=v*.89+np.array([24,17,3])
   if b[1]>b[0]*1.05: v=.6*v+.4*np.array([114,151,94])
   if b[0]>b[2]*1.22 and b[1]<b[0]*.98: v=.8*v+.2*np.array([215,173,104])
   k=int(np.argmin(((palette-v)**2).sum(1))); color='#%02x%02x%02x'%tuple(palette[k]);landcount+=1
   tiles.append([round(x,3),round(y,3),k])
  else:
   coast=np.any(mask[max(0,iy-3):iy+4,max(0,ix-3):ix+4]==1)
   color=water[2 if coast else 0 if a[0]<100 else 1]
  pts=[(x+r*math.cos(i*math.pi/3),y+r*math.sin(i*math.pi/3)) for i in range(6)]
  paths[color].append('M'+'L'.join(f'{a:.3f},{b:.3f}' for a,b in pts)+'Z');count+=1
D={'paths':[[k,''.join(v)] for k,v in paths.items()],'land':tiles,'count':count,'landCount':landcount,'radius':r,'bbox':[510,95,765,290]}
# Recover local shading directly from the shaded-relief image, without interpreting colors as elevation.
# Use a land-masked signed luminance residual to preserve the real mountain and valley textures.
from PIL import ImageOps
bounds=D['bbox']; x0,y0,x1,y1=bounds
img=Image.open(root/'shadedrelief.jpg').crop((int(x0*10.8),int(y0*10.8),int(x1*10.8),int(y1*10.8))).convert('L')
small=img.filter(ImageFilter.GaussianBlur(14))
delta=np.asarray(img,dtype=float)-np.asarray(small,dtype=float)
xx=np.clip(((np.arange(img.width)+.5)/img.width*(x1-x0)+x0)*4320/1000,0,4319).astype(int)
yy=np.clip((500-((np.arange(img.height)+.5)/img.height*(y1-y0)+y0))*2160/500,0,2159).astype(int)
landmask=mask[yy[:,None],xx[None,:]]==1
rgba=np.empty((img.height,img.width,4),dtype=np.uint8)
rgba[:,:,:3]=np.where(delta[:,:,None]>0,np.array([255,239,199]),np.array([28,31,29]))
rgba[:,:,3]=np.minimum(180, np.abs(delta)*5.2).astype(np.uint8)*landmask
buf=io.BytesIO();Image.fromarray(rgba).save(buf,'WEBP',quality=85,method=4);D['texture']='data:image/webp;base64,'+base64.b64encode(buf.getvalue()).decode()
(P/'data/worldtiles.json').write_text(json.dumps(D,separators=(',',':')))
print(count,landcount,len(paths))
