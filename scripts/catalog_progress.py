#!/usr/bin/env python3
"""Catalog coverage from local output only. Never claims remote completeness."""
from __future__ import annotations
import argparse, json, sys
from collections import Counter
from pathlib import Path

def audit(folder: Path) -> dict:
    manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    rows=[]
    errors=[]
    for ch in manifest.get('chunks',[]):
        path=folder/ch['path']
        if not path.is_file():
            errors.append(f'missing chunk: {path.name}')
            continue
        chunk=json.loads(path.read_text(encoding='utf-8'))
        items=chunk.get('characters',[])
        if len(items)!=ch['count']:
            errors.append(f'count mismatch: {path.name}')
        rows.extend(items)
    ids=[str(row.get('id','')) for row in rows]
    counts=Counter(ids)
    duplicates=[k for k,v in counts.items() if v>1]
    if len(rows)!=manifest.get('count'):
        errors.append('manifest count differs from chunk count')
    if duplicates:
        errors.append(f'{len(duplicates)} duplicate IDs')
    coverage=manifest.get('coverage',{})
    total_pages=coverage.get('totalPages') or 0
    visited_pages=coverage.get('listingPagesVisited') or 0
    total_families=coverage.get('familiesDiscovered') or 0
    verified_families=coverage.get('familiesVerified') or 0
    def share(a,b):return round(a/b*100,2) if b else 0.0
    summary={'generatedAt':manifest.get('generatedAt'),
        'records':len(rows),'manifestCount':manifest.get('count'),
        'distinctIDs':len(counts),'duplicateIDs':duplicates[:50],
        'namePresent':sum(bool(str(r.get('name','')).strip()) for r in rows),
        'imageURLPresent':sum(bool(r.get('image')) for r in rows),
        'abilitiesPresent':sum(bool(r.get('abilities')) for r in rows),
        'detailFields':{k:sum(r.get(k) is not None and r.get(k)!='' for r in rows)
                        for k in ('evolution','type','style','race','rarity','hp','attack','speed','friendship','ss')},
        'coverage':coverage,
        'progress':{'listingVisitedPercent':share(visited_pages,total_pages),
                    'familyProfilesVerifiedPercent':share(verified_families,total_families),
                    'imagesPresentPercent':share(sum(bool(r.get('image')) for r in rows),len(rows)),
                    'abilitiesPresentPercent':share(sum(bool(r.get('abilities')) for r in rows),len(rows)),
                    'familyVerificationPending':max(0,total_families-verified_families)},
        'errors':errors,
        'allCharactersAndFormsVerified':False,
        'note':'Listing record counts and line coverage are not ground truth for all evolutions.'}
    return summary

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('catalog', nargs='?',default='public/catalog')
    ap.add_argument('--output',default='catalog-audit-summary.json')
    args=ap.parse_args()
    result=audit(Path(args.catalog))
    Path(args.output).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(bool(result['errors']))
