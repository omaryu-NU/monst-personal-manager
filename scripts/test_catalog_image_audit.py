import json, tempfile, unittest
from pathlib import Path
from catalog_image_audit import audit,image_issue

class ImageAuditTests(unittest.TestCase):
    def test_missing(self):self.assertEqual(image_issue({'id':'7'}),'missing_url')
    def test_untrusted(self):self.assertEqual(image_issue({'id':'7','image':'https://elsewhere.test/monst/7.png'}),'untrusted_url')
    def test_mismatch(self):self.assertEqual(image_issue({'id':'7','image':'https://game.technophere.com/monst/8.png'}),'id_filename_mismatch')
    def test_valid(self):self.assertEqual(image_issue({'id':'7','image':'https://game.technophere.com/monst/icons/7.webp'}),'format_ok')
    def test_offline_no_requests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); cat=root/'catalog';cat.mkdir()
            (cat/'manifest.json').write_text(json.dumps({'count':1,'chunks':[{'path':'characters-0001.json','count':1}]}))
            (cat/'characters-0001.json').write_text(json.dumps({'characters':[{'id':'7','name':'例','image':'https://game.technophere.com/monst/icons/7.webp'}]}))
            report=audit(cat,root/'report')
            self.assertEqual(report['networkRequests'],0)
            self.assertEqual(report['statusCounts']['format_ok'],1)
            self.assertTrue((root/'report'/'image-audit.csv').exists())

if __name__=='__main__': unittest.main()
