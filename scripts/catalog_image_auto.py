#!/usr/bin/env python3
"""Phase16: bounded HTTP-verified image backfill with tracked resumable state.

Only activated explicitly by the workflow. Verification is transport/filename,
NOT visual identity. Never accesses Firebase or Firestore.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
from datetime import datetime, timezone

from catalog_image_backfill import audit, atomic_json
from catalog_image_evidence import import_report, replay


def execute(catalog, evidence, state, output, *, limit=3, delay=4.0,
            audit_fn=audit, import_fn=import_report, replay_fn=replay):
    if os.environ.get('TECHNOPHERE_REUSE_APPROVED') != 'true':
        raise RuntimeError('TECHNOPHERE_REUSE_APPROVED=true required')
    if not 1 <= limit <= 3 or delay < 3:
        raise ValueError('phase16 allows 1..3 attempts and >=3 seconds delay')
    catalog, evidence, state, output = map(Path, (catalog,evidence,state,output))
    if not evidence.is_file():
        raise FileNotFoundError('Tracked catalog-image-evidence.json is required')
    # Restore known evidence BEFORE choosing new missing-image candidates.
    restored = replay_fn(catalog, evidence, apply=True)
    if restored.get('conflicts') or restored.get('missingCatalogIDs'):
        raise ValueError('Evidence replay unresolved conflicts / missing IDs')
    report = audit_fn(catalog, online_limit=limit, delay=delay, apply=True,
                      state_file=state)
    output.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(output, report)
    if report.get('rateLimited'):
        raise RuntimeError('HTTP 429: do not commit or deploy; review request frequency')
    if report.get('dryRun') is not False or report.get('attempted',limit+1) > limit:
        raise ValueError('Invalid bounded image-apply report')
    if report.get('updatedRecords') != report.get('verifiedCount'):
        raise ValueError('Image apply counts differ')
    # Import is fail-closed: a HTTP-verified URL must also be present in the
    # saved local catalog and cannot replace conflicting image evidence.
    imported = import_fn(catalog,evidence,output,apply=True)
    after = replay_fn(catalog,evidence,apply=False)
    if after.get('conflicts') or after.get('missingCatalogIDs') or after.get('toRestore'):
        raise ValueError('Evidence and catalog out of sync after import')
    return {'generatedAt':datetime.now(timezone.utc).isoformat(),
            'attempted':report['attempted'], 'verifiedCount':report['verifiedCount'],
            'updatedRecords':report['updatedRecords'],
            'evidenceCount':imported['totalEvidence'], 'newEvidence':imported['newEvidence'],
            'stateFile':str(state), 'replay':restored, 'imageIdentityVerified':False}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--catalog',default='public/catalog')
    p.add_argument('--evidence',default='catalog-image-evidence.json')
    p.add_argument('--state',default='catalog-image-backfill-state.json')
    p.add_argument('--output',default='local-reports/image-backfill/phase16-apply.json')
    p.add_argument('--summary',default='local-reports/image-backfill/phase16-summary.json')
    p.add_argument('--limit',type=int,default=3)
    p.add_argument('--delay',type=float,default=4.0)
    a=p.parse_args()
    result=execute(a.catalog,a.evidence,a.state,a.output,limit=a.limit,delay=a.delay)
    atomic_json(Path(a.summary),result)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__': main()
