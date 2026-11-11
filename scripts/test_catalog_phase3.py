import json, os, sys, tempfile, unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import technophere_catalog as t
from test_catalog_family import HTML, LIST, P, FakeSession

class BadProfileSession(FakeSession):
    def get(self,url,timeout=25):
        if '/char/' in url:
            text=HTML.replace('No.9549', 'No.9547').replace('No.9548', 'No.9546')
            class Response:
                content=text.encode(); text=text
                def raise_for_status(self):pass
            return Response()
        return super().get(url,timeout)

class Phase3Tests(unittest.TestCase):
    def _run(self,session):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);old_out,old_state=t.OUT,t.STATE
            try:
                t.OUT=root/'public/catalog'; t.STATE=root/'state.json'
                with patch.dict(os.environ,{'TECHNOPHERE_REUSE_APPROVED':'true'}):
                    manifest=t.update(SimpleNamespace(pages=2,profiles=1,delay=0.5),session,check_robots=False,wait=lambda _:None)
                state=json.loads(t.STATE.read_text())
                return manifest,state
            finally:t.OUT=old_out;t.STATE=old_state
    def test_profile_keeps_form_inventory(self):
        manifest,state=self._run(FakeSession())
        self.assertEqual(manifest['coverage']['familiesVerified'],1)
        self.assertEqual(set(state['verifiedFamilyFormIDs'][P]),{'9548','9549'})
    def test_representative_mismatch_never_verified(self):
        # Monkeypatch parser to emit a structurally valid but unrelated form.
        with patch.object(t,'parse_family',return_value=[{'id':'123','name':'Other','attribute':'火','source':P}]):
            manifest,state=self._run(FakeSession())
        self.assertEqual(manifest['coverage']['familiesVerified'],0)
        self.assertEqual(manifest['coverage']['unmatchedRepresentativeProfilesThisRun'],1)
        self.assertFalse(state['verifiedFamilyURLs'])

if __name__=='__main__': unittest.main()
