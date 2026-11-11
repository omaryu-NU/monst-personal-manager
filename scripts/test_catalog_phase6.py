import json, tempfile, unittest
from pathlib import Path
from catalog_phase6 import audit, family

class Phase6Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name);self.catalog=self.root/'catalog';self.catalog.mkdir()
  self.u='https://game.technophere.com/monst/char/100/'
  (self.catalog/'characters-0001.json').write_text(json.dumps({'characters':[{'id':'101','name':'テスト','attribute':'火','source':self.u,'abilities':[]}]}),encoding='utf-8')
  (self.catalog/'manifest.json').write_text(json.dumps({'count':1,'chunks':[{'path':'characters-0001.json','count':1}],'coverage':{'totalPages':3,'visitedPages':[1,2]}}),encoding='utf-8')
  self.state=self.root/'state.json'
 def test_missing_page_and_unverified_family(self):
  s=audit(self.catalog,self.state,self.root/'output');self.assertEqual(s['listingPagesMissing'],[3]);self.assertEqual(s['familyStatuses']['verification_unknown_no_state'],1);self.assertFalse(s['allFormsProvenComplete'])
 def test_known_parsed_is_not_complete(self):
  self.state.write_text(json.dumps({'verifiedFamilyURLs':[self.u],'verifiedFamilyFormIDs':{self.u:['101']}}))
  s=audit(self.catalog,self.state,self.root/'output');self.assertTrue(s['allKnownFamiliesParsedAtLeastOnce']);self.assertFalse(s['allFormsProvenComplete'])
 def test_missing_expected_id(self):
  self.state.write_text(json.dumps({'verifiedFamilyURLs':[self.u],'verifiedFamilyFormIDs':{self.u:['101','102']}}))
  s=audit(self.catalog,self.state,self.root/'output');self.assertEqual(s['familyStatuses']['verified_forms_missing_in_catalog'],1)
 def test_invalid_url(self):
  self.assertIsNone(family('https://evil.example/monst/char/1/'))
 def test_duplicate_records_refused(self):
  p=self.catalog/'characters-0001.json';obj=json.loads(p.read_text());obj['characters']*=2;p.write_text(json.dumps(obj));self.assertRaises(ValueError,audit,self.catalog,self.state,self.root/'output')
if __name__=='__main__':unittest.main()
