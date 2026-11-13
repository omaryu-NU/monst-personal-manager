import importlib.util
import unittest
from pathlib import Path

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('queue_module', root / 'scripts/prepare_gamewith_icon_queue.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class QueueTests(unittest.TestCase):
    def test_valid(self):
        rows, bad = module.build_queue({'records':[{'id':'112','image':'https://img.gamewith.jp/article_tools/monst/gacha/112.jpg'}]}, permission_reference='owner email 2026-11-13')
        self.assertEqual(len(rows), 1)
        self.assertEqual(bad, [])
    def test_wrong_id_filename_is_rejected(self):
        rows,bad = module.build_queue({'records':[{'id':'112','image':'https://img.gamewith.jp/113.jpg'}]},permission_reference='yes')
        self.assertEqual(rows, []); self.assertEqual(len(bad),1)
    def test_wrong_host_is_rejected(self):
        rows,bad=module.build_queue({'records':[{'id':'112','image':'https://evil.example/112.jpg'}]},permission_reference='yes')
        self.assertEqual(rows, []); self.assertEqual(len(bad),1)
    def test_duplicate_same_url(self):
        row={'id':'112','image':'https://img.gamewith.jp/112.jpg'}
        rows,bad=module.build_queue({'records':[row,row]},permission_reference='yes')
        self.assertEqual(len(rows),1); self.assertEqual(bad,[])
    def test_missing_permission(self):
        with self.assertRaises(ValueError): module.build_queue({'records':[]},permission_reference='')
    def test_non_image(self):
        rows,bad=module.build_queue({'records':[{'id':'112','image':'https://img.gamewith.jp/112.svg'}]},permission_reference='yes')
        self.assertEqual(len(rows),0); self.assertEqual(len(bad),1)

if __name__ == '__main__': unittest.main()
