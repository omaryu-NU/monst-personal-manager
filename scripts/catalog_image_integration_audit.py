#!/usr/bin/env python3
"""Read-only Phase14 gate for image evidence, applied reports and catalog consistency."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

try:
    from catalog_image_evidence import catalog_records, checked_url, read, atomic
except ImportError:
    from scripts.catalog_image_evidence import catalog_records, checked_url, read, atomic


def audit(catalog_folder, evidence_path, report_paths=(), *, min_evidence=0):
    _, catalog = catalog_records(catalog_folder)
    evidence = read(evidence_path)
    if evidence.get('schema') != 1 or not isinstance(evidence.get('images'), dict):
        raise ValueError('Unsupported image evidence schema')
    images = evidence['images']
    invalid_evidence, absent_ids, conflicts, missing_images = [], [], [], []
    for rid, url in images.items():
        if not checked_url(rid, url):
            invalid_evidence.append(rid)
        elif rid not in catalog:
            absent_ids.append(rid)
        else:
            actual = catalog[rid][1].get('image')
            if not actual:
                missing_images.append(rid)
            elif actual != url:
                conflicts.append(rid)
    untracked_reports = []
    report_summaries = []
    for report_path in report_paths:
        report = read(report_path)
        if report.get('dryRun') is not False or not isinstance(report.get('verified'), list):
            raise ValueError('Applied image report required: ' + str(report_path))
        confirmed = {str(x.get('id')) for x in report.get('results', [])
                     if isinstance(x, dict) and x.get('status') == 'verified' and x.get('http_status') == 200}
        report_ids = []
        for item in report['verified']:
            if not isinstance(item, dict):
                raise ValueError('Invalid report verified entry')
            rid, url = str(item.get('id', '')), item.get('url')
            if rid not in confirmed or not checked_url(rid, url):
                raise ValueError('Unsubstantiated verified report entry: ' + str(rid))
            report_ids.append(rid)
            if images.get(rid) != url:
                untracked_reports.append({'report': str(report_path), 'id': rid})
        report_summaries.append({'path': str(report_path), 'verifiedIDs': sorted(set(report_ids), key=int)})
    failure = bool(invalid_evidence or absent_ids or conflicts or missing_images or untracked_reports or len(images) < min_evidence)
    return {
        'generatedAt': datetime.now(timezone.utc).isoformat(),
        'catalogRecords': len(catalog), 'evidenceCount': len(images),
        'minimumEvidence': min_evidence, 'imageURLsPresent': sum(bool(r[1].get('image')) for r in catalog.values()),
        'invalidEvidenceIDs': sorted(invalid_evidence), 'missingCatalogIDs': sorted(absent_ids),
        'conflictingIDs': sorted(conflicts), 'missingImageIDs': sorted(missing_images),
        'appliedReports': report_summaries, 'verifiedReportEntriesMissingFromEvidence': untracked_reports,
        'passed': not failure,
        'caution': 'Offline checks cannot prove that the image depicts the named character or is still served.'
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog', default='public/catalog')
    p.add_argument('--evidence', default='catalog-image-evidence.json')
    p.add_argument('--applied-report', action='append', default=[])
    p.add_argument('--min-evidence', type=int, default=0)
    p.add_argument('--output', default='local-reports/image-integration/report.json')
    p.add_argument('--strict', action='store_true')
    args = p.parse_args()
    if args.min_evidence < 0: p.error('--min-evidence must be nonnegative')
    result = audit(args.catalog, args.evidence, args.applied_report, min_evidence=args.min_evidence)
    atomic(Path(args.output), result)
    print(json.dumps(result, ensure_ascii=False))
    if args.strict and not result['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
