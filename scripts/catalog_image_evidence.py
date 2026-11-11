#!/usr/bin/env python3
"""Phase13: preserve HTTP-verified image URLs across catalog scraper runs.

Import only evidence from an --apply report which is reflected in the current
catalog; replay it without network access after each catalog scrape. This tool
never touches Firestore and never overwrites a different existing image URL.
"""
from __future__ import annotations
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

PREFIX = 'https://game.technophere.com/monst/wp-content/uploads/monst-lab/icon/'
CHUNK_NAME = re.compile(r'characters-\d{4}\.json\Z')


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    tmp.replace(path)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def checked_url(rid, url):
    if not isinstance(rid, str) or not rid.isdecimal() or not 1 <= int(rid) <= 999999:
        return False
    if not isinstance(url, str) or url != PREFIX + str(int(rid)) + '.webp':
        return False
    p = urlparse(url)
    return p.scheme == 'https' and p.hostname == 'game.technophere.com' and not p.query and not p.fragment


def catalog_records(folder):
    folder = Path(folder)
    manifest = read(folder / 'manifest.json')
    chunks = manifest.get('chunks')
    if not isinstance(chunks, list) or not chunks:
        raise ValueError('Manifest has no chunks')
    documents, mapping = {}, {}
    for chunk in chunks:
        name = chunk.get('path')
        if not isinstance(name, str) or not CHUNK_NAME.fullmatch(name):
            raise ValueError('Unsafe chunk path')
        doc = read(folder / name)
        records = doc.get('characters')
        if not isinstance(records, list) or len(records) != chunk.get('count'):
            raise ValueError('Chunk count mismatch: ' + name)
        documents[name] = doc
        for record in records:
            rid = str(record.get('id', ''))
            if not rid.isdecimal() or rid in mapping:
                raise ValueError('Invalid or duplicate character ID: ' + rid)
            mapping[rid] = (name, record)
    if len(mapping) != manifest.get('count'):
        raise ValueError('Manifest record count mismatch')
    return documents, mapping


def import_report(folder, evidence_path, report_path, *, apply=False):
    _, catalog = catalog_records(folder)
    report = read(report_path)
    if report.get('dryRun') is not False:
        raise ValueError('Only --apply reports can establish saved evidence')
    verified = report.get('verified')
    if not isinstance(verified, list):
        raise ValueError('Missing verified list')
    confirmed = {str(entry.get('id')) for entry in report.get('results', [])
                 if isinstance(entry, dict) and entry.get('status') == 'verified'
                 and entry.get('http_status') == 200}
    old = read(evidence_path) if Path(evidence_path).exists() else {'schema': 1, 'images': {}}
    if old.get('schema') != 1 or not isinstance(old.get('images'), dict):
        raise ValueError('Unrecognized evidence schema')
    images = dict(old['images'])
    added = 0
    conflicts = []
    for entry in verified:
        if not isinstance(entry, dict):
            raise ValueError('Bad verified entry')
        rid, url = str(entry.get('id', '')), entry.get('url')
        if rid not in confirmed or not checked_url(rid, url):
            raise ValueError('No matching successful HTTP 200 evidence for ID ' + rid)
        if rid not in catalog or catalog[rid][1].get('image') != url:
            raise ValueError('HTTP-verified URL not found in saved catalog for ID ' + rid)
        if rid in images and images[rid] != url:
            conflicts.append(rid)
            continue
        if rid not in images:
            images[rid] = url
            added += 1
    if conflicts:
        raise ValueError('Conflicting previously verified images: ' + ','.join(conflicts))
    if apply:
        atomic(Path(evidence_path), {'schema': 1, 'images': dict(sorted(images.items(), key=lambda p:int(p[0])))})
    return {'action': 'import', 'report': str(report_path), 'alreadyStored': len(old['images']),
            'newEvidence': added, 'totalEvidence': len(images), 'written': bool(apply)}


def replay(folder, evidence_path, *, apply=False):
    docs, catalog = catalog_records(folder)
    evidence = read(evidence_path)
    if evidence.get('schema') != 1 or not isinstance(evidence.get('images'), dict):
        raise ValueError('Unrecognized evidence schema')
    touched = set()
    restored = 0
    unchanged = 0
    missing = []
    conflicts = []
    # First validate everything, then write to prevent partial updates on conflict.
    for rid, url in evidence['images'].items():
        if not checked_url(rid, url):
            raise ValueError('Invalid image evidence for ID ' + str(rid))
        if rid not in catalog:
            missing.append(rid)
            continue
        filename, record = catalog[rid]
        old_url = record.get('image')
        if old_url and old_url != url:
            conflicts.append(rid)
        elif old_url == url:
            unchanged += 1
        else:
            restored += 1
            touched.add(filename)
    if conflicts:
        raise ValueError('Catalog contains different image URLs: ' + ','.join(conflicts))
    if apply:
        for rid, url in evidence['images'].items():
            if rid in catalog and not catalog[rid][1].get('image'):
                catalog[rid][1]['image'] = url
        for name in touched:
            atomic(Path(folder) / name, docs[name])
    return {'action': 'replay', 'evidence': len(evidence['images']), 'alreadyPresent': unchanged,
            'toRestore': restored, 'missingCatalogIDs': sorted(missing, key=int),
            'conflicts': conflicts, 'written': bool(apply),
            'note': 'Image bytes and character identity are not reverified during offline replay.'}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['import', 'replay'])
    p.add_argument('--catalog', default='public/catalog')
    p.add_argument('--evidence', default='catalog-image-evidence.json')
    p.add_argument('--report', help='Required for import; a previously applied Phase11/12 report')
    p.add_argument('--apply', action='store_true')
    p.add_argument('--output', default='local-reports/image-evidence/result.json')
    args = p.parse_args()
    if args.action == 'import':
        if not args.report: p.error('import requires --report')
        result = import_report(args.catalog, args.evidence, args.report, apply=args.apply)
    else:
        result = replay(args.catalog, args.evidence, apply=args.apply)
    result['generatedAt'] = datetime.now(timezone.utc).isoformat()
    atomic(Path(args.output), result)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
