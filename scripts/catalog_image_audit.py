#!/usr/bin/env python3
"""Read-only catalog image audit. Optional small, polite network sampling."""
from __future__ import annotations
import argparse, csv, json, re, time
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

HOST = 'game.technophere.com'
EXTS = {'.png', '.jpg', '.jpeg', '.webp'}


def load_catalog(folder):
    manifest = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    records=[]
    for ch in manifest['chunks']:
        f=folder / ch['path']
        obj=json.loads(f.read_text(encoding='utf-8'))
        assert len(obj['characters']) == ch['count'], f'Chunk count mismatch: {f}'
        records.extend(obj['characters'])
    assert len(records) == manifest['count'], 'Manifest count mismatch'
    return records


def image_issue(record):
    url = record.get('image', '')
    if not url:
        return 'missing_url'
    p=urlparse(url)
    if p.scheme != 'https' or p.hostname != HOST or p.username or p.password or p.port or not p.path.startswith('/monst/'):
        return 'untrusted_url'
    stem=Path(p.path).stem
    if Path(p.path).suffix.lower() not in EXTS:
        return 'unsupported_extension'
    if stem != str(record.get('id', '')):
        return 'id_filename_mismatch'
    return 'format_ok'


def audit(folder, output, online_limit=0, delay=2.0, session=None, robots=None):
    records=load_catalog(folder)
    results=[{'id':str(r.get('id','')), 'name':str(r.get('name','')), 'image':str(r.get('image','')),
              'status':image_issue(r), 'http_status':'', 'content_type':''} for r in records]
    inspected=0
    # Never send network traffic unless explicitly requested.
    if online_limit:
        import requests
        session=session or requests.Session()
        session.headers.update({'User-Agent':'MonstPersonalManagerImageAudit/1.0 (authorized, noncommercial)', 'Accept':'image/avif,image/webp,image/png,image/jpeg'})
        robots=robots or RobotFileParser()
        if not getattr(robots, '_monst_initialized', False):
            robots.set_url('https://'+HOST+'/robots.txt'); robots.read()
        for r in results:
            if inspected >= online_limit: break
            if r['status'] != 'format_ok': continue
            if not robots.can_fetch(session.headers['User-Agent'], r['image']):
                r['status']='robots_disallowed'; continue
            inspected+=1
            try:
                with session.get(r['image'], timeout=20, stream=True, allow_redirects=False) as response:
                    r['http_status']=str(response.status_code)
                    r['content_type']=response.headers.get('Content-Type','').split(';')[0].strip().lower()
                    if response.status_code == 429:
                        r['status']='rate_limited'; break
                    if response.status_code != 200:
                        r['status']='http_error'; continue
                    b=next(response.iter_content(chunk_size=64), b'')
                    magic=(b.startswith(b'\x89PNG\r\n\x1a\n') or b.startswith(b'\xff\xd8\xff') or (b[:4]==b'RIFF' and b[8:12]==b'WEBP'))
                    r['status']='image_ok' if r['content_type'].startswith('image/') and magic else 'not_image'
            except requests.RequestException:
                r['status']='request_error'
            finally:
                if delay: time.sleep(delay)
    output.mkdir(parents=True,exist_ok=True)
    with (output/'image-audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['id','name','image','status','http_status','content_type']); w.writeheader(); w.writerows(results)
    counts={k:sum(r['status']==k for r in results) for k in sorted({r['status'] for r in results})}
    summary={'records':len(results),'imageURLsPresent':sum(bool(r['image']) for r in results),
             'networkRequests':inspected,'statusCounts':counts,
             'caution':'format_ok checks URL structure only; image_ok confirms HTTP image signature, not character identity.'}
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('catalog',type=Path)
    p.add_argument('--output',type=Path,default=Path('local-reports/image-audit'))
    p.add_argument('--online-limit',type=int,default=0,help='Opt-in number of URLs to test (max 10)')
    p.add_argument('--delay',type=float,default=2.0)
    a=p.parse_args()
    if not 0<=a.online_limit<=10: p.error('--online-limit must be 0..10')
    if a.online_limit and a.delay<2: p.error('delay must be >=2s for online requests')
    print(json.dumps(audit(a.catalog,a.output,a.online_limit,a.delay),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
