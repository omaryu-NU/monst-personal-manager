#!/usr/bin/env python3
"""Fetch permission-documented icon URLs and publish them through local Vite public/."""
import argparse
import csv
import hashlib
import io
import json
import re
import sys
import time
import datetime
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ID = re.compile(r'^[0-9]{1,6}$')
MAX_BYTES = 5 * 1024 * 1024
EXT = {'image/png': '.png', 'image/jpeg': '.jpg', 'image/webp': '.webp'}
FIELDS = ('id', 'url', 'license', 'permission_reference', 'attribution')


def detect_image(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data) >= 24:
        return '.png'
    if data.startswith(b'\xff\xd8\xff') and data.endswith(b'\xff\xd9'):
        return '.jpg'
    if len(data) >= 16 and data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return '.webp'
    return None


def parse_rows(csv_path, allowed_hosts):
    with csv_path.open(encoding='utf-8-sig', newline='') as file:
        reader = csv.DictReader(file)
        if not set(FIELDS).issubset(reader.fieldnames or []):
            raise ValueError('CSVに必要な列: ' + ', '.join(FIELDS))
        rows = []
        seen = set()
        for n, row in enumerate(reader, 2):
            no = (row.get('id') or '').strip()
            url = (row.get('url') or '').strip()
            license_name = (row.get('license') or '').strip()
            evidence = (row.get('permission_reference') or '').strip()
            if not ID.fullmatch(no) or no in seen:
                raise ValueError(f'{n}行目: 図鑑No.が不正または重複: {no}')
            if not license_name or not evidence:
                raise ValueError(f'{n}行目: ライセンス・許可の根拠が必要です')
            parts = urllib.parse.urlsplit(url)
            if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password or
                    parts.hostname.lower() not in allowed_hosts or parts.port not in (None, 443)):
                raise ValueError(f'{n}行目: 許可ホスト上のHTTPS URLではありません')
            if not parts.path or parts.path == '/':
                raise ValueError(f'{n}行目: 画像ファイルへのURLが必要です')
            seen.add(no)
            rows.append({'id': no, 'url': url, 'license': license_name,
                         'permission_reference': evidence, 'attribution': (row.get('attribution') or '').strip()})
        return rows


class StrictRedirect(urllib.request.HTTPRedirectHandler):
    def __init__(self, allowed_hosts):
        self.allowed_hosts = allowed_hosts

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        parts = urllib.parse.urlsplit(newurl)
        if parts.scheme != 'https' or (parts.hostname or '').lower() not in self.allowed_hosts or parts.port not in (None,443):
            raise ValueError('許可されていないリダイレクト先です')
        return super().redirect_request(request, fp, code, msg, headers, newurl)


def fetch_image(url, allowed_hosts):
    opener = urllib.request.build_opener(StrictRedirect(allowed_hosts))
    req = urllib.request.Request(url, headers={'User-Agent': 'MonstPersonalManagerApprovedImageImporter/1.0', 'Accept':'image/png,image/jpeg,image/webp'})
    with opener.open(req, timeout=20) as response:
        length = response.headers.get('Content-Length')
        if length and int(length) > MAX_BYTES:
            raise ValueError('画像が5MBを超えています')
        mime = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
        # Some permitted image CDNs omit Content-Type despite returning valid image bytes.
        # A non-empty but non-image Content-Type is still rejected.
        if mime and mime not in EXT:
            raise ValueError(f'画像のContent-Typeではありません: {mime}')
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError('画像が5MBを超えています')
        ext = detect_image(data)
        if ext is None:
            raise ValueError('画像の実データではありません')
        if mime and ext != EXT[mime]:
            raise ValueError('画像形式とContent-Typeが一致しません')
        return data, ext


def load_manifest(path):
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if data.get('version') != 1 or not isinstance(data.get('icons'), dict):
        raise ValueError('既存の画像manifestが不正です')
    icons = data['icons']
    for k, value in icons.items():
        if not ID.fullmatch(k) or value not in {f'/character-icons/{k}{ext}' for ext in EXT.values()}:
            raise ValueError('既存の画像manifestに不正なパスがあります')
    return dict(icons)


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    tmp.replace(path)


def run(csv_path, output, allowed_hosts, *, apply=False, limit=10, delay=3.0, fetcher=None, allow_denied=False):
    if not allowed_hosts:
        raise ValueError('--allow-host を指定してください')
    if limit < 1 or delay < 1:
        raise ValueError('--limitは1以上、--delayは1秒以上にしてください')
    rows = parse_rows(csv_path, allowed_hosts)
    current = load_manifest(output / 'manifest.json')
    report = {'mode': 'apply' if apply else 'dry-run', 'input': len(rows), 'already_registered': 0,
              'downloaded': 0, 'errors': [], 'denied': [], 'pending': 0}
    cooldown_file = output / 'denied-urls.json'
    cooldown = json.loads(cooldown_file.read_text(encoding='utf-8')) if cooldown_file.exists() else {}
    if not isinstance(cooldown, dict):
        raise ValueError('403待機状態の形式が不正です')
    now = datetime.datetime.now(datetime.timezone.utc)
    pending = []
    for row in rows:
        if row['id'] in current:
            report['already_registered'] += 1
        elif (row['url'] in cooldown and
              isinstance(cooldown[row['url']], str) and
              datetime.datetime.fromisoformat(cooldown[row['url']]) > now):
            report['denied'].append({'id':row['id'],'reason':'403 cooldown until '+cooldown[row['url']]})
        else:
            pending.append(row)
    report['pending'] = len(pending)
    if not apply:
        return report
    fetcher = fetcher or fetch_image
    output.mkdir(parents=True, exist_ok=True)
    evidence_path = output / 'rights-evidence.json'
    if evidence_path.exists():
        evidence = json.loads(evidence_path.read_text(encoding='utf-8'))
        if not isinstance(evidence, dict):
            raise ValueError('権利証跡ファイルが不正です')
    else:
        evidence = {}
    for index, row in enumerate(pending[:limit]):
        if index:
            time.sleep(delay)
        no = row['id']
        try:
            # No 403 bypass, no cookies, no proxy tricks. Fail closed on permission errors.
            data, ext = fetcher(row['url'], allowed_hosts)
            dest = output / (no + ext)
            if dest.exists() and dest.read_bytes() != data:
                raise ValueError('同一No.の既存画像と内容が異なります')
            if not dest.exists():
                tmp = output / (no + ext + '.tmp')
                tmp.write_bytes(data)
                tmp.replace(dest)
            current[no] = f'/character-icons/{no}{ext}'
            evidence[no] = {**row, 'sha256': hashlib.sha256(data).hexdigest()}
            atomic_json(output / 'manifest.json', {'version': 1, 'icons': current})
            atomic_json(evidence_path, evidence)
            report['downloaded'] += 1
        except urllib.error.HTTPError as exc:
            if exc.code == 403 and allow_denied:
                cooldown[row['url']] = (now + datetime.timedelta(days=30)).isoformat()
                atomic_json(cooldown_file, cooldown)
                report['denied'].append({'id':no,'reason':'HTTP 403; no retries for 30 days'})
            else:
                report['errors'].append({'id':no,'error':str(exc)[:180]})
        except (urllib.error.URLError, OSError, ValueError, TimeoutError) as exc:
            report['errors'].append({'id': no, 'error': str(exc)[:180]})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', type=Path, required=True, help='利用許可済み画像CSV')
    parser.add_argument('--allow-host', action='append', required=True, help='画像配信許可ホスト。複数指定可能')
    parser.add_argument('--output', type=Path, default=Path('public/character-icons'))
    parser.add_argument('--limit', type=int, default=10)
    parser.add_argument('--delay', type=float, default=3.0)
    parser.add_argument('--apply', action='store_true', help='指定しないと検証のみ')
    parser.add_argument('--allow-denied', action='store_true', help='403画像は30日再試行せず報告し、他の画像を継続')
    parser.add_argument('--report', type=Path, help='取得結果のJSON出力')
    args = parser.parse_args(argv)
    try:
        result = run(args.csv, args.output, {host.lower().strip() for host in args.allow_host},
                     apply=args.apply, limit=args.limit, delay=args.delay, allow_denied=args.allow_denied)
        if args.report:
            atomic_json(args.report, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if not result['errors'] else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))


if __name__ == '__main__':
    sys.exit(main())
