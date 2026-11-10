#!/usr/bin/env python3
"""Independent Technophere catalog updater: conservative, resumable, never deletes records.
Explicit authorization required (TECHNOPHERE_REUSE_APPROVED=true); no login/circumvention.
"""
from __future__ import annotations
import argparse, json, os, re, sys, time
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

BASE='https://game.technophere.com'
INDEX=BASE+'/monst/characters/'
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'public/catalog'
STATE=ROOT/'catalog-update-state.json'
USER_AGENT='MonstPersonalManagerCatalog/1.0 (authorized, noncommercial; contact: repository owner)'
ELEMENTS=set('火水木光闇')
NO=re.compile(r'No[.．]\s*(\d{1,6})')
FORM=re.compile(r'\s(?:真獣神化|獣神化・改|獣神化改|獣神化|神化|進化|進化前|獣神化前|未進化)\s')
CHAR_URL=re.compile(r'^/monst/char/\d+/?$')


def safe_url(url):
    p=urlparse(url)
    return p.scheme=='https' and p.netloc=='game.technophere.com' and p.path.startswith('/monst/')

def atomic(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(path)

def read(path, default):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError): return default

def parse_listing(html, base=INDEX):
    soup=BeautifulSoup(html,'html.parser')
    page_count=None
    m=re.search(r'(\d+)\s*/\s*(\d+)\s*ページ',soup.get_text(' ',strip=True))
    if m: page_count=int(m.group(2))
    result={}
    for link in soup.select('a[href]'):
        u=urljoin(base,link.get('href',''))
        if not safe_url(u) or not CHAR_URL.match(urlparse(u).path):continue
        text=' '.join(link.stripped_strings)
        match=NO.search(text)
        if not match:continue
        no=int(match.group(1))
        prefix=text[:match.start()].strip()
        form=FORM.search(prefix)
        if not form:continue
        name=prefix[:form.start()].strip()
        # The listing uses a one-character avatar fallback before the name.
        if re.match(r'^\S\s+\S',name):name=name.split(' ',1)[1].strip()
        after=prefix[form.end():].strip()
        elem=after[0] if after[:1] in ELEMENTS else ''
        if not name or len(name)>120 or not elem:continue
        result[str(no)]={'id':str(no),'name':name,'attribute':elem,'source':u}
    return result,page_count

def parse_profile(html, page_url):
    soup=BeautifulSoup(html,'html.parser')
    headline=soup.find('h1')
    title=headline.get_text(' ',strip=True) if headline else ''
    m=re.search(r'^[【〖]モンスト[】〗]\s*(.+?)(?:[（(]|の性能|の評価)',title)
    if not m:return None
    name=m.group(1).strip()
    lines=[x.strip() for x in soup.get_text('\n',strip=True).splitlines() if x.strip()]
    near=' '.join(lines[:100]); match=re.search(r'([火水木光闇])\s*(?:真獣神化|獣神化・改|獣神化|進化|神化).*?No[.．]\s*(\d{1,6})',near)
    if not match:return None
    attr,no=match.group(1),int(match.group(2))
    def field(label):
        for i,s in enumerate(lines[:160]):
            if s==label and i+1<len(lines):return lines[i+1][:160]
        return ''
    acq=field('入手方法')
    # Image links must be validated as a concrete asset, not fabricated by ID.
    icon=''
    for img in soup.find_all('img'):
        if 'アイコン' not in (img.get('alt') or ''):continue
        url=urljoin(page_url,img.get('data-src') or img.get('src') or '')
        if safe_url(url) and urlparse(url).path.lower().endswith(('.webp','.png','.jpg','.jpeg')):
            icon=url;break
    return {'id':str(no),'name':name,'attribute':attr,'source':page_url,
            **({'acquisition':acq} if acq else {}), **({'image':icon} if icon else {})}

def normalize_old(record):
    if not isinstance(record,dict):return None
    # Keep only safe, additive fields from the previous run.
    try:
        id=str(int(record['id'])); name=str(record['name']).strip(); attr=record['attribute']
        if not name or attr not in ELEMENTS: return None
        item={'id':id,'name':name,'attribute':attr}
        for k in ('source','image','acquisition'):
            v=record.get(k)
            if isinstance(v,str) and v and (k=='acquisition' or safe_url(v)):item[k]=v
        return item
    except (TypeError,ValueError,KeyError):return None

def reconcile(old,new,verified=False):
    if old is None: return dict(new)
    result=dict(old)
    # Preserve existing data if the current page has partial or missing fields.
    for key in ('name','attribute','source'):
        if new.get(key) and (not result.get(key) or verified):result[key]=new[key]
    for key in ('image','acquisition'):
        if new.get(key) and (not result.get(key) or verified):result[key]=new[key]
    return result

def make_outputs(rows,stamp,source_pages,warnings):
    # Exclude internal-only fields from public catalog.
    items=[{'id':r['id'],'name':r['name'],'attribute':r['attribute'],
            'abilities':[], **({'image':r['image']} if r.get('image') else {}),
            **({'source':r['source']} if r.get('source') else {})}
           for r in sorted(rows.values(),key=lambda x:int(x['id']))]
    chunks=[]
    for i in range(0,len(items),200):
        filename=f'characters-{i//200+1:04d}.json'
        chunks.append({'path':filename,'count':len(items[i:i+200])})
        atomic(OUT/filename,{'version':1,'characters':items[i:i+200]})
    manifest={'schema':1,'generatedAt':stamp,'source':INDEX,'count':len(items),'chunks':chunks,
              'scan':{'pages':source_pages,'warnings':warnings[:30]}}
    atomic(OUT/'manifest.json',manifest)
    return manifest

def update(args, session, check_robots=True, wait=time.sleep):
    if os.getenv('TECHNOPHERE_REUSE_APPROVED')!='true':
        raise RuntimeError('Technophereの再利用・定期収集許可を確認し、TECHNOPHERE_REUSE_APPROVED=true を設定してください')
    old_manifest=read(OUT/'manifest.json',{})
    previous={}
    for chunk in old_manifest.get('chunks',[]):
        for raw in read(OUT/chunk['path'],{}).get('characters',[]):
            r=normalize_old(raw)
            if r:previous[r['id']]=r
    rows=dict(previous)
    state=read(STATE,{'nextPage':2,'totalPages':50})
    total=max(1,int(state.get('totalPages',50)))
    cursor=max(2,int(state.get('nextPage',2)))
    pages=[1]+[((cursor-2+i)%max(total-1,1))+2 for i in range(args.pages-1)]
    robots=RobotFileParser()
    if check_robots:
        robots.set_url(BASE+'/robots.txt');robots.read()
    scanned=[]; warnings=[]; profile_candidates=[]
    for page in pages:
        url=INDEX if page==1 else INDEX+f'page/{page}/'
        if check_robots and not robots.can_fetch(USER_AGENT,url):
            warnings.append(f'robots.txt denies page {page}');continue
        try:
            r=session.get(url,timeout=25);r.raise_for_status()
            if len(r.content)>4_000_000:raise ValueError('response too large')
            found,pg=parse_listing(r.text,url)
            if not found:raise ValueError('0 recognizable cards; refusing update of this page')
            scanned.append(page)
            if pg and 1<=pg<=500:total=pg
            for key,entry in found.items():
                existed=key in rows
                rows[key]=reconcile(rows.get(key),entry)
                if not existed or not rows[key].get('image') or not rows[key].get('acquisition'):
                    profile_candidates.append((not existed,int(key),entry['source']))
        except (requests.RequestException,ValueError) as e:warnings.append(f'page {page}: {str(e)[:110]}')
        wait(args.delay)
    seen=set(); candidates=[]
    for is_new,no,url in sorted(profile_candidates,key=lambda x:(not x[0],-x[1])):
        if no not in seen:seen.add(no);candidates.append((no,url))
    if not scanned:
        raise RuntimeError('No pages fetched; existing output was not touched: '+str(warnings[:3]))
    verified=0
    for no,url in candidates[:args.profiles]:
        if check_robots and not robots.can_fetch(USER_AGENT,url):continue
        try:
            r=session.get(url,timeout=25);r.raise_for_status()
            if len(r.content)>4_000_000:raise ValueError('profile too large')
            item=parse_profile(r.text,url)
            if item and int(item['id'])==no:
                rows[str(no)]=reconcile(rows.get(str(no)),item,verified=True)
                verified+=1
        except (requests.RequestException,ValueError) as e:warnings.append(f'profile {no}: {str(e)[:90]}')
        wait(args.delay)
    stamp=datetime.now(timezone.utc).isoformat()
    # Guard against catastrophic shrink (also no deletion at all).
    assert len(rows)>=len(previous)
    manifest=make_outputs(rows,stamp,scanned,warnings)
    next_page=((cursor-2+max(args.pages-1,0))%max(total-1,1))+2
    atomic(STATE,{'nextPage':next_page,'totalPages':total,'lastRun':stamp})
    print(f'pages={scanned} profile_verified={verified} records={manifest["count"]} nextPage={next_page} warnings={len(warnings)}')
    return manifest

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--pages',type=int,default=5)
    p.add_argument('--profiles',type=int,default=15)
    p.add_argument('--delay',type=float,default=1.5)
    args=p.parse_args()
    if not 2<=args.pages<=12 or not 0<=args.profiles<=60 or args.delay<0.5:p.error('limits exceeded')
    s=requests.Session();s.headers.update({'User-Agent':USER_AGENT,'Accept-Language':'ja,en;q=0.8'})
    return update(args,s)
if __name__=='__main__':main()
