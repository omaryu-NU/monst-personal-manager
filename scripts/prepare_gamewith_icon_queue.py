#!/usr/bin/env python3
"""Create a separate, validated GameWith image queue from previously collected JSON.

This script makes NO requests to GameWith. Never changes Technophere CSV.
"""
import argparse
import csv
import json
import re
from pathlib import Path
from urllib.parse import urlsplit, unquote

FIELDS = ('id', 'url', 'license', 'permission_reference', 'attribution')
MONSTER_ID = re.compile(r'[1-9][0-9]{0,6}')
VALID_EXT = {'.jpg', '.jpeg', '.png', '.webp'}

def build_queue(document, *, permission_reference):
    entries = document.get('records') if isinstance(document, dict) else None
    if not isinstance(entries, list):
        raise ValueError('input JSON must contain a records array')
    if not permission_reference.strip():
        raise ValueError('permission reference must be nonempty')
    result, rejected = {}, []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            rejected.append({'index': index, 'reason': 'non-object record'}); continue
        no = str(entry.get('id', '')).strip()
        url = str(entry.get('image') or entry.get('image_url') or '').strip()
        try:
            parsed = urlsplit(url)
            file_name = Path(unquote(parsed.path)).name
            stem = Path(file_name).stem
            ext = Path(file_name).suffix.lower()
            valid = (bool(MONSTER_ID.fullmatch(no)) and parsed.scheme == 'https'
                     and parsed.hostname == 'img.gamewith.jp' and parsed.port in (None, 443)
                     and not parsed.username and not parsed.password and not parsed.query
                     and not parsed.fragment and ext in VALID_EXT and stem == no)
        except ValueError:
            valid = False
        if not valid:
            rejected.append({'index': index, 'id': no, 'reason': 'not a verified numeric GameWith icon URL'})
            continue
        if no in result and result[no]['url'] != url:
            rejected.append({'index': index, 'id': no, 'reason': 'conflicting icon URL for same ID'})
            del result[no]
            continue
        result[no] = {'id': no, 'url': url,
                      'license': 'GameWith owner-authorized image reuse',
                      'permission_reference': permission_reference,
                      'attribution': 'GameWith'}
    return sorted(result.values(), key=lambda row: int(row['id'])), rejected

def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path('config/data/gamewith-observed-4455.json'))
    p.add_argument('--output', type=Path, default=Path('config/gamewith-approved-icon-sources.csv'))
    p.add_argument('--report', type=Path, default=Path('local-reports/gamewith-icons/queue-report.json'))
    p.add_argument('--permission-reference', required=True,
                   help='Record the actual GameWith authorization reference (date/email/ID)')
    p.add_argument('--apply', action='store_true', help='Write CSV only when supplied')
    args = p.parse_args(argv)
    data = json.loads(args.source.read_text(encoding='utf-8'))
    rows, rejected = build_queue(data, permission_reference=args.permission_reference)
    report = {'source_records': len(data['records']), 'queued': len(rows),
              'rejected_count': len(rejected), 'rejected_sample': rejected[:25],
              'output': str(args.output), 'mode': 'apply' if args.apply else 'dry-run'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    if args.apply:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp = args.output.with_suffix(args.output.suffix + '.tmp')
        with temp.open('w', encoding='utf-8', newline='') as fp:
            writer = csv.DictWriter(fp, fieldnames=FIELDS)
            writer.writeheader(); writer.writerows(rows)
        temp.replace(args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
