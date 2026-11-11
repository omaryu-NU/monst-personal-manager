import os,sys,tempfile,unittest,json
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parent))
import technophere_catalog as t
P='https://game.technophere.com/monst/char/9548/'
HTML='''<html><h1>〖モンスト〗マクスウェル（真獣神化）の性能</h1>
<h2>マクスウェルの形態ごとのステータスとアビリティ</h2>
<h3>真獣神化：秩序の悪魔 マクスウェル</h3>
<div><img alt="秩序の悪魔 マクスウェル" src="/monst/icons/9549.webp"/>
<p>No.9549 闇 亜人 貫通 超バランス ★6</p>
<table><tr><th></th><th>HP</th><th>攻撃力</th><th>スピード</th></tr>
<tr><th>Lv極</th><td>18,748</td><td>17,160</td><td>266.03</td></tr>
<tr><th>タス最大値</th><td>3,900</td><td>5,875</td><td>94.35</td></tr></table>
<table><tr><th>アビリティ</th><td><a href="/monst/">超アンチワープ</a><a href="/monst/">アンチ転送壁</a></td></tr>
<tr><th>ゲージショット</th><td>超アンチブロック</td></tr>
<tr><th>ストライクショット</th><td>スピードアップ 16ターン</td></tr>
<tr><th>友情コンボ</th><td>リフレクションリング（闇）</td></tr></table></div>
<h3>真獣神化前：マクスウェル</h3>
<div><p>No.9548 闇 亜人 貫通 バランス ★5</p>
<table><tr><th>Lv極</th><td>15,000</td><td>12,000</td><td>200.00</td></tr></table></div>
<h2>関係する記事</h2><h3>このキャラは対象外</h3><p>No.9999</p></html>'''
LIST='''<p>1 / 50ページ</p><a href="/monst/char/9548/">マ マクスウェル 真獣神化 闇 貫通・超バランス・亜人・No.9549 ワープ地雷</a>'''
class FakeResponse:
    def __init__(self,t):self.text=t;self.content=t.encode()
    def raise_for_status(self):pass
class FakeSession:
    def get(self,url,timeout=25):return FakeResponse(HTML if '/char/' in url else LIST)
class FamilyTests(unittest.TestCase):
    def test_two_forms_and_details(self):
        forms=t.parse_family(HTML,P)
        self.assertEqual({x['id'] for x in forms},{'9548','9549'})
        rec={x['id']:x for x in forms}['9549']
        self.assertEqual(rec['hp'],18748)
        self.assertEqual(rec['attack'],17160)
        self.assertEqual(rec['speed'],266.03)
        self.assertEqual(rec['abilities'],['超アンチワープ','アンチ転送壁'])
        self.assertIn('/9549.webp',rec['image'])
        self.assertEqual(rec['gaugeAbilities'],['超アンチブロック'])
        self.assertEqual(rec['friendship'],'リフレクションリング（闇）')
    def test_out_of_scope_ignored(self):
        self.assertNotIn('9999',{x['id'] for x in t.parse_family(HTML,P)})
    def test_missing_section_returns_empty(self):
        self.assertEqual(t.parse_family('<h1>nothing</h1>',P),[])
    def test_accumulate_and_preserve(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);a,b,c,d=t.OUT,t.STATE,t.ROOT,t.INDEX
            try:
                t.OUT=root/'public/catalog';t.STATE=root/'state.json'
                # Existing shorter name and icon must be retained for original record.
                t.atomic(t.OUT/'manifest.json',{'chunks':[{'path':'characters-0001.json','count':1}]})
                t.atomic(t.OUT/'characters-0001.json',{'characters':[{'id':'9549','name':'マクスウェル','attribute':'闇','image':'https://game.technophere.com/monst/old.webp','source':P}]})
                with patch.dict(os.environ,{'TECHNOPHERE_REUSE_APPROVED':'true'}):
                    out=t.update(SimpleNamespace(pages=2,profiles=1,delay=0.5),FakeSession(),check_robots=False,wait=lambda _:None)
                self.assertEqual(out['count'],2)
                recs=json.loads((t.OUT/'characters-0001.json').read_text())['characters']
                self.assertEqual({x['id'] for x in recs},{'9548','9549'})
                self.assertEqual(next(x['name'] for x in recs if x['id']=='9549'),'マクスウェル')
                self.assertEqual(out['coverage']['familiesVerified'],1)
            finally:t.OUT=a;t.STATE=b
if __name__=='__main__':unittest.main()
