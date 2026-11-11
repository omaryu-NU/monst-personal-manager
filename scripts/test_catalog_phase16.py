import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from catalog_image_auto import execute


class Phase16Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.cat=self.root/'catalog'; self.cat.mkdir()
        self.ev=self.root/'evidence.json'; self.ev.write_text('{"schema":1,"images":{}}')
        self.state=self.root/'state.json'; self.out=self.root/'report.json'
        self.env=patch.dict(os.environ,{'TECHNOPHERE_REUSE_APPROVED':'true'})
        self.env.start(); self.addCleanup(self.env.stop)

    def run_mock(self, *, rate=False, conflict=False, missing=False, verified=2):
        def replay(cat,ev,apply=False):
            return {'conflicts':['112'] if conflict else [],'missingCatalogIDs':['5'] if missing else [],'toRestore':0}
        def audit(cat,**kwargs):
            self.assertEqual(kwargs['state_file'],self.state)
            self.assertTrue(kwargs['apply'])
            return {'dryRun':False,'attempted':verified,'verifiedCount':verified,
                    'updatedRecords':verified,'rateLimited':rate,'verified':[], 'results':[]}
        def importer(*args,**kwargs):
            self.assertTrue(self.out.is_file())
            return {'totalEvidence':5+verified,'newEvidence':verified}
        return execute(self.cat,self.ev,self.state,self.out,
                       audit_fn=audit,import_fn=importer,replay_fn=replay)

    def test_success_report(self):
        r=self.run_mock()
        self.assertEqual(r['newEvidence'],2)
        self.assertEqual(r['evidenceCount'],7)
        self.assertFalse(r['imageIdentityVerified'])

    def test_429_halts(self):
        with self.assertRaisesRegex(RuntimeError,'429'):self.run_mock(rate=True)

    def test_conflict_halts_before_probe(self):
        with self.assertRaisesRegex(ValueError,'conflicts'):self.run_mock(conflict=True)

    def test_missing_id_halts(self):
        with self.assertRaisesRegex(ValueError,'missing IDs'):self.run_mock(missing=True)

    def test_invalid_limits(self):
        with self.assertRaises(ValueError):execute(self.cat,self.ev,self.state,self.out,limit=4)
        with self.assertRaises(ValueError):execute(self.cat,self.ev,self.state,self.out,delay=1)

    def test_no_authorization(self):
        with patch.dict(os.environ,{'TECHNOPHERE_REUSE_APPROVED':'false'}):
            with self.assertRaises(RuntimeError):execute(self.cat,self.ev,self.state,self.out)

    def test_required_evidence(self):
        self.ev.unlink()
        with self.assertRaises(FileNotFoundError):execute(self.cat,self.ev,self.state,self.out)

    def test_real_replay_and_import_e2e(self):
        from catalog_image_evidence import replay, import_report
        from catalog_image_backfill import PREFIX
        records=[{'id':'112','name':'A','attribute':'火','source':'https://game.technophere.com/monst/char/112/'},
                 {'id':'114','name':'B','attribute':'水','source':'https://game.technophere.com/monst/char/114/'}]
        (self.cat/'manifest.json').write_text(json.dumps({'count':2,'chunks':[{'path':'characters-0001.json','count':2}]}))
        (self.cat/'characters-0001.json').write_text(json.dumps({'characters':records}))
        self.ev.write_text(json.dumps({'schema':1,'images':{'112':PREFIX+'112.webp'}}))
        def fake_audit(cat,**kw):
            # after replay, 112 must already exist; only 114 newly verified
            doc=json.loads((self.cat/'characters-0001.json').read_text())
            self.assertEqual(doc['characters'][0]['image'],PREFIX+'112.webp')
            doc['characters'][1]['image']=PREFIX+'114.webp'
            (self.cat/'characters-0001.json').write_text(json.dumps(doc))
            self.state.write_text('{"schema":2,"lastProcessedID":114}')
            return {'dryRun':False,'attempted':1,'verifiedCount':1,'updatedRecords':1,
                    'rateLimited':False,'verified':[{'id':'114','url':PREFIX+'114.webp'}],
                    'results':[{'id':'114','status':'verified','http_status':200}]}
        result=execute(self.cat,self.ev,self.state,self.out,audit_fn=fake_audit)
        self.assertEqual(result['evidenceCount'],2)
        self.assertEqual(result['newEvidence'],1)
        self.assertEqual(json.loads(self.ev.read_text())['images']['114'],PREFIX+'114.webp')
        self.assertEqual(json.loads(self.state.read_text())['lastProcessedID'],114)

if __name__=='__main__':unittest.main()
