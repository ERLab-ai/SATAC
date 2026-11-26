# SATAC — v0.13.1 Stabilization (candidate)

Arabic documentation: [README_AR.md](README_AR.md). Legacy atlas, not the P1 platform.

## Build from the baseline repository

Linux / Python 3.13.5:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m playwright install --with-deps chromium
python scripts/rebuild.py --verify
python -m pytest -q --tb=short --junitxml=results.xml
```

The rebuild regenerates geography, world tiles, cell metrics, geology and the standalone HTML. `--verify` compares outputs with the existing release manifest. Run on a clean checkout; intentional data changes require reviewed manifest updates. Existing legacy source data are inputs. No external historical source acquisition is performed. The pinned package list reflects the observed Linux environment; clean installation and GitHub Actions must be verified separately.
