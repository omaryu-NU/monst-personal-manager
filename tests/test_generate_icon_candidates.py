import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from generate_icon_candidates import generate,discover

class TestCandidates(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name);self.cat=self.root/'catalog';self.cat.mkdir();self.csv=self.root/'sources.csv'
        (self.cat/'manifest.json').write_text(json.dumps({'schema':1,'chunks':[{'path':'characters-0001.json'}]}))
    def records(self,rs):
        (self.cat/'characters-0001.json').write_text(json.dumps({'characters':rs}))
    def test_collect_only_matching_direct_image(self):
        self.records([{'id':'12','image':'https://game.technophere.com/icons/12.webp'},
                      {'id':'13','image':'https://game.technophere.com/icons/99.webp'},
                      {'id':'14','image':'http://game.technophere.com/icons/14.png'},
                      {'id':'15','image':'https://other.example/15.png'}])
        self.assertEqual(discover(self.cat,'game.technophere.com'),{'12':'https://game.technophere.com/icons/12.webp'})
    def test_incremental_idempotent_and_preserve_manual(self):
        self.records([{'id':'12','image':'https://game.technophere.com/icons/12.webp'}]);
        a=generate(self.cat,self.csv,'game.technophere.com','owner-agreement-1')
        b=generate(self.cat,self.csv,'game.technophere.com','owner-agreement-1')
        self.assertEqual((a['newly_queued'],b['newly_queued']),(1,0))
        with self.csv.open(newline='') as f:self.assertEqual(next(csv.DictReader(f))['id'],'12')
    def test_no_url_guessing(self):
        self.records([{'id':'777','name':'No icon'}])
        self.assertEqual(generate(self.cat,self.csv,'game.technophere.com','agreement')['newly_queued'],0)
    def test_reject_unrecorded_permission(self):
        self.records([])
        with self.assertRaises(ValueError):generate(self.cat,self.csv,'game.technophere.com','')
    def test_path_rejected(self):
        self.records([])
        with self.assertRaises(ValueError):generate(self.cat,self.csv,'https://game.technophere.com','owner-confirmed')

if __name__=='__main__':unittest.main()
