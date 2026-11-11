#!/usr/bin/env python3
"""Offline validation of Monst catalog. Standard library only; read-only source.
Exit 1 only for structural corruption, never for incompleteness of upstream catalog.
"""
from __future__ import annotations
import argparse,csv,json,re,sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ATTRS={'火','水','木','光','闇'}
FIELDS=('image','abilities','evolution','type','style','race','rarity','hp','attack','speed','friendship','ss')

def check(catalog:Path,out:Path):
    errors=[];warnings=[];rows=[];seen_files=set(); expected_count=0
    try: manifest=json.loads((catalog/'manifest.json').read_text(encoding='utf-8'))
    except (OSError,ValueError) as e:
        manifest={};errors.append(f'manifest cannot be opened: {e}')
    for ch in manifest.get('chunks',[]):
        filename=ch.get('path','')
        if not re.fullmatch(r'characters-\d{4}\.json',filename) or filename in seen_files:
            errors.append(f'invalid or repeated chunk filename: {filename}');continue
        seen_files.add(filename)
        try:
            item=json.loads((catalog/filename).read_text(encoding='utf-8'))
            chunk=item['characters']
            if not isinstance(chunk,list): raise ValueError('characters is not a list')
        except (OSError,ValueError,KeyError,TypeError) as e:
            errors.append(f'bad chunk {filename}: {e}');continue
        if len(chunk)!=ch.get('count'):
            errors.append(f'chunk count mismatch {filename}: {len(chunk)} vs {ch.get("count")}')
        for r in chunk:
            if isinstance(r,dict):rows.append({**r,'_chunk':filename})
            else:errors.append(f'non-object record in {filename}')
        expected_count+=ch.get('count',0) if isinstance(ch.get('count'),int) else 0
    if len(rows)!=manifest.get('count') or len(rows)!=expected_count:
        errors.append(f'manifest count mismatch actual={len(rows)} count={manifest.get("count")} chunk_sum={expected_count}')
    found_chunks={p.name for p in catalog.glob('characters-*.json')}
    orphan_chunks=sorted(found_chunks-seen_files)
    if orphan_chunks:warnings.append(f'{len(orphan_chunks)} orphan chunks outside manifest')
    ids=[str(r.get('id','')) for r in rows]
    duplicate_ids=[x for x,c in Counter(ids).items() if c>1]
    if duplicate_ids:errors.append(f'duplicate IDs: {len(duplicate_ids)}')
    issues=[]; details=Counter(); image_domains=Counter()
    for r in rows:
        rid=str(r.get('id',''))
        def issue(code, severity='warning', note=''):
            details[code]+=1
            issues.append({'id':rid,'name':str(r.get('name','')),'issue':code,'severity':severity,'chunk':r['_chunk'],'note':note})
        if not rid.isdecimal() or int(rid)<1:issue('invalid_id','error')
        if not isinstance(r.get('name'),str) or not r['name'].strip():issue('missing_name','error')
        if r.get('attribute') not in ATTRS:issue('invalid_attribute','error')
        if not r.get('image'):issue('missing_image')
        else:
            url=str(r['image']);p=urlparse(url)
            image_domains[p.netloc]+=1
            if p.scheme!='https' or not p.netloc:issue('invalid_image_url','error',url[:120])
        if not r.get('abilities'):issue('empty_abilities')
        elif not isinstance(r['abilities'],list):issue('invalid_abilities','error')
        for k in ('evolution','type','style','race','rarity','hp','attack','speed','friendship','ss'):
            if r.get(k) is None or r.get(k)=='':issue(f'missing_{k}')
        source=str(r.get('source',''))
        if not source:issue('missing_source')
        else:
            p=urlparse(source)
            if p.scheme!='https' or p.netloc!='game.technophere.com' or not p.path.startswith('/monst/char/'):
                issue('invalid_source_url','error',source[:120])
            if p.fragment.startswith('f') and p.fragment[1:].isdigit() and p.fragment[1:]!=rid:
                issue('source_fragment_mismatch','warning',source[:120])
    for i in issues:
        if i['severity']=='error':errors.append(f"record {i['id']} {i['issue']}")
    coverage=manifest.get('coverage',{})
    total=coverage.get('totalPages')
    visited=coverage.get('visitedPages')
    if isinstance(total,int) and total>0 and isinstance(visited,list):
        missing_pages=[i for i in range(1,total+1) if i not in visited]
    else:missing_pages=None
    def pct(n):return round(n/len(rows)*100,2) if rows else 0
    summary={'generatedAt':manifest.get('generatedAt'),'records':len(rows),'expected':manifest.get('count'),
             'duplicateIDs':duplicate_ids,'structuralOK':not errors,'structuralErrors':errors[:200],
             'warnings':warnings,'missingCounts':dict(details),'imagesPresent':len(rows)-details['missing_image'],
             'imagesPresentPercent':pct(len(rows)-details['missing_image']),
             'abilitiesPresent':len(rows)-details['empty_abilities'],
             'abilitiesPresentPercent':pct(len(rows)-details['empty_abilities']),
             'imageDomains':dict(image_domains),'coverage':coverage,
             'listingPagesMissing':missing_pages,
             'completionVerified':False,
             'limitations':['URL existence not checked (offline)',
                            'Character names not compared with ground truth',
                            'All forms not proven by visited listing pages']}
    out.mkdir(parents=True,exist_ok=True)
    (out/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (out/'issues.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=['id','name','issue','severity','chunk','note']);writer.writeheader();writer.writerows(issues)
    print(json.dumps({'records':len(rows),'structuralOK':not errors,'imagesPresent':summary['imagesPresent'],
                     'abilitiesPresent':summary['abilitiesPresent'],'missingPages':len(missing_pages) if missing_pages is not None else None},ensure_ascii=False))
    return summary

def main():
    p=argparse.ArgumentParser();p.add_argument('catalog',nargs='?',default='public/catalog');p.add_argument('--output',default='catalog-integrity-report')
    args=p.parse_args();r=check(Path(args.catalog),Path(args.output));return 0 if r['structuralOK'] else 1
if __name__=='__main__':sys.exit(main())
