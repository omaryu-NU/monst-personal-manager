import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from technophere_catalog import parse_family,audit_profile_forms

def page(block):
    return '<html><h2>形態ごとのステータスとアビリティ</h2>'+block+'<h2>その他</h2></html>'

def form(no):
    return f'<h3>獣神化：サンプル{no}</h3><div>No.{no} 火</div>'

class Phase8ProfileAuditTests(unittest.TestCase):
    def check(self, html):
        rows=parse_family(html,'https://game.technophere.com/monst/char/123/')
        return audit_profile_forms(html,rows)
    def test_two_forms_are_complete_locally(self):
        a=self.check(page(form(123)+form(124)))
        self.assertEqual((a['headings'],a['parsed'],a['incomplete']),(2,2,False))
    def test_missing_no_triggers_retry(self):
        a=self.check(page(form(123)+'<h3>進化：サンプル</h3><div>番号不明 火</div>'))
        self.assertEqual((a['headings'],a['parsed'],a['incomplete']),(2,1,True))
    def test_no_section_triggers_retry(self):
        a=self.check('<html><h2>その他</h2></html>')
        self.assertTrue(a['incomplete'])
    def test_irrelevant_heading_not_counted(self):
        a=self.check(page(form(123)+'<h3>使い方</h3>'))
        self.assertEqual((a['headings'],a['parsed'],a['incomplete']),(1,1,False))
if __name__=='__main__':unittest.main()
