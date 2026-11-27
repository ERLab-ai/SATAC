"""Rebuild from installed basemap-data; derived GSHHG vectors retain LGPL-3.0-or-later."""
from pathlib import Path
import json,io,base64
from PIL import Image
import matplotlib
matplotlib.use('Agg')
from mpl_toolkits.basemap import Basemap,basemap_datadir
from shapely.geometry import LineString
P=Path(__file__).parent

def raster(name,quality):
    im=Image.open(Path(basemap_datadir)/(name+'.jpg')); b=io.BytesIO();im.save(b,'WEBP',quality=quality,method=4);return 'data:image/webp;base64,'+base64.b64encode(b.getvalue()).decode()
def paths(lines,tol,minlen=0):
    out=[]
    for line in lines:
        if len(line)<2:continue
        g=LineString(line)
        if g.length<minlen:continue
        coords=list(g.simplify(tol).coords)
        out.append(' '.join(('M' if i==0 else 'L')+f'{(x+180)*1000/360:.3f},{(90-y)*500/180:.3f}' for i,(x,y) in enumerate(coords)))
    return out
m=Basemap(projection='cyl',resolution='l');m.drawrivers();m.drawcountries()
r=Basemap(projection='cyl',resolution='i',llcrnrlon=18,llcrnrlat=0,urcrnrlon=75,urcrnrlat=45);r.drawrivers();r.drawcountries()
# Geographic reference labels, not historical events; approximate geographic centers.
labels=[]
for line in '''البحر الأحمر|39|19|water|1
الخليج العربي|51|27|water|1
بحر العرب|61|15|water|1
البحر المتوسط|22|35|water|1
خليج عدن|47|12|water|2
خليج عُمان|58|24|water|2
المحيط الهندي|77|-12|water|0
المحيط الأطلسي|-35|18|water|0
المحيط الهادئ|-145|8|water|0
بحر قزوين|51|42|water|1
البحر الأسود|34|43|water|1
الربع الخالي|50|19.5|land|1
النفود الكبير|41|28.8|land|2
الدهناء|46.7|26.8|land|2
جبال السروات|41.6|18.8|land|2
جبال الحجاز|39.8|24.6|land|2
نجد|44.6|24.1|land|1
تهامة|40.3|17.1|land|2
جبال زاغروس|49|32|land|1
جبال طوروس|35|37|land|2
الصحراء الكبرى|15|24|land|0
وادي النيل|31.5|24.5|land|2
دلتا النيل|31|31|land|2
نهر الفرات|41.1|35.2|water|2
نهر دجلة|44.2|35.3|water|2
وادي الرمة|43.4|26.1|land|3
وادي الدواسر|45|20.5|land|3
آسيا|85|49|land|0
أفريقيا|20|3|land|0
أوروبا|18|51|land|0
أمريكا الشمالية|-105|45|land|0
أمريكا الجنوبية|-58|-15|land|0
أستراليا|134|-24|land|0
تبوك|36.57|28.38|city|2
تيماء|38.54|27.62|city|2
دومة الجندل|39.87|29.81|city|2
سكاكا|40.2|29.97|city|2
ينبع|38.06|24.09|city|2
الوجه|36.46|26.24|city|3
ضباء|35.69|27.35|city|3
بدر|38.79|23.78|city|3
الطائف|40.42|21.27|city|2
أبها|42.50|18.22|city|2
جازان|42.55|16.89|city|2
نجران|44.13|17.49|city|2
بريدة|43.98|26.36|city|2
عنيزة|43.99|26.09|city|3
الدمام|50.10|26.43|city|2
القطيف|50.01|26.57|city|3
الجبيل|49.66|27.01|city|3
حفر الباطن|45.96|28.43|city|2
عرعر|41.04|30.98|city|2
رفحاء|43.49|29.62|city|3
القريات|37.34|31.33|city|3
بيشة|42.61|20.00|city|3
الباحة|41.47|20.01|city|3
القاهرة|31.24|30.04|city|1
الإسكندرية|29.92|31.20|city|2
دمشق|36.29|33.51|city|1
عمّان|35.93|31.95|city|2
القدس|35.22|31.78|city|2
بيروت|35.50|33.89|city|2
بغداد|44.36|33.31|city|1
البصرة|47.81|30.51|city|2
الموصل|43.12|36.34|city|2
الكويت|47.98|29.38|city|2
المنامة|50.58|26.23|city|2
الدوحة|51.53|25.29|city|2
أبوظبي|54.37|24.45|city|2
دبي|55.27|25.20|city|3
مسقط|58.38|23.59|city|1
صلالة|54.09|17.02|city|2
صنعاء|44.21|15.35|city|1
عدن|45.03|12.8|city|2
المكلا|49.12|14.54|city|2
الخرطوم|32.56|15.50|city|1
بورتسودان|37.22|19.61|city|2
سواكن|37.33|19.11|city|3
جيبوتي|43.15|11.59|city|2
أسمرة|38.93|15.32|city|2
أديس أبابا|38.76|9.03|city|1
مقديشو|45.34|2.05|city|1
مومباي|72.88|19.08|city|1
كراتشي|67.01|24.86|city|1
إسطنبول|28.98|41.01|city|1
روما|12.49|41.90|city|1
أثينا|23.73|37.98|city|1
طهران|51.39|35.69|city|1
زنجبار|39.20|-6.16|city|1
جاكرتا|106.85|-6.21|city|1
ملقا|102.25|2.19|city|1'''.splitlines():
    n,x,y,k,z=line.split('|');labels.append([n,float(x),float(y),k,int(z)])
d={'relief':raster('shadedrelief',82),'etopo':raster('etopo1',80),'worldRivers':paths(m.riversegs,.06,.5),'regionalRivers':paths(r.riversegs,.012,.08),'worldBorders':paths(m.cntrysegs,.045),'regionalBorders':paths(r.cntrysegs,.012),'labels':labels}
(P/'data/geography.json').write_text(json.dumps(d,ensure_ascii=False,separators=(',',':')))
print({k:len(v) for k,v in d.items()})
