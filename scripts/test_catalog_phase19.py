import json
import tempfile
import unittest
from pathlib import Path
from catalog_phase19 import audit, family_url


class Phase19AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.catalog = self.root / 'catalog'
        self.catalog.mkdir()
        self.family = 'https://game.technophere.com/monst/char/123/'
        self.records = [
            {'id': '123', 'name': 'A', 'attribute': '火', 'source': self.family,
             'abilities': ['x'], 'image': 'https://game.technophere.com/monst/a.webp'},
            {'id': '124', 'name': 'B', 'attribute': '水', 'source': self.family + '#f124'},
        ]
        self.write_catalog()

    def tearDown(self):
        self.temp.cleanup()

    def write_catalog(self):
        (self.catalog / 'manifest.json').write_text(json.dumps({
            'count': len(self.records), 'chunks': [{'path': 'characters-0001.json',
                                                   'count': len(self.records)}]}))
        (self.catalog / 'characters-0001.json').write_text(json.dumps({'characters': self.records}))

    def state(self, verified=True, form_ids=('123', '124')):
        path = self.root / 'state.json'
        path.write_text(json.dumps({'totalPages': 3, 'visitedPages': [1, 3],
            'verifiedFamilyURLs': [self.family] if verified else [],
            'verifiedFamilyFormIDs': {self.family: list(form_ids)} if verified else {}}))
        return path

    def test_no_state_does_not_infer_verified(self):
        s = audit(self.catalog, None)
        self.assertEqual(s['familyStatuses']['unknown_no_state'], 1)
        self.assertFalse(s['allFormsProvenComplete'])

    def test_verified_subset_detects_missing_form(self):
        self.records.pop()
        self.write_catalog()
        s = audit(self.catalog, self.state())
        self.assertEqual(s['formStateDiscrepancies'], 1)
        self.assertTrue(s['structuralIssuesFound'])

    def test_verified_present_still_not_complete(self):
        s = audit(self.catalog, self.state())
        self.assertEqual(s['familyStatuses']['parsed_at_least_once'], 1)
        self.assertFalse(s['allFormsProvenComplete'])

    def test_missing_pages(self):
        s = audit(self.catalog, self.state())
        self.assertEqual(s['missingListingPages'], [2])

    def test_missing_field_counts(self):
        s = audit(self.catalog, self.state())
        self.assertEqual(s['missingFieldCounts']['image'], 1)
        self.assertEqual(s['missingFieldCounts']['hp'], 2)

    def test_output_files_are_created(self):
        out = self.root / 'out'
        audit(self.catalog, self.state(), out)
        self.assertTrue((out / 'family-status.csv').exists())
        self.assertTrue((out / 'structural-issues.csv').exists())
        self.assertTrue((out / 'summary.json').exists())

    def test_duplicate_id_is_structural_error(self):
        self.records.append(dict(self.records[0]))
        self.write_catalog()
        s = audit(self.catalog, self.state())
        self.assertEqual(s['duplicateIDCount'], 1)

    def test_manifest_mismatch(self):
        self.write_catalog()
        path = self.catalog / 'manifest.json'
        d = json.loads(path.read_text()); d['count'] = 999
        path.write_text(json.dumps(d))
        self.assertFalse(audit(self.catalog, self.state())['manifestCountMatches'])

    def test_source_fragment_family_is_normalized(self):
        self.assertEqual(family_url(self.family + '#f124'), self.family)
        self.assertEqual(family_url('https://not-the-site.com/monst/char/123/'), '')

    def test_no_network_or_mutation(self):
        before = (self.catalog / 'characters-0001.json').read_bytes()
        audit(self.catalog, self.state(), self.root / 'reports')
        self.assertEqual(before, (self.catalog / 'characters-0001.json').read_bytes())

    def test_missing_state_can_use_manifest_coverage(self):
        d = json.loads((self.catalog / 'manifest.json').read_text())
        d['coverage'] = {'totalPages': 4, 'visitedPages': [1, 2]}
        (self.catalog / 'manifest.json').write_text(json.dumps(d))
        s = audit(self.catalog)
        self.assertEqual(s['missingListingPages'], [3, 4])
        self.assertFalse(s['stateAvailable'])


if __name__ == '__main__':
    unittest.main()
