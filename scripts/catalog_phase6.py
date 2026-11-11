#!/usr/bin/env python3
"""Read-only catalog coverage reconciliation. Does not fetch websites or modify source files."""
import argparse,csv,json,re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

PAT=re.compile(r'^/monst/char/\d+/?$')
FIELDS=['image','abilities','evolution','type','style','race','rarity','hp','attack','speed','ss','friendship']

def load(p, fallback):
    if not p.exists(): return fallback
    return json.loads(p.read_text(encoding='utf-8'))

def family(url):
    if not isinstance(url,str):return None
    u=urlparse(url)
    if u.scheme!='https' or u.netloc!='game.technophere.com' or not PAT.fullmatch(u.path):return None
    return f'https://{u.netloc}{u.path.rstrip("/")}/'

def writecsv(p,headers,rows):
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=headers,extrasaction='ignore');w.writeheader();w.writerows(rows)

def audit(catalog,state_path,out):
    manifest=load(catalog/'manifest.json',None)
    if not isinstance(manifest,dict):raise ValueError('manifest.json is missing or invalid')
    records=[]
    for chunk in manifest.get('chunks',[]):
        name=chunk['path']
        if not re.fullmatch(r'characters-\d{4}\.json',name):raise ValueError(f'Unsafe chunk name: {name}')
        obj=load(catalog/name,None)
        if obj is None:raise ValueError(f'Missing chunk: {name}')
        rows=obj.get('characters')
        if not isinstance(rows,list) or len(rows)!=chunk.get('count'):raise ValueError(f'Chunk count mismatch: {name}')
        records.extend(rows)
    ids=[str(x.get('id','')) for x in records]
    if manifest.get('count')!=len(records) or len(set(ids))!=len(ids):raise ValueError('Manifest mismatch or duplicate ID')
    state=load(state_path,{})
    coverage=manifest.get('coverage') or {}
    total=coverage.get('totalPages',state.get('totalPages'))
    visited_raw=coverage.get('visitedPages',state.get('visitedPages',[]))
    complete_coverage=isinstance(total,int) and 1<=total<=500 and isinstance(visited_raw,list)
    visited={int(x) for x in visited_raw if str(x).isdigit() and complete_coverage and 1<=int(x)<=total}
    missing=[i for i in range(1,total+1) if i not in visited] if complete_coverage else None
    by_family={};invalid=[]
    for r in records:
        key=family(r.get('source'))
        if not key:invalid.append({'id':r.get('id'),'name':r.get('name'),'source':r.get('source','')});continue
        by_family.setdefault(key,[]).append(r)
    raw_verified=state.get('verifiedFamilyURLs',[])
    verified={u for x in raw_verified if (u:=family(x))}
    forms_state=state.get('verifiedFamilyFormIDs',{})
    expected_by_family={}
    for url,form_ids in forms_state.items():
        u=family(url)
        if u and isinstance(form_ids,list):expected_by_family[u]={str(x) for x in form_ids}
    # The state is evidence only for families with a tracked list of extracted IDs.
    report=[]
    for u,rs in sorted(by_family.items()):
        record_ids={str(x.get('id')) for x in rs}
        state_ids=expected_by_family.get(u,set())
        if not state_path.exists():status='verification_unknown_no_state'
        elif u not in verified: status='unverified'
        elif not state_ids:status='verified_without_form_ids'
        elif not state_ids.issubset(record_ids):status='verified_forms_missing_in_catalog'
        else:status='parsed_at_least_once'
        report.append({'family_url':u,'records':len(rs),'status':status,
                       'catalog_ids':' '.join(sorted(record_ids,key=lambda x:int(x) if x.isdigit() else 0)),
                       'tracked_form_ids':' '.join(sorted(state_ids,key=lambda x:int(x) if x.isdigit() else 0))})
    missing_fields=[]; counts=Counter()
    for r in records:
        missing_keys=[k for k in FIELDS if r.get(k) is None or r.get(k)=='' or r.get(k)==[]]
        counts.update(missing_keys)
        if missing_keys:missing_fields.append({'id':r.get('id'),'name':r.get('name'),'missing_fields':';'.join(missing_keys),'source':r.get('source','')})
    state_known=bool(state_path.exists())
    statuses=Counter(x['status'] for x in report)
    summary={
      'records':len(records),'familiesWithRecords':len(by_family),
      'listingPagesTotal':total if complete_coverage else None,
      'listingPagesVisited':len(visited) if complete_coverage else None,
      'listingPagesMissing':missing,
      'stateAvailable':state_known,
      'familyStatuses':dict(statuses),
      'invalidSourceCount':len(invalid),
      'missingFieldCounts':dict(counts),
      'imagesPresent':len(records)-counts['image'],
      'abilitiesPresent':len(records)-counts['abilities'],
      'allListingPagesVisited':missing==[] if missing is not None else False,
      'allKnownFamiliesParsedAtLeastOnce':state_known and bool(report) and all(x['status']=='parsed_at_least_once' for x in report),
      'allFormsProvenComplete':False,
      'explanation':'A family parsed at least once does not establish that every evolution form exists on the site and was captured. External reference and HTTP image checks are required.'}
    out.mkdir(parents=True,exist_ok=True)
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    writecsv(out/'missing-listing-pages.csv',['page'],[{'page':x} for x in (missing or [])])
    writecsv(out/'family-verification.csv',['family_url','records','status','catalog_ids','tracked_form_ids'],report)
    writecsv(out/'missing-fields.csv',['id','name','missing_fields','source'],missing_fields)
    writecsv(out/'invalid-sources.csv',['id','name','source'],invalid)
    print(f"records={len(records)} missing_pages={len(missing) if missing is not None else 'unknown'} unverified_families={statuses['unverified']} images={summary['imagesPresent']} abilities={summary['abilitiesPresent']}")
    return summary

def main():
    ap=argparse.ArgumentParser();ap.add_argument('catalog',type=Path);ap.add_argument('--state',type=Path,default=Path('catalog-update-state.json'));ap.add_argument('--output',type=Path,default=Path('local-reports/phase6'))
    args=ap.parse_args();audit(args.catalog,args.state,args.output)
if __name__=='__main__':main()
