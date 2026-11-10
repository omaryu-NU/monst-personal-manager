import importlib.util, json, os, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
mod_path=Path(__file__).with_name('technophere_catalog.py')
spec=importlib.util.spec_from_file_location('tc',mod_path); tc=importlib.util.module_from_spec(spec);spec.loader.exec_module(tc)
LIST='''<p>1 / 50ページ</p><a href="/monst/char/9548/">マ マクスウェル 真獣神化 闇 貫通・超バランス・亜人・No.9549 ワープ地雷</a>'''
PROFILE='''<h1>〖モンスト〗マクスウェル（真獣神化）の性能</h1><p>闇 真獣神化 No.9549</p><div>入手方法</div><div>ガチャ（限定）</div><img alt="マクスウェルのアイコン" src="/monst/wp-content/uploads/monst-lab/icon/9549.webp">'''
class FakeResponse:
    def __init__(self,text):self.text=text;self.content=text.encode()
    def raise_for_status(self):pass
class FakeSession:
    def get(self,url,timeout=25):
        if '/char/' in url:return FakeResponse(PROFILE)
        if url.endswith('/characters/'):return FakeResponse(LIST)
        raise tc.requests.RequestException('offline')
class CatalogTests(unittest.TestCase):
    def test_listing(self):
        items,pages=tc.parse_listing(LIST)
        self.assertEqual(pages,50);self.assertEqual(items['9549']['name'],'マクスウェル')
    def test_profile(self):
        row=tc.parse_profile(PROFILE,'https://game.technophere.com/monst/char/9548/')
        self.assertEqual(row['image'],'https://game.technophere.com/monst/wp-content/uploads/monst-lab/icon/9549.webp')
    def test_reconcile_preserves_old(self):
        old={'id':'1','name':'以前','attribute':'火','image':'https://game.technophere.com/monst/icon/1.webp'}
        self.assertEqual(tc.reconcile(old,{'id':'1','name':'今','attribute':'水'})['image'],old['image'])
    def test_restricted_hosts(self):
        self.assertFalse(tc.safe_url('https://evil.example/monst/abc'))
        self.assertFalse(tc.safe_url('http://game.technophere.com/monst/abc'))
    def test_requires_permission(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(RuntimeError,'許可'):
                tc.update(SimpleNamespace(pages=2,profiles=0,delay=0),FakeSession(),check_robots=False,wait=lambda _:None)
    def test_update_keeps_previous_and_chunks(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);oldout=tc.OUT;oldstate=tc.STATE
            try:
                tc.OUT=root/'catalog';tc.STATE=root/'cursor.json'
                tc.atomic(tc.OUT/'manifest.json',{'chunks':[{'path':'characters-0001.json','count':1}]})
                tc.atomic(tc.OUT/'characters-0001.json',{'characters':[{'id':'100','name':'以前','attribute':'火','abilities':[]}]})
                with patch.dict(os.environ,{'TECHNOPHERE_REUSE_APPROVED':'true'}):
                    manifest=tc.update(SimpleNamespace(pages=2,profiles=1,delay=0),FakeSession(),check_robots=False,wait=lambda _:None)
                self.assertEqual(manifest['count'],2)
                rows=json.loads((tc.OUT/'characters-0001.json').read_text())['characters']
                self.assertEqual({x['id'] for x in rows},{'100','9549'})
                self.assertTrue(any(x.get('image') for x in rows))
            finally:tc.OUT=oldout;tc.STATE=oldstate
if __name__=='__main__':unittest.main()
