import json
import tempfile
import unittest
from pathlib import Path
from pipelines.verify_distribution import ART, inventory

class DistributionInventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/"dist"
        self.public=Path(self.tmp.name)/"public"
        def put(root,name,content):
            p=root/name
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text(content,encoding="utf-8")
        self.put=put
        for name in {"land.geojson"}|{f"legacy-art/{n}" for n in ART}:
            put(self.root,name,"test:"+name)
            put(self.public,name,"test:"+name)
        put(self.root,"physical/labels.json","fixture")
        put(self.root,"physical/manifest.json",json.dumps({"files":{"labels.json":"fixture"}}))
        for name in ("index.html","assets/index-test.js","assets/index-test.css","assets/maplibre-gl-worker.mjs"):
            put(self.root,name,"fixture")
    def test_inventory_classifies_and_rejects_unclassified_files(self):
        result=inventory(self.root,self.public)
        self.assertEqual(len(result["application"]),4)
        self.assertIn("land.geojson",result["protected_static"])
        self.put(self.root,"extra.json","unexpected")
        with self.assertRaises(ValueError):
            inventory(self.root,self.public)
    def test_tracked_bytes_must_match(self):
        self.put(self.root,"land.geojson","changed")
        with self.assertRaises(ValueError):
            inventory(self.root,self.public)
    def test_identical_static_paths_are_reported(self):
        for root in (self.root,self.public):
            self.put(root,"legacy-art/rock.svg","test:land.geojson")
        self.assertIn(["land.geojson","legacy-art/rock.svg"],inventory(self.root,self.public)["identical_static_paths"])
