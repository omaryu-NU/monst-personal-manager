#!/usr/bin/env python3
"""Offline read-only catalog gap and provenance audit (Phase 19).

Never claims every on-site evolution has been captured. Does not fetch URLs or
modify catalog, state, evidence, or Firebase data.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

FIELDS = ('image', 'abilities', 'evolution', 'type', 'style', 'race',
          'rarity', 'hp', 'attack', 'speed', 'ss', 'friendship')
FAMILY_PATH = re.compile(r'^/monst/char/\d+/?$')


def load_json(path, fallback=None):
    if path is None or not Path(path).is_file():
        return fallback
    return json.loads(Path(path).read_text(encoding='utf-8'))


def family_url(url):
    if not isinstance(url, str):
        return ''
    parsed = urlparse(url)
    if parsed.scheme != 'https' or parsed.netloc != 'game.technophere.com':
        return ''
    if not FAMILY_PATH.fullmatch(parsed.path):
        return ''
    return f'https://game.technophere.com{parsed.path.rstrip("/")}/'


def populated(value):
    if value is None or isinstance(value, bool):
        return False
    if isinstance(value, (list, dict, str)):
        return bool(value)
    return isinstance(value, (int, float))


def csv_write(path, headers, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as out:
        writer = csv.DictWriter(out, fieldnames=headers, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)


def audit(catalog, state_path=None, output=None):
    catalog = Path(catalog)
    manifest = load_json(catalog / 'manifest.json')
    if not isinstance(manifest, dict) or not isinstance(manifest.get('chunks'), list):
        raise ValueError('manifest.json is absent or malformed')

    state = load_json(state_path, None)
    if state is not None and not isinstance(state, dict):
        raise ValueError('state must be a JSON object')
    records = []
    chunk_errors = []
    for chunk in manifest['chunks']:
        path = chunk.get('path') if isinstance(chunk, dict) else None
        if not isinstance(path, str) or not re.fullmatch(r'characters-\d{4}\.json', path):
            chunk_errors.append({'chunk': str(path), 'problem': 'invalid_manifest_chunk_path'})
            continue
        content = load_json(catalog / path)
        if not isinstance(content, dict) or not isinstance(content.get('characters'), list):
            chunk_errors.append({'chunk': path, 'problem': 'missing_or_invalid_chunk'})
            continue
        if len(content['characters']) != chunk.get('count'):
            chunk_errors.append({'chunk': path, 'problem': 'chunk_count_mismatch'})
        records.extend(content['characters'])

    by_id = {}
    duplicates = []
    bad_records = []
    families = defaultdict(list)
    missing_rows = []
    counts = Counter()
    for index, rec in enumerate(records):
        if not isinstance(rec, dict):
            bad_records.append({'row': index, 'problem': 'not_an_object'})
            continue
        raw_id = str(rec.get('id', ''))
        if not raw_id.isdigit() or int(raw_id) <= 0:
            bad_records.append({'row': index, 'problem': 'invalid_id'})
            continue
        char_id = str(int(raw_id))
        if char_id in by_id:
            duplicates.append(char_id)
        by_id[char_id] = rec
        url = family_url(rec.get('source'))
        if url:
            families[url].append(char_id)
        for field in FIELDS:
            if not populated(rec.get(field)):
                counts[field] += 1
                missing_rows.append({'id': char_id, 'name': rec.get('name', ''),
                                     'family': url, 'field': field})

    verified_urls = set()
    verified_forms = {}
    visited = set()
    total_pages = 0
    if state is not None:
        total_pages = state.get('totalPages', 0)
        if not isinstance(total_pages, int) or isinstance(total_pages, bool) or not 1 <= total_pages <= 500:
            raise ValueError('invalid state totalPages')
        visited = {p for p in state.get('visitedPages', []) if type(p) is int and 1 <= p <= total_pages}
        verified_urls = {u for raw in state.get('verifiedFamilyURLs', []) if (u := family_url(raw))}
        for raw, ids in state.get('verifiedFamilyFormIDs', {}).items():
            u = family_url(raw)
            if u and isinstance(ids, list):
                verified_forms[u] = {str(int(x)) for x in ids if str(x).isdigit() and int(x) > 0}
    elif isinstance(manifest.get('coverage'), dict):
        coverage = manifest['coverage']
        total_pages = coverage.get('totalPages', 0)
        if type(total_pages) is int and 1 <= total_pages <= 500:
            visited = {p for p in coverage.get('visitedPages', []) if type(p) is int and 1 <= p <= total_pages}

    family_rows = []
    states = Counter()
    form_discrepancies = []
    for u, ids in sorted(families.items()):
        is_verified = u in verified_urls
        known = verified_forms.get(u, set())
        actual = set(ids)
        missing_ids = sorted(known - actual, key=int)
        if is_verified and not known:
            status = 'verified_without_form_ids'
        elif is_verified and missing_ids:
            status = 'verified_forms_missing_from_catalog'
        elif is_verified:
            status = 'parsed_at_least_once'
        elif state is None:
            status = 'unknown_no_state'
        else:
            status = 'unverified'
        states[status] += 1
        family_rows.append({'family': u, 'status': status, 'catalogRecordCount': len(ids),
                            'recordIDs': ' '.join(sorted(actual, key=int)),
                            'verifiedFormIDs': ' '.join(sorted(known, key=int)),
                            'missingVerifiedFormIDs': ' '.join(missing_ids)})
        if missing_ids or status == 'verified_without_form_ids':
            form_discrepancies.append({'family': u, 'reason': status,
                                       'missingVerifiedFormIDs': ' '.join(missing_ids)})

    orphan_verified = sorted(verified_urls - set(families))
    bad_manifest_count = manifest.get('count') != len(records)
    summary = {
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'catalogGeneratedAt': manifest.get('generatedAt'),
        'stateAvailable': state is not None,
        'records': len(records), 'distinctIDs': len(by_id),
        'manifestCount': manifest.get('count'),
        'manifestCountMatches': not bad_manifest_count,
        'duplicateIDCount': len(duplicates), 'invalidRecordCount': len(bad_records),
        'chunkIssueCount': len(chunk_errors),
        'familiesWithRecords': len(families), 'familyStatuses': dict(states),
        'verifiedFamiliesWithoutRecords': len(orphan_verified),
        'formStateDiscrepancies': len(form_discrepancies),
        'totalListingPages': total_pages or None, 'listingPagesVisited': len(visited),
        'missingListingPages': [p for p in range(1, total_pages + 1) if p not in visited],
        'missingFieldCounts': dict(counts),
        'structuralIssuesFound': bool(duplicates or bad_records or chunk_errors or bad_manifest_count or
                                      orphan_verified or form_discrepancies),
        'allKnownFamiliesParsedAtLeastOnce': bool(families) and bool(state is not None) and all(
            u in verified_urls and bool(verified_forms.get(u)) for u in families),
        'allFormsProvenComplete': False,
        'notes': [
            'A listed family can contain forms not currently present in the catalog.',
            'Verified form IDs reflect previously parsed HTML, not independent proof of all on-site forms.',
            'Missing fields on representative listing entries are expected until profile extraction.',
            'This audit never fetches pages, validates image bytes, or changes existing data.'
        ]
    }
    if output is not None:
        out = Path(output)
        out.mkdir(parents=True, exist_ok=True)
        (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        csv_write(out / 'family-status.csv',
                  ['family', 'status', 'catalogRecordCount', 'recordIDs', 'verifiedFormIDs', 'missingVerifiedFormIDs'], family_rows)
        csv_write(out / 'missing-fields.csv', ['id', 'name', 'family', 'field'], missing_rows)
        csv_write(out / 'missing-listing-pages.csv', ['page'],
                  [{'page': p} for p in summary['missingListingPages']])
        csv_write(out / 'form-state-discrepancies.csv',
                  ['family', 'reason', 'missingVerifiedFormIDs'], form_discrepancies)
        csv_write(out / 'structural-issues.csv', ['kind', 'item'],
                  [{'kind': 'duplicate_id', 'item': x} for x in duplicates] +
                  [{'kind': 'invalid_record', 'item': str(x)} for x in bad_records] +
                  [{'kind': 'chunk_issue', 'item': str(x)} for x in chunk_errors] +
                  [{'kind': 'orphan_verified_family', 'item': x} for x in orphan_verified] +
                  ([{'kind': 'manifest_count_mismatch', 'item': str(manifest.get('count'))}]
                   if bad_manifest_count else []))
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalog', nargs='?', default='public/catalog')
    parser.add_argument('--state', default='catalog-update-state.json')
    parser.add_argument('--output', default='local-reports/phase19')
    parser.add_argument('--fail-on-structural-issues', action='store_true')
    args = parser.parse_args()
    summary = audit(args.catalog, args.state, args.output)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.fail_on_structural_issues and summary['structuralIssuesFound']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
