#!/usr/bin/env python3
"""Phase22 offline per-form data quality reconciliation. No HTTP, no catalog mutation."""
import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

FIELDS = ('image', 'abilities', 'rarity', 'hp', 'attack', 'speed', 'ss', 'friendship', 'evolution', 'type', 'style', 'race')
CORE = ('abilities', 'rarity', 'hp', 'attack', 'speed', 'ss', 'friendship')


def load_catalog(folder):
    manifest_path = folder / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    by_id = {}
    duplicates = []
    for chunk in manifest.get('chunks', []):
        name = chunk.get('path', '')
        if not isinstance(name, str) or Path(name).name != name or not name.endswith('.json'):
            raise ValueError('Unsafe catalog chunk name')
        doc = json.loads((folder / name).read_text(encoding='utf-8'))
        for row in doc.get('characters', []):
            if not isinstance(row, dict):
                raise ValueError('Non-object character record')
            try:
                identifier = str(int(row['id']))
            except (KeyError, ValueError, TypeError):
                raise ValueError('Invalid character ID') from None
            if identifier in by_id:
                duplicates.append(identifier)
            by_id[identifier] = row
    return manifest, by_id, duplicates


def is_missing(value):
    if value is None or value == '':
        return True
    if isinstance(value, (list, dict)) and not value:
        return True
    return False


def valid_family(url):
    if not isinstance(url, str):
        return False
    parsed = urlparse(url.split('#')[0])
    return parsed.scheme == 'https' and parsed.netloc == 'game.technophere.com' and parsed.path.startswith('/monst/char/') and parsed.path.strip('/').split('/')[-1].isdigit()


def analyze(folder, state_file, output, baseline=None):
    manifest, rows, dupes = load_catalog(folder)
    state = json.loads(state_file.read_text(encoding='utf-8'))
    verified = set(u for u in state.get('verifiedFamilyURLs', []) if valid_family(u))
    form_state = {u: set(map(str, ids)) for u, ids in state.get('verifiedFamilyFormIDs', {}).items() if valid_family(u) and isinstance(ids, list)}
    families = defaultdict(list)
    for row in rows.values():
        source = row.get('source', '')
        if valid_family(source):
            families[source.split('#')[0]].append(row)
    details = []
    family_report = []
    counts = Counter()
    for family in sorted(families):
        family_rows = sorted(families[family], key=lambda r: int(r['id']))
        missing_core = 0
        for row in family_rows:
            missing = [field for field in FIELDS if is_missing(row.get(field))]
            status = 'previously_parsed_family' if family in verified else 'unverified_family'
            if any(x in missing for x in CORE):
                missing_core += 1
            for field in missing:
                counts[field] += 1
                counts[status + ':' + field] += 1
            details.append({'id': str(row['id']), 'family': family, 'status': status, 'missingFields': '|'.join(missing), 'missingCoreCount': sum(x in missing for x in CORE)})
        known_ids = {str(r['id']) for r in family_rows}
        expected_ids = form_state.get(family, set())
        family_report.append({'family': family, 'status': 'previously_parsed_family' if family in verified else 'unverified_family', 'knownForms': len(family_rows), 'missingCoreForms': missing_core, 'verifiedFormIDsMissingFromCatalog': '|'.join(sorted(expected_ids - known_ids, key=int))})
    count_by_status = Counter(f['status'] for f in family_report)
    report = {'catalogGeneratedAt': manifest.get('generatedAt'), 'records': len(rows), 'manifestCount': manifest.get('count'), 'duplicateIDs': dupes, 'familiesWithRecords': len(families), 'verifiedFamilies': count_by_status['previously_parsed_family'], 'unverifiedFamilies': count_by_status['unverified_family'], 'missingFieldCounts': {key: counts[key] for key in FIELDS}, 'missingCoreByStatus': {status: sum(r['missingCoreCount'] > 0 for r in details if r['status'] == status) for status in ('previously_parsed_family','unverified_family')}, 'stateVerifiedNotInCatalog': sorted(verified - set(families)), 'verifiedFormIDsMissingCount': sum(bool(f['verifiedFormIDsMissingFromCatalog']) for f in family_report), 'allFormsProvenComplete': False, 'caution': 'Missing data is not always a parsing failure: some forms may legitimately lack fields; parsed families are not proof of all on-site forms.'}
    if baseline:
        old = json.loads(baseline.read_text(encoding='utf-8'))
        previous = old.get('missingFieldCounts', {})
        report['baselineComparison'] = {'baselineRecords': old.get('records'), 'recordDelta': len(rows)-old['records'] if isinstance(old.get('records'), int) else None, 'missingFieldDelta': {k: counts[k]-previous[k] for k in FIELDS if isinstance(previous.get(k), int)}, 'note': 'Absolute missing-count changes are not quality changes when record totals differ.'}
    output.mkdir(parents=True, exist_ok=True)
    (output / 'summary.json').write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    for filename, data, keys in (
        ('form-quality.csv', details, ('id', 'family', 'status', 'missingFields', 'missingCoreCount')),
        ('family-quality.csv', family_report, ('family', 'status', 'knownForms', 'missingCoreForms', 'verifiedFormIDsMissingFromCatalog')),
    ):
        with (output / filename).open('w', encoding='utf-8-sig', newline='') as fp:
            writer = csv.DictWriter(fp, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('catalog', type=Path)
    parser.add_argument('--state', type=Path, default=Path('catalog-update-state.json'))
    parser.add_argument('--output', type=Path, default=Path('local-reports/phase22'))
    parser.add_argument('--baseline', type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(args.catalog, args.state, args.output, args.baseline), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
