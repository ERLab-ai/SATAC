"""Verify exact reference assets against the successful CI artifact manifest."""
import argparse
import hashlib
import json
from pathlib import Path

EXPECTED = "ef7cdd125d2b9f5600f90d7406f1e0ea3c95a6f1ce4a0b9a134afebeec64797b"
ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify(root):
    root = root.resolve()
    manifest = root / "manifest.json"
    if digest(manifest) != EXPECTED:
        raise ValueError("reference asset manifest differs from run 46023832001")
    data = json.loads(manifest.read_bytes())
    files = data["files"]
    if len(files) != 52:
        raise ValueError("unexpected asset inventory")
    actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}
    if actual != set(files) | {"manifest.json"}:
        raise ValueError("asset inventory mismatch")
    for name, expected in files.items():
        p = root / name
        if not p.resolve().is_relative_to(root) or p.is_symlink() or digest(p) != expected:
            raise ValueError("asset mismatch: " + name)
    print("PASS: 52 reference assets and original manifest SHA-256 verified")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT / "apps/web/public/physical")
    verify(p.parse_args().root)
