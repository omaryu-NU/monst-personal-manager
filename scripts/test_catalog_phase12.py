import importlib.util, tempfile, unittest, os
from pathlib import Path
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('p12',Path(__file__).with_name('catalog_image_backfill.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Robots:
    def can_fetch(self,*args):return True
class Response:
    def __init__(self, status=200,ct='image/webp'):
        self.status_code=status;self.headers={'Content-Type':ct}
    def __enter__(self):return self
    def __exit__(self,*a):pass
    def iter_content(self,chunk_size=4096):yield b'RIFF0000WEBPpayload'
class Session:
    def __init__(self,statuses):self.statuses=iter(statuses);self.seen=[];self.headers={}
    def get(self,url,**kwargs):
        self.seen.append(url);return Response(next(self.statuses))
class Phase12(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        root=Path(self.tmp.name);self.cat=root/'public/catalog';self.cat.mkdir(parents=True)
        self.state=root/'local-reports/image-backfill/state.json'
        self.file=self.cat/'characters-0001.json'
        records=[{'id':str(i),'source':f'https://game.technophere.com/monst/char/{i}/'} for i in [112,114,116,118,120,122,124]]
        m.atomic_json(self.file,{'version':1,'characters':records})
        m.atomic_json(self.cat/'manifest.json',{'count':len(records),'chunks':[{'path':self.file.name,'count':len(records)}]})
    def run_audit(self,statuses,**kwargs):
        with patch.dict(os.environ,{'TECHNOPHERE_REUSE_APPROVED':'true'}):
            return m.audit(self.cat,online_limit=len(statuses),delay=1,apply=kwargs.pop('apply',True),state_file=self.state,session=Session(statuses),robots=Robots(),wait=lambda _:None,**kwargs)
    def test_successive_batches_do_not_skip_missing_rows(self):
        a=self.run_audit([200]*5)
        self.assertEqual([x['id'] for x in a['verified']],['112','114','116','118','120'])
        b=self.run_audit([200]*2)
        self.assertEqual([x['id'] for x in b['verified']],['122','124'])
        self.assertEqual(m.load(self.state)['lastProcessedID'],124)
        self.assertEqual(sum(bool(x.get('image')) for x in m.load(self.file)['characters']),7)
    def test_old_cursor_state_migrates_without_skipping(self):
        self.state.parent.mkdir(parents=True,exist_ok=True)
        m.atomic_json(self.state,{'cursor':5})
        doc=m.load(self.file)
        for r in doc['characters'][:5]:r['image']='https://example.test/old.webp'
        m.atomic_json(self.file,doc)
        result=self.run_audit([200,200])
        self.assertEqual([x['id'] for x in result['verified']],['122','124'])
        self.assertEqual(m.load(self.state)['schema'],2)
    def test_dry_run_never_updates_catalog_or_state(self):
        a=self.run_audit([200],apply=False)
        self.assertEqual(a['verifiedCount'],1)
        self.assertFalse(self.state.exists())
        self.assertFalse(m.load(self.file)['characters'][0].get('image'))
    def test_retry_backoff_skips_failed_id_on_next_run(self):
        a=self.run_audit([404])
        self.assertEqual(a['results'][0]['id'],'112')
        s=m.load(self.state)
        self.assertEqual(s['retry']['112']['retryAfterRun'],3)
        b=self.run_audit([200])
        self.assertEqual(b['results'][0]['id'],'114')
        self.assertNotIn('112',[x['id'] for x in b['verified']])
    def test_rate_limit_stops_without_marking_failed_id(self):
        a=self.run_audit([429])
        self.assertTrue(a['rateLimited'])
        self.assertEqual(m.load(self.state)['lastProcessedID'],0)
        self.assertEqual(m.load(self.state)['retry'],{})
        b=self.run_audit([200])
        self.assertEqual(b['results'][0]['id'],'112')
if __name__=='__main__':unittest.main()
