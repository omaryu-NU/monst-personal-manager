"""Phase21: offline fixtures for safe, per-form extraction."""
import unittest
from bs4 import BeautifulSoup
from technophere_catalog import _parse_stats_table,parse_family,audit_profile_forms

URL='https://game.technophere.com/monst/char/9000/'
def get_item(html):
    item={}
    _parse_stats_table(BeautifulSoup(html,'html.parser'),item)
    return item

class Phase21Tests(unittest.TestCase):
    def test_reordered_labeled_columns(self):
        row='<table><tr><th>レベル</th><th>スピード</th><th>HP</th><th>攻撃力</th></tr><tr><th>Lv極</th><td>333.3</td><td>11,111</td><td>22,222</td></tr></table>'
        self.assertEqual(get_item(row),{'hp':11111,'attack':22222,'speed':333.3})
    def test_level_precedence_not_document_order(self):
        a='<table><tr><th>Lv極</th><td>100</td><td>200</td><td>300</td></tr><tr><th>Lv120</th><td>900</td><td>800</td><td>700</td></tr></table>'
        b='<table><tr><th>Lv120</th><td>900</td><td>800</td><td>700</td></tr><tr><th>Lv極</th><td>100</td><td>200</td><td>300</td></tr></table>'
        for x in (a,b):
            self.assertEqual(get_item(x),{'hp':100,'attack':200,'speed':300})
    def test_only_lv120_fallback(self):
        self.assertEqual(get_item('<table><tr><th>Lv120</th><td>123</td><td>456</td><td>7.8</td></tr></table>'),{'hp':123,'attack':456,'speed':7.8})
    def test_ambiguous_header_does_not_assign_wrong_columns(self):
        html='<table><tr><th>レベル</th><th>スピード</th><th>不明</th><th>攻撃力</th></tr><tr><th>Lv極</th><td>1</td><td>2</td><td>3</td></tr></table>'
        self.assertEqual(get_item(html),{})
    def test_non_numeric_stat_ignored(self):
        html='<table><tr><th>Lv極</th><td>HP不明</td><td>999</td><td>100.5</td></tr></table>'
        self.assertEqual(get_item(html),{'attack':999,'speed':100.5})
    def test_tas_max_is_never_added(self):
        html='<table><tr><th>Lv極</th><td>10</td><td>20</td><td>30</td></tr><tr><th>タス最大値</th><td>100</td><td>100</td><td>100</td></tr></table>'
        self.assertEqual(get_item(html),{'hp':10,'attack':20,'speed':30})
    def test_multiple_ability_columns(self):
        html='<table><tr><th>アビリティ</th><td><a>超AGB</a></td><td><a>AW</a></td></tr><tr><th>ゲージ</th><td><a>AB</a></td><td><a>SS短縮</a></td></tr></table>'
        self.assertEqual(get_item(html),{'abilities':['超AGB','AW'],'gaugeAbilities':['AB','SS短縮']})
    def test_duplicate_ability_dedupes(self):
        html='<table><tr><th>アビリティ</th><td><a>AW</a></td><td><a>AW</a></td></tr></table>'
        self.assertEqual(get_item(html),{'abilities':['AW']})
    def test_forms_separately_scoped(self):
        html='''<h2>形態ごとのステータスとアビリティ</h2>
        <h3>進化前：キャラA</h3><p>No.9000 火</p><table><tr><th>Lv極</th><td>100</td><td>200</td><td>300</td></tr></table>
        <h3>進化：キャラA</h3><p>No.9001 水</p><table><tr><th>Lv極</th><td>400</td><td>500</td><td>600</td></tr></table>
        <h2>その他</h2>'''
        forms=parse_family(html,URL)
        self.assertEqual([(f['id'],f['hp']) for f in forms],[('9000',100),('9001',400)])
        self.assertFalse(audit_profile_forms(html,forms)['incomplete'])
    def test_incomplete_headings_remain_unverified(self):
        html='<h2>形態ごとのステータスとアビリティ</h2><h3>進化前：A</h3><p>No.9000 火</p><h3>進化：A</h3><p>No.が不明</p>'
        forms=parse_family(html,URL)
        self.assertEqual(len(forms),1)
        self.assertTrue(audit_profile_forms(html,forms)['incomplete'])
    def test_empty_fields_not_invented(self):
        self.assertEqual(get_item('<table><tr><th>SS</th><td></td></tr></table>'),{})

if __name__=='__main__':unittest.main()
