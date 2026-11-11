import json
import tempfile
import unittest
from pathlib import Path
from catalog_phase22 import analyze, is_missing, valid_family, load_catalog

class Phase22Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.catalog = self.root / 'catalog'
        self.catalog.mkdir()
        self.rows = [
            {'id':'101','source':'https://game.technophere.com/monst/char/100/','name':'A','attribute':'火','abilities':['X'],'hp':123,'attack':456,'speed':7.5},
            {'id':'102','source':'https://game.technophere.com/monst/char/100/','name':'B','attribute':'水'},
            {'id':'201','source':'https://game.technophere.com/monst/char/200/','name':'C','attribute':'木'},
        ]
        self.set_catalog(self.rows)
        self.state = self.root / 'state.json'
        self.state.write_text(json.dumps({'verifiedFamilyURLs':['https://game.technophere.com/monst/char/100/'], 'verifiedFamilyFormIDs':{'https://game.technophere.com/monst/char/100/':['101','102','103']}}),encoding='utf-8')
    def set_catalog(self, rows):
        (self.catalog/'manifest.json').write_text(json.dumps({'count':len(rows),'chunks':[{'path':'characters-0001.json'}]}),encoding='utf-8')
        (self.catalog/'characters-0001.json').write_text(json.dumps({'characters':rows}),encoding='utf-8')
    def report(self, baseline=None):
        return analyze(self.catalog,self.state,self.root/'out',baseline)
    def test_counts(self):
        r=self.report();self.assertEqual(r['records'],3);self.assertEqual(r['verifiedFamilies'],1);self.assertEqual(r['unverifiedFamilies'],1)
    def test_missing_by_status(self):
        r=self.report();self.assertEqual(r['missingCoreByStatus']['previously_parsed_family'],2);self.assertEqual(r['missingCoreByStatus']['unverified_family'],1)
    def test_form_state_missing(self):
        self.assertEqual(self.report()['verifiedFormIDsMissingCount'],1)
    def test_csv_generated(self):
        self.report();self.assertEqual(len((self.root/'out/form-quality.csv').read_text(encoding='utf-8-sig').splitlines()),4)
    def test_zero_is_present(self):
        self.assertFalse(is_missing(0))
    def test_none_empty_missing(self):
        self.assertTrue(is_missing([]));self.assertTrue(is_missing(''))
    def test_invalid_source(self):
        self.assertFalse(valid_family('https://evil.test/monst/char/1/'))
    def test_duplicated_ids(self):
        self.set_catalog(self.rows+[self.rows[0]]);self.assertEqual(len(load_catalog(self.catalog)[2]),1)
    def test_reject_unsafe_chunk(self):
        (self.catalog/'manifest.json').write_text(json.dumps({'chunks':[{'path':'../private.json'}]}));
        with self.assertRaises(ValueError):load_catalog(self.catalog)
    def test_baseline(self):
        baseline=self.root/'baseline.json';baseline.write_text(json.dumps({'records':2,'missingFieldCounts':{'image':2}}))
        r=self.report(baseline);self.assertEqual(r['baselineComparison']['recordDelta'],1)
    def test_read_only_input(self):
        before=(self.catalog/'characters-0001.json').read_bytes();self.report();self.assertEqual(before,(self.catalog/'characters-0001.json').read_bytes())

if __name__=='__main__': unittest.main()
