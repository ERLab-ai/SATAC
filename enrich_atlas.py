from pathlib import Path
import csv,json
p=Path(__file__).parent
rows=[]
for id,name,lon,lat,region,kind in csv.reader((p/'data/gazetteer.tsv').open(),delimiter='\t'):
 rows.append(dict(id=id,name=name,lon=float(lon),lat=float(lat),region=region,kind=kind,source_certainty='certain'))
(p/'data/gazetteer.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
