"""Regression: transient failure on one family cannot prevent others from being verified."""
import json, os, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import technophere_catalog as t
from test_catalog_family import HTML, FakeResponse

U1='https://game.technophere.com/monst/char/9548/'
U2='https://game.technophere.com/monst/char/9540/'
LIST='<p>1 / 50ページ</p><a href="/monst/char/9548/">マ マクスウェル 真獣神化 闇 貫通・超バランス・亜人・No.9549</a><a href="/monst/char/9540/">マ マクスウェル 真獣神化 闇 貫通・超バランス・亜人・No.9540</a>'
class MixedSession:
    def get(self,url,timeout=25):
        if url.startswith(U1): return FakeResponse('<div>Missing forms</div>')
        if url.startswith(U2): return FakeResponse(HTML.replace('No.9549','No.9540'))
        return FakeResponse(LIST)

class Phase4Tests(unittest.TestCase):
    def test_failed_profile_does_not_starve_next_profile(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); out,state=t.OUT,t.STATE
            t.OUT=root/'public/catalog';t.STATE=root/'catalog-update-state.json'
            try:
                with patch.dict(os.environ,{'TECHNOPHERE_REUSE_APPROVED':'true'}):
                    run1=t.update(SimpleNamespace(pages=2,profiles=1,delay=0.5),MixedSession(),check_robots=False,wait=lambda _:None)
                    run2=t.update(SimpleNamespace(pages=2,profiles=1,delay=0.5),MixedSession(),check_robots=False,wait=lambda _:None)
                self.assertEqual(run1['coverage']['familiesVerified'],0)
                self.assertEqual(run2['coverage']['familiesVerified'],1)
                self.assertEqual(run2['coverage']['familiesRemaining'],1)
                s=json.loads(t.STATE.read_text())
                self.assertIn(U1,s['profileRetry'])
                self.assertIn(U2,s['verifiedFamilyURLs'])
            finally:t.OUT=out;t.STATE=state
    def test_old_state_without_retry_fields_is_supported(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);out,state=t.OUT,t.STATE
            t.OUT=root/'public/catalog';t.STATE=root/'catalog-update-state.json'
            try:
                t.atomic(t.STATE,{'nextPage':2,'totalPages':50,'visitedPages':[1]})
                with patch.dict(os.environ,{'TECHNOPHERE_REUSE_APPROVED':'true'}):
                    manifest=t.update(SimpleNamespace(pages=2,profiles=0,delay=0.5),MixedSession(),check_robots=False,wait=lambda _:None)
                self.assertEqual(manifest['coverage']['listingPagesVisited'],2)
            finally:t.OUT=out;t.STATE=state
if __name__=='__main__':unittest.main()
