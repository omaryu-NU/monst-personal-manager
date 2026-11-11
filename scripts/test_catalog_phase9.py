import unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from technophere_catalog import parse_family, reconcile, _form_icon
from bs4 import BeautifulSoup

BASE='https://game.technophere.com/monst/char/9540/'

def html(forms):
    return '<html><h2>形態ごとのステータスとアビリティ</h2>'+forms+'<h2>その他</h2></html>'

def form(no, inner='', evolution='神化'):
    return f'<h3>{evolution}：サンプル{no}</h3><section><p>No.{no} 水 魔人 貫通 砲撃 ★6</p>{inner}</section>'

class Phase9Tests(unittest.TestCase):
    def test_image_exact_id_in_srcset_and_data_src(self):
        block='''<img alt="他の画像" src="/monst/wp-content/uploads/monst-lab/icon/19542.webp">
          <img alt="サンプルのアイコン" src="data:image/gif;base64,R0" data-srcset="/monst/wp-content/uploads/monst-lab/icon/9542.webp 1x, /monst/wp-content/uploads/monst-lab/icon/9542.png 2x">'''
        rows=parse_family(html(form(9542,block)),BASE)
        self.assertEqual(rows[0]['image'],'https://game.technophere.com/monst/wp-content/uploads/monst-lab/icon/9542.webp')
    def test_unrelated_images_not_used(self):
        rows=parse_family(html(form(9542,'<img src="/monst/assets/logo.png">')),BASE)
        self.assertNotIn('image',rows[0])
    def test_different_forms_have_distinct_images(self):
        markup=form(9542,'<img src="/monst/wp-content/uploads/monst-lab/icon/9542.webp">')+form(9541,'<img data-lazy-src="/monst/wp-content/uploads/monst-lab/icon/9541.webp">','進化')
        rows=parse_family(html(markup),BASE)
        self.assertEqual([x['id'] for x in rows],['9542','9541'])
        self.assertTrue(rows[0]['image'].endswith('9542.webp'))
        self.assertTrue(rows[1]['image'].endswith('9541.webp'))
    def test_different_form_stats_not_cross_contaminated(self):
        part='<table><tr><th>Lv極</th><td>21,505</td><td>17,171</td><td>269.3</td></tr><tr><th>タス最大値</th><td>4,200</td><td>5,875</td><td>95.2</td></tr><tr><th>アビリティ</th><td><a>アンチ重力バリア</a><a>アンチダメージウォール</a></td></tr><tr><th>ゲージショット</th><td><a>アンチブロック</a> バリア付与</td></tr><tr><th>ストライクショット</th><td>16ターン</td></tr><tr><th>友情コンボ</th><td>超強全敵反射衝撃波</td></tr></table>'
        a=parse_family(html(form(9542,part)+form(9541,'<table><tr><th>Lv極</th><td>19,125</td><td>17,534</td><td>251.1</td></tr></table>','進化')),BASE)
        self.assertEqual((a[0]['hp'],a[0]['attack'],a[0]['speed']),(21505,17171,269.3))
        self.assertEqual(a[1]['hp'],19125)
        self.assertEqual(a[0]['abilities'],['アンチ重力バリア','アンチダメージウォール'])
        self.assertIn('バリア付与',a[0]['gaugeAbilities'])
        self.assertEqual(a[0]['ss'],'16ターン')
    def test_no_fabricated_icon_for_image_without_url(self):
        rows=parse_family(html(form(9542,'<img alt="サンプルのアイコン" src="data:image/png;base64,AAAA">')),BASE)
        self.assertNotIn('image',rows[0])
    def test_preserves_existing_fields_when_new_partial(self):
        old={'id':'9542','name':'元名','attribute':'水','image':'https://game.technophere.com/monst/wp-content/uploads/monst-lab/icon/9542.webp','abilities':['アンチ重力バリア'],'hp':21505}
        new={'id':'9542','name':'新名','attribute':'水','abilities':[]}
        merged=reconcile(old,new,verified=True)
        self.assertEqual(merged['image'],old['image'])
        self.assertEqual(merged['abilities'],old['abilities'])
        self.assertEqual(merged['hp'],old['hp'])

if __name__=='__main__':unittest.main()
