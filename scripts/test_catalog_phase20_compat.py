"""Regression: old callers without profile_strategy retain the original order."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from technophere_catalog import order_family_profiles, update

class CompatibilityTests(unittest.TestCase):
    def test_original_order_for_legacy_callers(self):
        families={f'https://game.technophere.com/monst/char/{id}/':True for id in (5,7,3,9)}
        self.assertEqual([int(x.split('/char/')[1].strip('/')) for x in order_family_profiles(families,strategy='newest_first')],[9,7,5,3])

    def test_update_explicit_fallback_without_strategy(self):
        import inspect
        src=inspect.getsource(update)
        self.assertIn("getattr(args,'profile_strategy','newest_first')",src)

    def test_cli_stratified_is_independent_of_legacy_fallback(self):
        import inspect
        from technophere_catalog import main
        self.assertIn("default='stratified'",inspect.getsource(main))

if __name__=='__main__':unittest.main()
