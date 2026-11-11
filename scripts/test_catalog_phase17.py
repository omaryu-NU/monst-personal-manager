import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from catalog_image_schedule_guard import evaluate

NOW=datetime(2026,11,11,12,0,tzinfo=timezone.utc)

class Phase17GuardTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);self.state=self.root/'state.json';self.evidence=self.root/'evidence.json'
        self.evidence.write_text(json.dumps({'schema':1,'images':{'112':'https://example.com/x.webp'}}))
        self.make_state(NOW-timedelta(hours=7))
    def make_state(self,dt):
        self.state.write_text(json.dumps({'schema':2,'lastProcessedID':116,'updatedAt':dt.isoformat()}))
    def check(self,**kw):return evaluate(self.state,self.evidence,now=NOW,**kw)
    def test_due_after_seven_hours(self):self.assertTrue(self.check()['runBackfill'])
    def test_cooldown_before_six_hours(self):
        self.make_state(NOW-timedelta(hours=5,minutes=59))
        self.assertEqual(self.check()['reason'],'cooldown_active')
    def test_six_hours_exactly(self):
        self.make_state(NOW-timedelta(hours=6))
        self.assertTrue(self.check()['runBackfill'])
    def test_hosting_blocks_auto_backfill(self):
        self.assertEqual(self.check(hosting_enabled=True)['reason'],'hosting_enabled_blocks_unreviewed_image_backfill')
    def test_missing_state_fails_closed(self):
        self.state.unlink(); self.assertEqual(self.check()['reason'],'missing_or_invalid_state')
    def test_empty_evidence_fails_closed(self):
        self.evidence.write_text('{"schema":1,"images":{}}')
        self.assertEqual(self.check()['reason'],'missing_or_invalid_evidence')
    def test_future_timestamp_fails_closed(self):
        self.make_state(NOW+timedelta(hours=1));self.assertEqual(self.check()['reason'],'future_state_timestamp')
    def test_malformed_timestamp_fails_closed(self):
        self.state.write_text('{"schema":2,"lastProcessedID":116,"updatedAt":"no"}')
        self.assertEqual(self.check()['reason'],'missing_or_invalid_state')
    def test_no_timezone_fails_closed(self):
        self.make_state(datetime(2026,11,11,5,0));self.assertEqual(self.check()['reason'],'missing_or_invalid_state')
    def test_invalid_min_hours(self):
        with self.assertRaises(ValueError):self.check(min_hours=1)
    def test_workflow_gate_location_and_limits(self):
        text=(Path(__file__).resolve().parents[1]/'.github/workflows/catalog-update.yml').read_text()
        self.assertLess(text.index('Phase 17 scheduled image safety guard'),text.index('Phase 16 verified image backfill'))
        self.assertIn('steps.image_schedule_guard.outputs.run_backfill',text)
        self.assertIn('LIMIT=1',text)
        self.assertIn('DELAY=6',text)
        self.assertIn("vars.AUTO_DEPLOY_HOSTING != 'true'",text)
        self.assertIn("--min-hours 6",text)
        self.assertIn('Phase 14 image integration gate',text)
        self.assertIn('Commit validated catalog',text)
        self.assertIn('Deploy Hosting only',text)

if __name__=='__main__':unittest.main()
