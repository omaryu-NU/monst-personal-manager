import os, sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import technophere_catalog as t

class TestListing(unittest.TestCase):
    def test_listing_metadata(self):
        html='''<html><body>1 / 50ページ<a href="/monst/char/9548/">マ マクスウェル 真獣神化 闇 貫通・超バランス・亜人・No.9549 ワープ地雷</a></body></html>'''
        found,total=t.parse_listing(html)
        self.assertEqual(total,50)
        self.assertEqual(found['9549']['name'],'マクスウェル')
        self.assertEqual(found['9549']['evolution'],'真獣神化')
        self.assertEqual(found['9549']['type'],'貫通')
        self.assertEqual(found['9549']['style'],'超バランス')
        self.assertEqual(found['9549']['race'],'亜人')
    def test_no_fake_image(self):
        html='<a href="/monst/char/9548/">マ マクスウェル 真獣神化 闇 貫通・超バランス・亜人・No.9549</a>'
        self.assertNotIn('image',t.parse_listing(html)[0]['9549'])
    def test_reconcile_preserves_fields(self):
        old={'id':'9549','name':'マクスウェル','attribute':'闇','image':'https://game.technophere.com/a.png','abilities':['超アンチワープ']}
        new={'id':'9549','name':'マクスウェル','attribute':'闇','source':'https://game.technophere.com/monst/char/9548/'}
        merged=t.reconcile(old,new)
        self.assertEqual(merged['abilities'],['超アンチワープ'])
        self.assertEqual(merged['image'],old['image'])

if __name__=='__main__':unittest.main()
