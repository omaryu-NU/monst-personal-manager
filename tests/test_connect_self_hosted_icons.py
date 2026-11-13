import importlib.util
import pathlib
import unittest

MODULE_PATH = pathlib.Path(__file__).parents[1] / 'scripts' / 'connect_self_hosted_icons.py'
spec = importlib.util.spec_from_file_location('connector_icons', MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TestInstaller(unittest.TestCase):
    def test_installs_one_icon_preserves_other_markup(self):
        src = '''import { useState } from 'react';\nconst test = () => <><span className="char-icon">{c.image?<img src={c.image}/>:c.name.slice(0,1)}</span><button onClick={() => addOwned(c.id)}>所持に追加</button></>;'''
        result = module.patch_source(src)
        self.assertIn('<SelfHostedCharacterIcon id={c.id} name={c.name} />', result)
        self.assertIn('addOwned(c.id)', result)
        self.assertNotIn('src={c.image}', result)
        self.assertEqual(module.patch_source(result), result)
    def test_reject_no_match(self):
        with self.assertRaises(ValueError): module.patch_source('<div>not here</div>')
    def test_reject_multiple_matches(self):
        src = '<span className="char-icon">{c.name}</span>' * 2
        with self.assertRaises(ValueError): module.patch_source(src)
    def test_reject_unknown_markup(self):
        with self.assertRaises(ValueError): module.patch_source('<span className="char-icon">unknown</span>')

if __name__ == '__main__': unittest.main()
