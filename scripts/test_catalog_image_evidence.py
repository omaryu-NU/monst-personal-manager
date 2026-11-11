import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_image_evidence as mod


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        root = Path(self.t.name)
        self.catalog = root / 'public/catalog'
        self.catalog.mkdir(parents=True)
        self.evidence = root / 'catalog-image-evidence.json'
        self.report = root / 'apply-report.json'
        self.url = mod.PREFIX+'112.webp'
        mod.atomic(self.catalog/'manifest.json', {'count':2,'chunks':[{'path':'characters-0001.json','count':2}]})
        mod.atomic(self.catalog/'characters-0001.json', {'version':1,'characters':[
            {'id':'112','name':'A','attribute':'火','image':self.url},
            {'id':'114','name':'B','attribute':'水'}]})
        mod.atomic(self.report, {'dryRun':False,'results':[{'id':'112','status':'verified','http_status':200}],
                                 'verified':[{'id':'112','url':self.url}]})

    def test_import_and_replay_after_scraper(self):
        result=mod.import_report(self.catalog,self.evidence,self.report,apply=True)
        self.assertEqual(result['newEvidence'],1)
        doc=mod.read(self.catalog/'characters-0001.json')
        del doc['characters'][0]['image']
        mod.atomic(self.catalog/'characters-0001.json',doc)
        self.assertEqual(mod.replay(self.catalog,self.evidence)['toRestore'],1)
        self.assertNotIn('image',mod.read(self.catalog/'characters-0001.json')['characters'][0])
        self.assertEqual(mod.replay(self.catalog,self.evidence,apply=True)['toRestore'],1)
        self.assertEqual(mod.read(self.catalog/'characters-0001.json')['characters'][0]['image'],self.url)
        self.assertEqual(mod.replay(self.catalog,self.evidence,apply=True)['toRestore'],0)

    def test_no_import_from_dry_run(self):
        doc=mod.read(self.report);doc['dryRun']=True;mod.atomic(self.report,doc)
        with self.assertRaises(ValueError): mod.import_report(self.catalog,self.evidence,self.report,apply=True)
        self.assertFalse(self.evidence.exists())

    def test_no_import_when_catalog_does_not_match(self):
        doc=mod.read(self.catalog/'characters-0001.json')
        del doc['characters'][0]['image']
        mod.atomic(self.catalog/'characters-0001.json',doc)
        with self.assertRaises(ValueError): mod.import_report(self.catalog,self.evidence,self.report,apply=True)

    def test_conflict_does_not_write_partial_replay(self):
        mod.atomic(self.evidence, {'schema':1,'images':{'112':self.url,'114':mod.PREFIX+'114.webp'}})
        doc=mod.read(self.catalog/'characters-0001.json')
        doc['characters'][0]['image']='https://example.com/different.webp'
        mod.atomic(self.catalog/'characters-0001.json',doc)
        before=(self.catalog/'characters-0001.json').read_bytes()
        with self.assertRaises(ValueError): mod.replay(self.catalog,self.evidence,apply=True)
        self.assertEqual(before,(self.catalog/'characters-0001.json').read_bytes())

    def test_reject_fake_image_or_unverified_status(self):
        doc=mod.read(self.report)
        doc['verified'][0]['url']='https://evil.example/112.webp'
        mod.atomic(self.report,doc)
        with self.assertRaises(ValueError):mod.import_report(self.catalog,self.evidence,self.report,apply=True)

    def test_missing_catalog_id_is_reported_not_inserted(self):
        mod.atomic(self.evidence, {'schema':1,'images':{'112':self.url,'999':mod.PREFIX+'999.webp'}})
        result=mod.replay(self.catalog,self.evidence,apply=True)
        self.assertEqual(result['missingCatalogIDs'],['999'])
        self.assertEqual(len(mod.read(self.catalog/'characters-0001.json')['characters']),2)


if __name__=='__main__':unittest.main()
