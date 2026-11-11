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
        detail=after[1:].strip()
        # Listing cards expose only a representative form, never the full family.
        # Parse defensively: no inferred values from IDs or neighboring cards.
        traits=re.search(r'(反射|貫通)・([^・]+)・([^・]+)・?', detail)
        item={'id':str(no),'name':name,'attribute':elem,'source':u,
              'evolution':form.group(0).strip()}
        if traits:
            item.update(type=traits.group(1),style=traits.group(2),race=traits.group(3))
        result[str(no)]=item
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
        for url in _image_candidates(img,page_url):
            if Path(urlparse(url).path).stem==str(no) and '/icon/' in urlparse(url).path.lower():
                icon=url;break
        if icon:break
    return {'id':str(no),'name':name,'attribute':attr,'source':page_url,
            **({'acquisition':acq} if acq else {}), **({'image':icon} if icon else {})}

def _clean(value):
    return ' '.join(value.split()).strip()


def _stats_number(value):
    value=value.replace(',', '').strip()
    match=re.search(r'\d+(?:\.\d+)?', value)
    if not match:return None
    return float(match.group(0)) if '.' in match.group(0) else int(match.group(0))


def _split_abilities(cell):
    # Anchor boundaries are reliable. For plain concatenated text, do not invent splits.
    anchors=[_clean(a.get_text(' ',strip=True)) for a in cell.find_all('a')]
    anchors=[a for a in anchors if a]
    text=_clean(cell.get_text(' ',strip=True))
    if not text:return []
    if anchors:
        # Keep any unlinked suffix (e.g. killer abilities) instead of losing it.
        rest=text
        for a in anchors:rest=rest.replace(a,' ',1)
        suffix=_clean(rest)
        return list(dict.fromkeys(anchors + ([suffix] if suffix else [])))
    return [text]



def _image_candidates(tag, page_url):
    """Only real image URLs appearing in markup; no fabricated No. -> URL paths."""
    raw=[]
    for key in ('data-src','data-lazy-src','data-original','src'):
        v=tag.get(key)
        if v: raw.append(v)
    for key in ('data-srcset','srcset'):
        value=tag.get(key) or ''
        raw.extend(x.strip().split()[0] for x in value.split(',') if x.strip())
    for value in raw:
        url=urljoin(page_url,value)
        path=urlparse(url).path.lower()
        if safe_url(url) and path.endswith(('.webp','.png','.jpg','.jpeg')):
            yield url


def _form_icon(block, page_url, form_no):
    """Avoid unrelated images: prefer an explicit icon path ending in the form No."""
    numbered=[]
    for img in block.find_all('img'):
        alt=_clean(img.get('alt') or '')
        for url in _image_candidates(img,page_url):
            path=urlparse(url).path
            # Exact numeric stem, never a substring (954 vs 1954).
            stem=Path(path).stem
            if stem==str(form_no):
                numbered.append(url)
    if numbered:return numbered[0]
    # Do not guess which image belongs to this form if no No.-matched asset.
    return ''


def _field_label(text):
    return _clean(text).replace(' ', '').replace('：', '').replace(':','')


def _stat_column_keys(table):
    """Use explicit per-table headings where available; no assumed order then."""
    for tr in table.find_all('tr'):
        cells=tr.find_all(['th', 'td'], recursive=False)
        if len(cells)<4:
            continue
        labels=[_field_label(c.get_text(' ',strip=True)).lower() for c in cells[1:]]
        mapping=[]
        for label in labels:
            if label in ('hp','ＨＰ','ｈｐ'):
                mapping.append('hp')
            elif label in ('攻撃力','攻撃'):
                mapping.append('attack')
            elif label in ('スピード','速度'):
                mapping.append('speed')
            else:
                mapping.append(None)
        if set(k for k in mapping if k) == {'hp','attack','speed'} and len(set(mapping)) == len(mapping):
            return mapping
        if any(k is not None for k in mapping):
            # If a column header is recognized but ambiguous, avoid guessing.
            return []
    return None


def _parse_stats_table(block, item):
    """Parse only labeled form-local cells. Prefer Lv極 over Lv120 regardless of DOM order."""
    stats_by_level={}
    for table in block.find_all('table'):
        keys=_stat_column_keys(table)
        for tr in table.find_all('tr'):
            cells=tr.find_all(['th','td'],recursive=False)
            if not cells:
                continue
            label=_field_label(cells[0].get_text(' ',strip=True))
            if label in ('Lv極','Lv120','レベル極'):
                if keys == [] or len(cells)<4:
                    continue
                columns=keys if keys is not None else ['hp','attack','speed']
                if len(columns)>len(cells)-1:
                    continue
                values={}
                for key, cell in zip(columns,cells[1:]):
                    if key is None:
                        continue
                    raw=_clean(cell.get_text(' ',strip=True))
                    # Parse a strictly numeric cell; never take part of a label or formula.
                    if not re.fullmatch(r'\d[\d,]*(?:\.\d+)?',raw):
                        continue
                    num=_stats_number(raw)
                    if num is not None:
                        values[key]=num
                if values:
                    level='Lv極' if label in ('Lv極','レベル極') else 'Lv120'
                    stats_by_level.setdefault(level,{}).update(values)
                continue
            if len(cells)<2:
                continue
            val=_clean(' '.join(c.get_text(' ',strip=True) for c in cells[1:]))
            if label in ('アビリティ','アビリティー','ゲージショット','ゲージ','ゲージアビリティ','コネクトスキル','コネクト'):
                name= ('abilities' if label in ('アビリティ','アビリティー') else
                       'gaugeAbilities' if label in ('ゲージショット','ゲージ','ゲージアビリティ') else
                       'connectAbilities')
                abilities=[]
                for cell in cells[1:]:
                    abilities.extend(_split_abilities(cell))
                abilities=list(dict.fromkeys(abilities))
                if abilities:
                    item[name]=list(dict.fromkeys(item.get(name,[])+abilities))
            elif label in ('ストライクショット','SS') and val:
                item['ss']=val
            elif label in ('友情コンボ','友情') and val:
                item['friendship']=val
    # Lv極 is used as the single published level; Lv120 only fills missing cells.
    for key in ('hp','attack','speed'):
        value=stats_by_level.get('Lv極',{}).get(key)
        if value is None:
            value=stats_by_level.get('Lv120',{}).get(key)
        if value is not None:
            item[key]=value


def parse_family(html,page_url):
    """Extract only forms explicitly shown under the profile's forms section.

    Never infer missing IDs or icon paths. A family can yield zero rows if the
    upstream HTML structure differs. In that case the existing catalog is kept.
    """
    soup=BeautifulSoup(html,'html.parser')
    h2=next((h for h in soup.find_all('h2') if '形態ごとのステータスとアビリティ' in h.get_text(' ',strip=True)),None)
    if not h2:return []
    result={}
    for element in h2.next_elements:
        if getattr(element,'name',None)=='h2':break
        if getattr(element,'name',None)!='h3':continue
        heading=_clean(element.get_text(' ',strip=True))
        head=re.match(r'^(進化前|真獣神化前|獣神化・改|獣神化改|真獣神化|獣神化|神化|進化|未進化)\s*[：:]\s*(.+)$',heading)
        if not head:continue
        evolution,full_name=head.group(1),head.group(2)
        nodes=[]
        for sibling in element.next_siblings:
            if getattr(sibling,'name',None) in ('h2','h3'):break
            nodes.append(sibling)
        block=BeautifulSoup(''.join(str(x) for x in nodes),'html.parser')
        content=_clean(block.get_text(' ',strip=True))
        match=re.search(r'No[.．]\s*(\d{1,6})\s*([火水木光闇])',content)
        if not match:continue
        no,attr=match.group(1),match.group(2)
        item={'id':str(int(no)),'name':full_name,'fullName':full_name,'attribute':attr,'evolution':evolution,'source':page_url}
        # These metadata fields are copied only if explicitly present.
        meta=content[match.end():match.end()+90]
        m=re.search(r'(亜人|魔人|神|妖精|魔族|獣|幻獣|ドラゴン|ロボット|サムライ|ユニバース|コスモ|聖騎士|鳥|鉱物|魔王|幻妖|ユニバース族)',meta)
        if m:item['race']=m.group(1)
        m=re.search(r'(反射|貫通)',meta)
        if m:item['type']=m.group(1)
        m=re.search(r'(超バランス|超砲撃|超パワー|超スピード|バランス|砲撃|パワー|スピード)',meta)
        if m:item['style']=m.group(1)
        m=re.search(r'★\s*(\d)',meta)
        if m:item['rarity']=int(m.group(1))
        icon=_form_icon(block,page_url,no)
        if icon:item['image']=icon
        # Stats use Lv極/Lv120, not タス最大値, and data comes from this form only.
        _parse_stats_table(block,item)
        result[item['id']]=item
    return list(result.values())



def audit_profile_forms(html, extracted):
    """Return local structural evidence, NOT proof of global form completeness.

    Check that every *recognized* form heading in the target section yielded an
    extracted unique form. If the DOM changes or a heading lacks its No., leave
    the family eligible for a later retry instead of sealing it as verified.
    """
    soup=BeautifulSoup(html,'html.parser')
    h2=next((h for h in soup.find_all('h2') if '形態ごとのステータスとアビリティ' in h.get_text(' ',strip=True)),None)
    if not h2:
        return {'headings':0,'parsed':len(extracted),'incomplete':True,'reason':'section_missing'}
    recognized=[]
    for element in h2.next_elements:
        if getattr(element,'name',None)=='h2':break
        if getattr(element,'name',None)!='h3':continue
        heading=_clean(element.get_text(' ',strip=True))
        if re.match(r'^(進化前|真獣神化前|獣神化・改|獣神化改|真獣神化|獣神化|神化|進化|未進化)\s*[：:]',heading):
            recognized.append(heading)
    parsed_ids=[str(r['id']) for r in extracted]
    complete=bool(recognized) and len(recognized)==len(parsed_ids)==len(set(parsed_ids))
    return {'headings':len(recognized),'parsed':len(parsed_ids),
            'incomplete':not complete,
            'reason':('ok' if complete else 'heading_form_mismatch')}


def normalize_old(record):
    if not isinstance(record,dict):return None
    # Keep only safe, additive fields from the previous run.
    try:
        id=str(int(record['id'])); name=str(record['name']).strip(); attr=record['attribute']
        if not name or attr not in ELEMENTS: return None
        item={'id':id,'name':name,'attribute':attr}
        for k in ('source','image','acquisition','evolution','type','style','race','friendship','ss','fullName','fullName'):
            v=record.get(k)
            if isinstance(v,str) and v and (k not in ('source','image') or safe_url(v)):item[k]=v
        for k in ('rarity','hp','attack','speed'):
            v=record.get(k)
            if isinstance(v,(int,float)) and not isinstance(v,bool) and 0<=v<1e9:item[k]=v
        for k in ('abilities','gaugeAbilities','connectAbilities'):
            v=record.get(k)
            if isinstance(v,list) and all(isinstance(x,str) and x for x in v):item[k]=v
        return item
    except (TypeError,ValueError,KeyError):return None

def reconcile(old,new,verified=False):
    if old is None: return dict(new)
    result=dict(old)
    # Preserve existing data if the current page has partial or missing fields.
    for key in ('name','attribute','source','evolution','type','style','race'):
        if new.get(key) and (not result.get(key) or verified):result[key]=new[key]
    for key in ('image','acquisition','friendship','ss','fullName','acquisition','rarity','hp','attack','speed','abilities','gaugeAbilities','connectAbilities'):
        if new.get(key) and (not result.get(key) or verified):result[key]=new[key]
    return result

def make_outputs(rows,stamp,source_pages,warnings,coverage=None):
    # Exclude internal-only fields from public catalog.
    items=[{'id':r['id'],'name':r['name'],'attribute':r['attribute'],
            'abilities':r.get('abilities',[]),
            **{k:r[k] for k in ('image','source','evolution','type','style','race','friendship','ss','rarity','hp','attack','speed','gaugeAbilities','connectAbilities') if r.get(k) is not None and r.get(k)!=''} }
           for r in sorted(rows.values(),key=lambda x:int(x['id']))]
    chunks=[]
    for i in range(0,len(items),200):
        filename=f'characters-{i//200+1:04d}.json'
        chunks.append({'path':filename,'count':len(items[i:i+200])})
        atomic(OUT/filename,{'version':1,'characters':items[i:i+200]})
    manifest={'schema':1,'generatedAt':stamp,'source':INDEX,'count':len(items),'chunks':chunks,
              'scan':{'pages':source_pages,'warnings':warnings[:30]}, 'coverage':coverage or {}}
    atomic(OUT/'manifest.json',manifest)
    return manifest

def plan_listing_pages(total, visited, cursor, budget):
    """Keep page 1 fresh, then fill slots with unseen pages before revisits.

    Rotation from persisted cursor prevents a repeatedly failing page from
    permanently blocking unseen pages farther around the index.
    """
    if total < 1 or budget < 1:
        return []
    if total == 1 or budget == 1:
        return [1]
    start = (max(2, int(cursor)) - 2) % (total - 1)
    cycle = list(range(2, total + 1))
    rotated = cycle[start:] + cycle[:start]
    unseen = [p for p in rotated if p not in visited]
    seen = [p for p in rotated if p in visited]
    return [1] + (unseen + seen)[:budget - 1]


def next_listing_cursor(total, planned, fallback):
    """Advance past the last scheduled non-index page, not just a fixed count."""
    last = next((p for p in reversed(planned) if p != 1), None)
    if last is None or total <= 1:
        return max(2, int(fallback))
    return last + 1 if last < total else 2


def order_family_profiles(families, strategy='stratified'):
    """Stable ordering of *all known* families across four historic ID bands.

    This operates on live discovered families, not an old audit CSV. Quartiles
    are interleaved in numeric ascending order; filtering out verified and
    retry-delayed entries happens later, so profileCursor stays anchored to
    the full universe instead of an ever-shrinking eligible list.
    """
    numbered=[]
    for url in set(families):
        if not isinstance(url,str) or not safe_url(url):continue
        match=CHAR_URL.fullmatch(urlparse(url).path)
        if match:
            numbered.append((int(re.search(r'/char/(\d+)',urlparse(url).path).group(1)),url))
    numbered.sort(key=lambda pair:(pair[0],pair[1]))
    if strategy=='newest_first':
        return [url for _,url in reversed(numbered)]
    if strategy!='stratified':
        raise ValueError('unknown profile strategy')
    size=len(numbered)
    bands=[numbered[(band*size)//4:((band+1)*size)//4] for band in range(4)]
    ordered=[]
    for offset in range(max((len(band) for band in bands),default=0)):
        for band in bands:
            if offset<len(band):ordered.append(band[offset][1])
    return ordered


def choose_family_profiles(order, verified, retries, run_number, cursor, count):
    """Pick at most count new URLs while preserving retry delays/cursor.

    Returned cursor is an index in the full ordering and only moves past the
    final selected URL; it does not claim the URL was fetched successfully.
    """
    if count < 0:raise ValueError('count must be nonnegative')
    if not order or count==0:return [],(cursor%len(order) if order else 0)
    start=cursor%len(order)
    selected=[];last=None
    for offset in range(len(order)):
        idx=(start+offset)%len(order)
        url=order[idx]
        if url in verified:continue
        delay=retries.get(url,{})
        if run_number<int(delay.get('retryAfterRun',0)):continue
        selected.append(url);last=idx
        if len(selected)>=count:break
    return selected,((last+1)%len(order) if last is not None else start)


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
    visited=set(int(x) for x in state.get('visitedPages',old_manifest.get('scan',{}).get('pages',[])) if str(x).isdigit() and 1<=int(x)<=total)
    pages=plan_listing_pages(total, visited, cursor, args.pages)
    robots=RobotFileParser()
    if check_robots:robots.set_url(BASE+'/robots.txt');robots.read()
    scanned=[];warnings=[]
    # Source page URL identifies a family; representative ID is NOT the family ID.
    families={}
    for item in rows.values():
        u=item.get('source','').split('#',1)[0]
        if safe_url(u) and CHAR_URL.match(urlparse(u).path):families[u]=True
    verified_urls=set(u for u in state.get('verifiedFamilyURLs',[]) if isinstance(u,str) and safe_url(u))
    # Backfill: a prior 'verified' result could contain only one recognized form.
    # Re-check families whose known representative IDs are not present in their
    # own profile extraction. Never count an unverified family as complete.
    representative_ids={}
    for item in rows.values():
        u=item.get('source','').split('#',1)[0]
        if safe_url(u) and CHAR_URL.match(urlparse(u).path) and item.get('id'):
            representative_ids.setdefault(u,set()).add(str(item['id']))
    verified_form_ids={u:set(map(str,ids)) for u,ids in state.get('verifiedFamilyFormIDs',{}).items()
                       if isinstance(u,str) and safe_url(u) and isinstance(ids,list)}
    verified_incomplete={u for u in verified_urls if u not in verified_form_ids
                         or not representative_ids.get(u,set()).intersection(verified_form_ids[u])}
    verified_urls.difference_update(verified_incomplete)
    rate_limited=False
    for page in pages:
        url=INDEX if page==1 else INDEX+f'page/{page}/'
        if check_robots and not robots.can_fetch(USER_AGENT,url):
            warnings.append(f'robots.txt denies page {page}');continue
        try:
            r=session.get(url,timeout=25);r.raise_for_status()
            if len(r.content)>4_000_000:raise ValueError('response too large')
            found,pg=parse_listing(r.text,url)
            if not found:raise ValueError('0 recognizable cards; refusing update of this page')
            scanned.append(page);visited.add(page)
            if pg and 1<=pg<=500:total=pg
            for key,entry in found.items():
                rows[key]=reconcile(rows.get(key),entry)
                source=entry['source'].split('#',1)[0]
                if safe_url(source):
                    families[source]=True
                    representative_ids.setdefault(source,set()).add(key)
        except (requests.RequestException,ValueError) as e:
            warnings.append(f'page {page}: {str(e)[:110]}')
            if isinstance(e,requests.HTTPError) and e.response is not None and e.response.status_code==429:
                rate_limited=True;break
        wait(args.delay)
    if not scanned:
        raise RuntimeError('No pages fetched; existing output was not touched: '+str(warnings[:3]))
    # A failing high-number family must not starve all other families. Iterate
    # deterministically across the full discovered family set, using a persisted
    # cursor and a bounded per-family backoff (runs, not wall-clock seconds).
    family_order=order_family_profiles(families, strategy=getattr(args,'profile_strategy','newest_first'))
    run_number=max(0,int(state.get('runNumber',0)))+1
    retry_state={u:v for u,v in state.get('profileRetry',{}).items()
                 if u in families and isinstance(v,dict)}
    profile_cursor=int(state.get('profileCursor',0))%max(len(family_order),1)
    selected,next_profile_cursor=choose_family_profiles(
        family_order,verified_urls,retry_state,run_number,profile_cursor,args.profiles)
    # Match the existing behavior: do not advance cursor after listing HTTP 429.
    # The next run will re-evaluate verified and retry-delayed families.
    if selected and not rate_limited:
        profile_cursor=next_profile_cursor
    def failed_profile(url):
        prior=retry_state.get(url,{})
        count=min(12,int(prior.get('failures',0))+1)
        retry_state[url]={'failures':count,'retryAfterRun':run_number+min(2**min(count,5),32)}
    verified_this_run=0;forms_extracted=0;unmatched_profiles=0;incomplete_profiles=0
    for url in ([] if rate_limited else selected):
        if check_robots and not robots.can_fetch(USER_AGENT,url):continue
        try:
            r=session.get(url,timeout=25);r.raise_for_status()
            if len(r.content)>4_000_000:raise ValueError('profile too large')
            forms=parse_family(r.text,url)
            if not forms:
                warnings.append(f'family parse failed: {url}')
                failed_profile(url)
                continue
            parsed_ids={item['id'] for item in forms}
            audit=audit_profile_forms(r.text, forms)
            expected=representative_ids.get(url,set())
            # The listing's representative form must be among the profile forms.
            # Otherwise the parser may have captured an unrelated subset; retry
            # in a later run rather than permanently marking the family verified.
            if expected and not parsed_ids.intersection(expected):
                unmatched_profiles+=1
                warnings.append(f'representative form missing from family profile: {url}')
                failed_profile(url)
                continue
            for item in forms:
                # Retain familiar short name when a listing record already exists.
                old=rows.get(item['id'])
                if old and old.get('name'):
                    item['name']=old['name']
                rows[item['id']]=reconcile(old,item,verified=True)
                forms_extracted+=1
            # Partial pages contribute confirmed records but must be retried.
            if audit['incomplete']:
                incomplete_profiles+=1
                warnings.append(f'incomplete profile forms {url}: {audit["parsed"]}/{audit["headings"]} ({audit["reason"]})')
                failed_profile(url)
                continue
            verified_urls.add(url)
            retry_state.pop(url,None)
            verified_form_ids[url]=parsed_ids
            verified_this_run+=1
        except (requests.RequestException,ValueError) as e:
            warnings.append(f'family {url}: {str(e)[:90]}')
            failed_profile(url)
            if isinstance(e,requests.HTTPError) and e.response is not None and e.response.status_code==429:
                rate_limited=True;break
        wait(args.delay)
    stamp=datetime.now(timezone.utc).isoformat()
    assert len(rows)>=len(previous)
    coverage={'visitedPages':sorted(visited),'totalPages':total,
              'listingPagesVisited':len(visited),'listingPagesRemaining':max(0,total-len(visited)),
              'profileVerifiedThisRun':verified_this_run,'formsExtractedThisRun':forms_extracted,
              'familiesDiscovered':len(families),'familiesVerified':len(verified_urls & set(families)),
              'familiesRemaining':len(set(families)-verified_urls),
              'profilesAttemptedThisRun':len([] if rate_limited else selected),
              'profileSelectionStrategy':getattr(args,'profile_strategy','stratified'),
               'profileRetryDelayed':sum(1 for u in families if u not in verified_urls
                                        and run_number<int(retry_state.get(u,{}).get('retryAfterRun',0))),
              'listingPagesMissing':sorted(p for p in range(1,total+1) if p not in visited),
              'unmatchedRepresentativeProfilesThisRun':unmatched_profiles,
               'incompleteFormSectionsThisRun':incomplete_profiles,
              'rateLimited':rate_limited,
              'imagesPresent':sum(bool(v.get('image')) for v in rows.values()),
              'abilitiesPresent':sum(bool(v.get('abilities')) for v in rows.values()),
              'representativeRecords':len(rows),'complete':False}
    manifest=make_outputs(rows,stamp,scanned,warnings,coverage)
    atomic(ROOT/'catalog-coverage.json',{'generatedAt':stamp,**coverage})
    next_page=next_listing_cursor(total,pages,cursor)
    if rate_limited:
        incomplete=[p for p in pages if p not in scanned and p!=1]
        if incomplete:next_page=incomplete[0]
    atomic(STATE,{'nextPage':next_page,'totalPages':total,'lastRun':stamp,
                  'visitedPages':sorted(visited),'runNumber':run_number,
                  'profileCursor':profile_cursor,'profileRetry':retry_state,
                  'verifiedFamilyURLs':sorted(verified_urls),
                  'verifiedFamilyFormIDs':{u:sorted(v,key=int) for u,v in verified_form_ids.items()
                                            if u in verified_urls}})
    print(f'pages={scanned} families_verified={verified_this_run} forms={forms_extracted} records={manifest["count"]} nextPage={next_page} warnings={len(warnings)}')
    return manifest

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--pages',type=int,default=5)
    p.add_argument('--profiles',type=int,default=15)
    p.add_argument('--profile-strategy',choices=('stratified','newest_first'),default='stratified',
                   help='live family order; newest_first rolls back to the previous behavior')
    p.add_argument('--delay',type=float,default=1.5)
    args=p.parse_args()
    if not 2<=args.pages<=12 or not 0<=args.profiles<=60 or args.delay<0.5:p.error('limits exceeded')
    s=requests.Session();s.headers.update({'User-Agent':USER_AGENT,'Accept-Language':'ja,en;q=0.8'})
    return update(args,s)
if __name__=='__main__':main()
