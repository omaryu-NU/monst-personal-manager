#!/usr/bin/env python3
"""Conservative opt-in image backfill: only a verified image response is published.

Default is read-only dry-run. No Firestore interaction, no image URL fabrication.
"""
from __future__ import annotations
import argparse, json, os, re, time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import requests

HOST = 'game.technophere.com'
PREFIX = 'https://game.technophere.com/monst/wp-content/uploads/monst-lab/icon/'
AGENT = 'MonstPersonalManagerCatalog/1.0 (authorized, noncommercial; contact: repository owner)'
MAX_RESPONSE = 64 * 1024


def load(path):
    with path.open(encoding='utf-8') as f:
        return json.load(f)


def atomic_json(path, value):
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')
    temp.replace(path)


def candidate_url(record):
    """Only propose a pattern, never claim an image exists."""
    s = str(record.get('id', ''))
    src = str(record.get('source', ''))
    if not s.isdecimal() or int(s) <= 0 or int(s)>999999:
        return None
    if record.get('image'):
        return None
    parsed = urlparse(src)
    if parsed.scheme != 'https' or parsed.hostname != HOST or not re.fullmatch(r'/monst/char/\d+/?', parsed.path):
        return None
    return PREFIX + str(int(s)) + '.webp'


def looks_webp(buf):
    return len(buf) >= 12 and buf[:4] == b'RIFF' and buf[8:12] == b'WEBP'


def probe(session, url):
    """Fetch at most MAX_RESPONSE bytes and verify actual WebP signature."""
    try:
        with session.get(url, timeout=(10, 20), stream=True, allow_redirects=False) as r:
            status = r.status_code
            if status == 429:
                return 'rate_limited', status
            if status != 200:
                return 'http_error', status
            ctype = r.headers.get('Content-Type', '').split(';')[0].strip().lower()
            if ctype != 'image/webp':
                return 'not_webp', status
            length = r.headers.get('Content-Length')
            if length and length.isdigit() and int(length)>2_000_000:
                return 'too_large', status
            buf=b''
            for chunk in r.iter_content(chunk_size=4096):
                buf += chunk
                if len(buf)>=12: break
                if len(buf)>MAX_RESPONSE: return 'too_large', status
            return ('verified' if looks_webp(buf) else 'invalid_signature'), status
    except requests.RequestException:
        return 'request_error', None


def audit(catalog, *, online_limit=5, delay=3.0, apply=False, state_file=None, session=None, robots=None, wait=time.sleep):
    if os.environ.get('TECHNOPHERE_REUSE_APPROVED') != 'true':
        raise RuntimeError('TECHNOPHERE_REUSE_APPROVED=true is required')
    if online_limit<1 or online_limit>20 or delay<1:
        raise ValueError('Use 1..20 requests/run and >=1 second delay')
    catalog=Path(catalog)
    manifest=load(catalog/'manifest.json')
    chunks=manifest.get('chunks', [])
    if not isinstance(chunks,list) or not chunks:
        raise ValueError('Missing manifest chunks')
    data={}
    entries=[]
    ids=set()
    for item in chunks:
        filename=item['path']
        if not re.fullmatch(r'characters-\d{4}\.json',filename):
            raise ValueError('Unexpected chunk name')
        doc=load(catalog/filename)
        records=doc['characters']
        if len(records)!=item['count']:
            raise ValueError(f'Chunk count mismatch: {filename}')
        data[filename]=doc
        for record in records:
            rid=str(record.get('id',''))
            if rid in ids: raise ValueError(f'Duplicate ID: {rid}')
            ids.add(rid)
            candidate=candidate_url(record)
            if candidate:entries.append((filename,record,candidate))
    if len(ids)!=manifest.get('count'):
        raise ValueError('Manifest count mismatch')
    state_file = Path(state_file) if state_file else catalog.parent.parent/'local-reports/image-backfill/state.json'
    if state_file.is_file():
        prior=load(state_file)
    else: prior={}
    # Phase12: stable ordering by numeric character ID, not by the shrinking
    # missing-image list. Phase11's index cursor skipped five following IDs
    # after five successful images disappeared from entries.
    entries.sort(key=lambda t:int(t[1]['id']))
    last_id=int(prior.get('lastProcessedID',0)) if str(prior.get('lastProcessedID',0)).isdigit() else 0
    retry=prior.get('retry',{}) if isinstance(prior.get('retry',{}),dict) else {}
    run=int(prior.get('runNumber',0))+1
    # One-time backwards compatibility with Phase11 cursor: the first 5 IDs
    # have already been added to JSON, so start at the lowest remaining ID.
    if 'lastProcessedID' not in prior:
        last_id=0
    # Wrap after reaching end of the present missing list. A failed ID is
    # delayed for later runs; successful IDs disappear from the candidate list.
    after=[e for e in entries if int(e[1]['id'])>last_id]
    before=[e for e in entries if int(e[1]['id'])<=last_id]
    pool=after+before
    subset=[]
    for entry in pool:
        rid=str(entry[1]['id'])
        until=retry.get(rid,{}).get('retryAfterRun',0) if isinstance(retry.get(rid),dict) else 0
        if run<int(until):continue
        subset.append(entry)
        if len(subset)>=online_limit:break
    s=session or requests.Session()
    s.headers.update({'User-Agent':AGENT, 'Accept':'image/webp'})
    rp=robots or RobotFileParser()
    if robots is None:
        rp.set_url('https://'+HOST+'/robots.txt')
        rp.read()
    verified=[]; events=[]; rate_limited=False; touched=set()
    processed=0
    last_attempted_id=last_id
    for filename,record,url in subset:
        if not rp.can_fetch(AGENT,url):
            events.append({'id':record['id'],'status':'robots_denied'})
            processed+=1
            last_attempted_id=int(record['id'])
            retry[str(record['id'])]={'failures':1,'retryAfterRun':run+32,'reason':'robots_denied'}
            continue
        outcome,status=probe(s,url)
        events.append({'id':record['id'],'status':outcome,'http_status':status})
        processed+=1
        if outcome!='rate_limited':
            last_attempted_id=int(record['id'])
        if outcome=='verified':
            retry.pop(str(record['id']),None)
            verified.append({'id':record['id'],'url':url})
            if apply:
                record['image']=url
                touched.add(filename)
        elif outcome!='rate_limited':
            old=retry.get(str(record['id']),{})
            failures=min(12,int(old.get('failures',0))+1)
            retry[str(record['id'])]={'failures':failures,'retryAfterRun':run+min(2**min(failures,5),32),'reason':outcome}
        if outcome=='rate_limited':
            rate_limited=True
            break
        wait(delay)
    # Persist only verified image URLs; never add a guessed URL to the public catalog.
    if apply:
        for filename in sorted(touched):
            atomic_json(catalog/filename,data[filename])
    report={'generatedAt':datetime.now(timezone.utc).isoformat(),'dryRun':not apply,
            'candidateRecords':len(entries),'attempted':processed,'verifiedCount':len(verified),
            'updatedRecords':len(verified) if apply else 0,
            'rateLimited':rate_limited,'results':events,'verified':verified,
            'stateSchema':2,'lastProcessedID':last_attempted_id,
            'delayedCandidates':sum(1 for e in entries if str(e[1]['id']) in retry and run<int(retry[str(e[1]['id'])].get('retryAfterRun',0))),
            'note':'A verified WebP file does not establish character identity. URL candidates are never stored without HTTP validation.'}
    if apply:
        state_file.parent.mkdir(parents=True,exist_ok=True)
        # Only successful applies advance the stable ID anchor; on a 429,
        # the throttled record remains available for the next execution.
        atomic_json(state_file,{'schema':2,'lastProcessedID':last_attempted_id,
                                'runNumber':run,'retry':retry,
                                'updatedAt':report['generatedAt']})
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('catalog',nargs='?',default='public/catalog')
    p.add_argument('--online-limit',type=int,default=5)
    p.add_argument('--delay',type=float,default=3.0)
    p.add_argument('--apply',action='store_true',help='Persist only HTTP-verified image URLs')
    p.add_argument('--output',default='local-reports/image-backfill/report.json')
    p.add_argument('--state-file',default='local-reports/image-backfill/state.json')
    args=p.parse_args()
    report=audit(args.catalog,online_limit=args.online_limit,delay=args.delay,apply=args.apply,state_file=args.state_file)
    dest=Path(args.output);dest.parent.mkdir(parents=True,exist_ok=True)
    atomic_json(dest,report)
    print(f"tested={report['attempted']} verified={report['verifiedCount']} saved={report['updatedRecords']} rate_limited={report['rateLimited']}")

if __name__=='__main__':main()
