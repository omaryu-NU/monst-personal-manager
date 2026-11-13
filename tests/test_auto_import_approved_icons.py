import csv
import json
import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from auto_import_approved_icons import run, parse_rows, detect_image

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 20

class TestAutoApprovedIcons(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.csv = self.root / 'images.csv'

    def write(self, rows):
        with self.csv.open('w', encoding='utf-8', newline='') as fp:
            writer = csv.DictWriter(fp, fieldnames=['id','url','license','permission_reference','attribution'])
            writer.writeheader()
            writer.writerows(rows)

    def row(self, id='112', url='https://licensed.example/icons/112.png', permission='contract-123'):
        return dict(id=id, url=url, license='Authorized for redistribution', permission_reference=permission, attribution='Creator')

    def test_dry_run_makes_no_files_and_no_requests(self):
        self.write([self.row()])
        result = run(self.csv, self.root/'out', {'licensed.example'})
        self.assertEqual(result['pending'], 1)
        self.assertFalse((self.root/'out').exists())

    def test_batch_import_and_resume(self):
        self.write([self.row(), self.row(id='113',url='https://licensed.example/icons/113.png')])
        f=lambda url,hosts: (PNG,'.png')
        a=run(self.csv,self.root/'out',{'licensed.example'},apply=True,limit=1,fetcher=f)
        self.assertEqual(a['downloaded'],1)
        b=run(self.csv,self.root/'out',{'licensed.example'},apply=True,limit=2,fetcher=f)
        self.assertEqual(b['downloaded'],1)
        self.assertEqual(b['already_registered'],1)
        icons=json.loads((self.root/'out'/'manifest.json').read_text())['icons']
        self.assertEqual(icons['113'],'/character-icons/113.png')
        self.assertEqual(len(json.loads((self.root/'out'/'rights-evidence.json').read_text())),2)

    def test_reject_host_not_allowlisted(self):
        self.write([self.row(url='https://unapproved.example/112.png')])
        with self.assertRaises(ValueError):
            parse_rows(self.csv, {'licensed.example'})

    def test_reject_incomplete_permission(self):
        self.write([self.row(permission='')])
        with self.assertRaises(ValueError):
            parse_rows(self.csv, {'licensed.example'})

    def test_reject_duplicate_ids(self):
        self.write([self.row(),self.row()])
        with self.assertRaises(ValueError):
            parse_rows(self.csv, {'licensed.example'})

    def test_failed_download_does_not_create_manifest(self):
        self.write([self.row()])
        def fails(url,hosts):
            raise ValueError('403 Forbidden')
        report=run(self.csv,self.root/'out',{'licensed.example'},apply=True,fetcher=fails)
        self.assertEqual(report['downloaded'],0)
        self.assertEqual(len(report['errors']),1)
        self.assertFalse((self.root/'out'/'manifest.json').exists())

    def test_existing_manifest_is_preserved(self):
        self.write([self.row(id='113',url='https://licensed.example/icons/113.png')])
        dest=self.root/'out'
        dest.mkdir()
        (dest/'manifest.json').write_text(json.dumps({'version':1,'icons':{'112':'/character-icons/112.jpg'}}))
        report=run(self.csv,dest,{'licensed.example'},apply=True,fetcher=lambda *_: (PNG,'.png'))
        self.assertEqual(report['downloaded'],1)
        self.assertIn('112',json.loads((dest/'manifest.json').read_text())['icons'])

    def test_magic_detection(self):
        self.assertEqual(detect_image(PNG),'.png')
        self.assertIsNone(detect_image(b'<html>403 Forbidden</html>'))

if __name__ == '__main__': unittest.main()

class TestDeniedCooldown(unittest.TestCase):
    def test_403_is_logged_and_not_retried_when_opted_in(self):
        import urllib.error
        import datetime
        root=Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__('shutil').rmtree(root))
        path=root/'sources.csv'
        path.write_text('id,url,license,permission_reference,attribution\n112,https://licensed.example/icons/112.png,permission,owner-confirmed,Creator\n')
        called=[0]
        def denied(url, hosts):
            called[0]+=1
            raise urllib.error.HTTPError(url,403,'Forbidden',{},None)
        first=run(path,root/'out',{'licensed.example'},apply=True,fetcher=denied,allow_denied=True)
        second=run(path,root/'out',{'licensed.example'},apply=True,fetcher=denied,allow_denied=True)
        self.assertEqual(called[0],1)
        self.assertEqual(len(first['denied']),1)
        self.assertEqual(len(second['denied']),1)
        self.assertEqual(len(second['errors']),0)
