import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from import_gamewith_daily import remaining_budget
from setup_gamewith_100_and_icons import (update_workflow, update_catalog, OLD_STEP, OLD_CALL,
                                         OLD_IMG, NEW_IMG, NEW_STEP, NEW_CALL)

class GameWithDailyTests(unittest.TestCase):
    def test_new_day(self):
        self.assertEqual(remaining_budget({'day':'2026-11-12','attempts':98}, '2026-11-13',100),100)
    def test_same_day(self):
        self.assertEqual(remaining_budget({'day':'2026-11-13','attempts':30}, '2026-11-13',100),70)
    def test_exhausted(self):
        self.assertEqual(remaining_budget({'day':'2026-11-13','attempts':100}, '2026-11-13',100),0)
    def test_reject_invalid_limit(self):
        with self.assertRaises(ValueError): remaining_budget({},'2026-11-13',101)
    def test_workflow_patch_idempotent(self):
        original='timeout-minutes: 20\n' + OLD_STEP+'\n'+OLD_CALL+'\n'
        patched=update_workflow(original)
        self.assertIn(NEW_STEP,patched)
        self.assertIn(NEW_CALL,patched)
        self.assertIn('timeout-minutes: 60',patched)
        self.assertEqual(update_workflow(patched),patched)
    def test_workflow_fail_closed(self):
        with self.assertRaises(ValueError): update_workflow('foo')
    def test_catalog_patch_idempotent(self):
        original="import X from './X';\n"+OLD_IMG+'\n'
        patched=update_catalog(original)
        self.assertIn(NEW_IMG,patched)
        self.assertEqual(update_catalog(patched),patched)
    def test_catalog_fail_closed(self):
        with self.assertRaises(ValueError): update_catalog('no matching images')

if __name__=='__main__': unittest.main()
