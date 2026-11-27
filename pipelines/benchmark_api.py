"""Loopback HTTP performance baseline; no production writes or external traffic."""
import argparse
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID

import httpx
import psycopg

SCALE_RELEASE = "eeee0000-0000-4000-8000-000000000003"

def percentile(samples, p):
    if not samples:
        raise ValueError("empty sample")
    return sorted(samples)[math.ceil(p*len(samples))-1]

def measure(client, label, path, params, key, expected, count, warmup):
    def request():
        t = time.perf_counter()
        response = client.get(path, params=params)
        elapsed = (time.perf_counter()-t)*1000
        response.raise_for_status()
        body = response.json()
        if body.get("release_id") != params["release"]:
            raise AssertionError("release mismatch")
        value = body[key]
        result = value if isinstance(value, int) else len(value)
        if expected is not None and result != expected:
            raise AssertionError(f"{label}: expected {expected}, got {result}")
        return elapsed, len(response.content), result, body.get("next_after")
    for _ in range(warmup):
        request()
    records = [request() for _ in range(count)]
    times = [r[0] for r in records]
    if len({r[2:] for r in records}) != 1:
        raise AssertionError("result count or cursor drift")
    return {"case":label,"path":path,"parameters":params,"requests":count,"warmup":warmup,
            "p50_ms":round(statistics.median(times),3),"p95_ms":round(percentile(times,.95),3),
            "max_ms":round(max(times),3),"response_bytes":records[0][1],"result_count":records[0][2],
            "has_next_page":records[0][3] is not None,"samples_ms":[round(t,3) for t in times]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scale",action="store_true")
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    dsn=os.environ["SATAC_READER_DSN"]
    with psycopg.connect(dsn) as conn:
        database,pg,postgis=conn.execute("SELECT current_database(),version(),public.PostGIS_Full_Version()").fetchone()
        if args.scale:
            if database!="satac_benchmark" or os.environ.get("SATAC_BENCHMARK_ONLY")!="1":
                raise RuntimeError("scale benchmark is restricted to the isolated CI database")
            release=SCALE_RELEASE
        else:
            if database!="satac" or os.environ.get("SATAC_BENCHMARK_ONLY")!="1":
                raise RuntimeError("reference benchmark is restricted to the disposable CI database")
            release=str(conn.execute("SELECT release_id FROM public_read.releases WHERE is_current").fetchone()[0])
        members=conn.execute("SELECT count(*) FROM public_read.release_claims WHERE release_id=%s",(UUID(release),)).fetchone()[0]
    if args.scale and members!=10000:
        raise AssertionError("incorrect scale fixture")
    cases=(
       [("a13_filtered_map","/api/v1/map/features",{"bbox":"40,20,43,24","as_of":"550","certainty":"certain","lens":"location","limit":200},"features",36,100,10),
        ("scale_world_first_page","/api/v1/map/features",{"bbox":"-180,-85,180,85","lens":"location","limit":200},"features",200,20,5)]
       if args.scale else
       [("reference_map","/api/v1/map/features",{"bbox":"34,12,60,34","lens":"location","limit":200},"features",None,20,5),
        ("reference_dated_map","/api/v1/map/features",{"bbox":"34,12,60,34","as_of":"550","certainty":"certain","lens":"location","limit":200},"features",None,20,5),
        ("arabic_explore","/api/v1/explore",{"q":"فيد"},"references",None,20,5),
        ("dated_explore","/api/v1/explore",{"q":"فيد","as_of":"550"},"references",None,20,5),
        ("articles","/api/v1/articles",{},"articles",50,20,5),
        ("directory","/api/v1/directory",{},"entries",513,20,5),
        ("geology","/api/v1/geology",{},"records",56,20,5),
        ("cells","/api/v1/cells",{},"cells",2480,20,5),
        ("route","/api/v1/routes/path",{"start":"MAKKA_398E213N_S_JAZI","end":"MADINA_396E244N_S_JAZI"},"meters",392496,20,5)])
    if args.scale:
        assert sum(1 for i in range(10000) if 40<=34+(i%100)*.25<=43 and 20<=12+(i//100)*.22<=24 and 100+(i%10)*100<=550<=199+(i%10)*100)==36
    server=subprocess.Popen([sys.executable,"-m","uvicorn","apps.api.main:app","--host","127.0.0.1","--port","8765","--no-access-log"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    try:
        with httpx.Client(base_url="http://127.0.0.1:8765",timeout=15,trust_env=False) as client:
            for _ in range(100):
                if server.poll() is not None: raise RuntimeError("benchmark server exited")
                try:
                    if client.get("/health").status_code==200: break
                except httpx.RequestError: pass
                time.sleep(.1)
            else: raise RuntimeError("benchmark server not ready")
            results=[measure(client,name,path,{"release":release,**params},key,expected,count,warmup)
                     for name,path,params,key,expected,count,warmup in cases]
        rss=None
        status=Path(f"/proc/{server.pid}/status")
        if status.exists():
            rss=next((int(line.split()[1]) for line in status.read_text().splitlines() if line.startswith("VmHWM:")),None)
    finally:
        server.terminate()
        try: server.wait(timeout=10)
        except subprocess.TimeoutExpired: server.kill();server.wait()
    report={"mode":"isolated_synthetic" if args.scale else "restored_ci_candidate",
            "release_id":release,"claim_versions":members,"environment":{"os":platform.platform(),
            "python":platform.python_version(),"cpu_count":os.cpu_count(),"postgresql":pg,"postgis":postgis,
            "server":"single uvicorn process / loopback HTTP / fresh DB connection per request","api_peak_rss_kib":rss},
            "measurements":results}
    if args.scale:
        report["a13_target_ms"]=1000
        report["a13_measured_pass"]=results[0]["p95_ms"]<1000
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n")
    print("BENCHMARK_REPORT "+json.dumps({**report,"measurements":[{k:v for k,v in x.items() if k!="samples_ms"} for x in results]},ensure_ascii=False))
    # Baseline is observational, not a release gate; later threshold review is explicit.

if __name__=="__main__": main()
