"""Compare same-run HTTP benchmarks; reject public payload changes."""
import argparse
import json
from pathlib import Path

def compare(before,after):
    for field in ("mode","release_id","claim_versions"):
        if before[field]!=after[field]:
            raise ValueError("benchmark identity mismatch: "+field)
    old={m["case"]:m for m in before["measurements"]}
    new={m["case"]:m for m in after["measurements"]}
    if old.keys()!=new.keys():
        raise ValueError("workload mismatch")
    rows=[]
    for case,b in old.items():
        a=new[case]
        for field in ("path","parameters","requests","warmup","result_count","response_sha256","has_next_page"):
            if b[field]!=a[field]:
                raise ValueError(f"{case}: response or workload changed: {field}")
        rows.append({"case":case,"before_p95_ms":b["p95_ms"],"after_p95_ms":a["p95_ms"],
                     "p95_reduction_pct":round((1-a["p95_ms"]/b["p95_ms"])*100,2),
                     "response_sha256":a["response_sha256"]})
    return {"mode":before["mode"],"before_commit":before["server_commit"],"after_commit":after["server_commit"],
            "identical_public_responses":True,"comparison":rows,
            "after_a13_measured_pass":after.get("a13_measured_pass")}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("before",type=Path)
    p.add_argument("after",type=Path)
    p.add_argument("output",type=Path)
    args=p.parse_args()
    result=compare(json.loads(args.before.read_text()),json.loads(args.after.read_text()))
    args.output.write_text(json.dumps(result,indent=2)+"\n")
    print("PERFORMANCE_COMPARISON "+json.dumps(result))
if __name__=="__main__": main()
