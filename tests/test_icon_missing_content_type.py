"""Regression tests for image servers that omit Content-Type."""
import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from auto_import_approved_icons import fetch_image

JPEG = b'\xff\xd8\xff' + b'\x00' * 16 + b'\xff\xd9'
HOSTS = {'img.gamewith.jp'}
URL = 'https://img.gamewith.jp/article_tools/monst/gacha/112.jpg'

class FakeResponse:
    def __init__(self, data, content_type=None):
        self.data = io.BytesIO(data)
        self.headers = {} if content_type is None else {'Content-Type': content_type}
    def read(self, n=-1): return self.data.read(n)
    def __enter__(self): return self
    def __exit__(self, *args): return False

class TestMissingContentType(unittest.TestCase):
    def check(self, data, mime=None):
        class FakeOpener:
            def open(self, request, timeout):
                return FakeResponse(data, mime)
        with patch('auto_import_approved_icons.urllib.request.build_opener', return_value=FakeOpener()):
            return fetch_image(URL, HOSTS)

    def test_accepts_jpeg_without_content_type(self):
        self.assertEqual(self.check(JPEG), (JPEG, '.jpg'))

    def test_accepts_jpeg_with_content_type(self):
        self.assertEqual(self.check(JPEG, 'image/jpeg'), (JPEG, '.jpg'))

    def test_rejects_html_without_content_type(self):
        with self.assertRaisesRegex(ValueError, '実データ'):
            self.check(b'<html>Not an image</html>')

    def test_rejects_html_content_type_even_with_image_bytes(self):
        with self.assertRaisesRegex(ValueError, 'Content-Type'):
            self.check(JPEG, 'text/html')

    def test_rejects_mismatch(self):
        with self.assertRaisesRegex(ValueError, '一致'):
            self.check(JPEG, 'image/png')

if __name__ == '__main__': unittest.main()
