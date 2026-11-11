import unittest
from install_phase23_workflow import patch

BASE='  run: python scripts/technophere_catalog.py --pages 5 --profiles 5 --delay 2.5 --profile-strategy stratified\n'
class Phase23WorkflowTests(unittest.TestCase):
    def test_patch_and_idempotence(self):
        result,yes=patch(BASE)
        self.assertTrue(yes)
        self.assertEqual(result.count('--detail-refresh 1'),1)
        self.assertEqual(patch(result),(result,False))
    def test_refuses_wrong_strategy(self):
        with self.assertRaises(ValueError):patch(BASE.replace('stratified','newest_first'))
    def test_preserves_others(self):
        result,_=patch('hello\n'+BASE+'bye\n')
        self.assertTrue(result.startswith('hello\n'))
        self.assertTrue(result.endswith('bye\n'))
if __name__=='__main__':unittest.main()
