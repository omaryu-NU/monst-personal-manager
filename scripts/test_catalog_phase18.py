import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).parent))
import catalog_image_rate_limit as rl
import catalog_local_sync_guard as sync

NOW=datetime(2026,11,11,9,0,tzinfo=timezone.utc)

class PauseTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'pause.json'
        self.report=Path(self.temp.name)/'run.json'
        self.report.write_text(json.dumps({'rateLimited':True,'results':[{'status':'rate_limited','http_status':429}]}))
    def test_no_pause_allows(self):self.assertTrue(rl.check(self.path,now=NOW)['allowed'])
    def test_record_and_hold(self):
        p=rl.record(self.path,self.report,now=NOW)
        self.assertEqual(p['minimumPauseHours'],24)
        self.assertFalse(rl.check(self.path,now=NOW+timedelta(hours=23))['allowed'])
    def test_expiry(self):
        rl.record(self.path,self.report,now=NOW)
        self.assertTrue(rl.check(self.path,now=NOW+timedelta(hours=24))['allowed'])
    def test_no_false_429_record(self):
        self.report.write_text(json.dumps({'rateLimited':False,'results':[]}))
        with self.assertRaises(ValueError):rl.record(self.path,self.report,now=NOW)
        self.assertFalse(self.path.exists())
    def test_missing_explicit_429(self):
        self.report.write_text(json.dumps({'rateLimited':True,'results':[{'status':'request_error'}]}))
        with self.assertRaises(ValueError):rl.record(self.path,self.report,now=NOW)
    def test_bad_state_blocks(self):
        self.path.write_text('{bad json')
        self.assertEqual(rl.check(self.path,now=NOW)['reason'],'invalid_pause_state')
        with self.assertRaises(ValueError):rl.record(self.path,self.report,now=NOW)
    def test_record_cannot_shorten(self):
        rl.record(self.path,self.report,now=NOW,hours=48)
        p=rl.record(self.path,self.report,now=NOW+timedelta(hours=1),hours=24)
        self.assertEqual(rl.dt(p['pauseUntil']),NOW+timedelta(hours=48))
    def test_reject_naive_time(self):
        with self.assertRaises(ValueError):rl.dt('2026-11-11T09:00:00')
    def test_reject_short_pause(self):
        with self.assertRaises(ValueError):rl.record(self.path,self.report,now=NOW,hours=2)

class GitGuardTests(unittest.TestCase):
    def setUp(self):
        import subprocess
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        subprocess.run(['git','-C',str(self.root),'config','user.email','test@example.com'],check=True)
        subprocess.run(['git','-C',str(self.root),'config','user.name','Test'],check=True)
        self.target=self.root/sync.TARGET
        self.target.write_text('{"count":1}\n')
        (self.root/'README.md').write_text('untouched')
        subprocess.run(['git','-C',str(self.root),'add','.'],check=True)
        subprocess.run(['git','-C',str(self.root),'commit','-qm','init'],check=True)
    def test_no_change(self):
        self.assertEqual(sync.prepare(self.root)['status'],'nothing_to_backup')
    def test_dry_run_preserves(self):
        self.target.write_text('{"count":2}\n')
        result=sync.prepare(self.root)
        self.assertFalse(result['applied']);self.assertIn('count":2',self.target.read_text())
    def test_apply_backup_only_target(self):
        self.target.write_text('{"count":2}\n')
        (self.root/'README.md').write_text('personal change')
        result=sync.prepare(self.root,apply=True)
        self.assertTrue(result['applied'])
        self.assertIn('count":2',Path(result['backup']).read_text())
        self.assertIn('count":1',self.target.read_text())
        self.assertEqual((self.root/'README.md').read_text(),'personal change')
    def test_refuses_staged(self):
        import subprocess
        self.target.write_text('{"count":2}\n')
        subprocess.run(['git','-C',str(self.root),'add',sync.TARGET],check=True)
        with self.assertRaises(ValueError):sync.prepare(self.root,apply=True)

class WorkflowTests(unittest.TestCase):
    def test_order_and_fail_closed(self):
        txt=(Path(__file__).parents[1]/'.github/workflows/catalog-update.yml').read_text()
        self.assertLess(txt.index('Phase 18 persistent image pause guard'),txt.index('Phase 16 verified image backfill'))
        self.assertLess(txt.index('Persist only image HTTP 429 cooldown'),txt.index('Restore HTTP-verified catalog images'))
        self.assertIn('git add -- catalog-image-rate-limit.json',txt)
        self.assertIn("steps.image_pause_guard.outputs.allowed == 'true'",txt)
        self.assertIn('exit 1',txt)

if __name__=='__main__':unittest.main()
