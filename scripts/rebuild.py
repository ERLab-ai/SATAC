"""Regenerate derived geographic assets and check byte identity against v0.13 manifest."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'data/manifest.json'
STEPS = ('prepare_geography.py', 'prepare_world.py', 'prepare_cells.py', 'prepare_geology.py', 'build.py')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', help='Require exact match with existing release manifest')
    args = parser.parse_args()
    original = MANIFEST.read_bytes() if args.verify else None
    expected = json.loads(original) if original is not None else None
    try:
        for step in STEPS:
            print(f'==> {step}', flush=True)
            subprocess.run([sys.executable, str(ROOT / step)], cwd=ROOT, check=True)
        actual = json.loads(MANIFEST.read_text())
        for rel, digest in actual.items():
            if hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() != digest:
                raise SystemExit(f'Manifest mismatch: {rel}')
        if expected is not None and actual != expected:
            changed = sorted(k for k in expected.keys() | actual.keys() if expected.get(k) != actual.get(k))
            raise SystemExit('Release output differs: ' + ', '.join(changed))
    finally:
        # A failed verification must not silently redefine the reference manifest.
        if original is not None:
            MANIFEST.write_bytes(original)
    print(f'Build verified: {len(actual)} SHA-256 entries')


if __name__ == '__main__':
    main()
