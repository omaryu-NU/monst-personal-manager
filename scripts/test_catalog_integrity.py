import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from catalog_integrity import check

class IntegrityTests(unittest.TestCase):
    def setup_data(self,base,rows,declared=None):
        p=base/'public/catalog';p.mkdir(parents=True)
        (p/'characters-0001.json').write_text(json.dumps({'characters':rows}),encoding='utf-8')
        (p/'manifest.json').write_text(json.dumps({'count':len(rows) if declared is None else declared,
              'chunks':[{'path':'characters-0001.json','count':len(rows)}],
              'coverage':{'totalPages':3,'visitedPages':[1,2]}}),encoding='utf-8')
        return p
    def test_missing_fields_are_reported_not_corruption(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=self.setup_data(root,[{'id':'1','name':'テスト','attribute':'火'}]);r=check(p,root/'out')
            self.assertTrue(r['structuralOK']);self.assertEqual(r['missingCounts']['missing_image'],1)
            self.assertEqual(r['listingPagesMissing'],[3])
    def test_duplicate_ids_block(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);rows=[{'id':'1','name':'A','attribute':'火'}]*2
            r=check(self.setup_data(root,rows),root/'out');self.assertFalse(r['structuralOK'])
    def test_manifest_count_mismatch_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=self.setup_data(root,[{'id':'1','name':'A','attribute':'水'}],declared=4)
            self.assertFalse(check(p,root/'out')['structuralOK'])
    def test_source_fragment_mismatch_is_warning(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=self.setup_data(root,[{'id':'2','name':'A','attribute':'火','source':'https://game.technophere.com/monst/char/1/#f3'}]);r=check(p,root/'out')
            self.assertTrue(r['structuralOK']);self.assertEqual(r['missingCounts']['source_fragment_mismatch'],1)
if __name__=='__main__':unittest.main()
