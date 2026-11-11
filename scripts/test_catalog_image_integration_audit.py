import json
import tempfile
import unittest
from pathlib import Path

try:
    from catalog_image_integration_audit import audit
    from catalog_image_evidence import PREFIX
except ImportError:
    from scripts.catalog_image_integration_audit import audit
    from scripts.catalog_image_evidence import PREFIX


class IntegrationAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.cat=self.root/'catalog'
        self.cat.mkdir()
        self.url=PREFIX+'112.webp'
        self.rows=[{'id':'112','name':'sample','attribute':'火','image':self.url}]
        self.write_cat()
        self.evidence=self.root/'evidence.json'
        self.write_ev({'112':self.url})
    def write_cat(self):
        (self.cat/'manifest.json').write_text(json.dumps({'count':len(self.rows),'chunks':[{'path':'characters-0001.json','count':len(self.rows)}]}))
        (self.cat/'characters-0001.json').write_text(json.dumps({'characters':self.rows}))
    def write_ev(self,images):
        self.evidence.write_text(json.dumps({'schema':1,'images':images}))
    def report(self):
        p=self.root/'apply.json'
        p.write_text(json.dumps({'dryRun':False,'results':[{'id':'112','status':'verified','http_status':200}], 'verified':[{'id':'112','url':self.url}]}))
        return p
    def test_pass(self):
        self.assertTrue(audit(self.cat,self.evidence,[self.report()],min_evidence=1)['passed'])
    def test_missing_image(self):
        self.rows[0].pop('image');self.write_cat()
        self.assertEqual(audit(self.cat,self.evidence)['missingImageIDs'],['112'])
    def test_conflict(self):
        self.rows[0]['image']='https://other.example/112.webp';self.write_cat()
        self.assertEqual(audit(self.cat,self.evidence)['conflictingIDs'],['112'])
    def test_missing_catalog(self):
        self.rows=[];self.write_cat()
        self.assertFalse(audit(self.cat,self.evidence)['passed'])
    def test_missing_report_evidence(self):
        self.write_ev({})
        result=audit(self.cat,self.evidence,[self.report()])
        self.assertFalse(result['passed'])
        self.assertEqual(result['verifiedReportEntriesMissingFromEvidence'][0]['id'],'112')
    def test_minimum_evidence(self):
        self.assertFalse(audit(self.cat,self.evidence,min_evidence=2)['passed'])
    def test_invalid_url(self):
        self.write_ev({'112':'https://example.com/112.webp'})
        self.assertEqual(audit(self.cat,self.evidence)['invalidEvidenceIDs'],['112'])
    def test_reject_dry_run(self):
        p=self.report(); r=json.loads(p.read_text());r['dryRun']=True;p.write_text(json.dumps(r))
        with self.assertRaises(ValueError):audit(self.cat,self.evidence,[p])

if __name__=='__main__': unittest.main()
