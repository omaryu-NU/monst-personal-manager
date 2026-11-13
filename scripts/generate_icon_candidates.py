#!/usr/bin/env python3
"""Derive authorized icon download queue only from existing explicit catalog image URLs.

Never guess filenames or request third party pages. No network access.
"""
import argparse
import csv
import json
import re
import urllib.parse
from pathlib import Path

FIELDS = ('id','url','license','permission_reference','attribution')
ID = re.compile(r'[0-9]{1,6}\Z')
EXT = re.compile(r'\.(?:png|jpg|jpeg|webp)\Z', re.I)


def discover(catalog_dir: Path, host: str):
    manifest = json.loads((catalog_dir / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema') != 1 or not isinstance(manifest.get('chunks'), list):
        raise ValueError('catalog manifest形式が不正です')
    found = {}
    for chunk in manifest['chunks']:
        file = chunk.get('path', '')
        if not isinstance(file, str) or not re.fullmatch(r'characters-\d{4}\.json', file):
            raise ValueError('不正なチャンク名です')
        for row in json.loads((catalog_dir / file).read_text(encoding='utf-8')).get('characters', []):
            id_ = str(row.get('id',''))
            url = row.get('image')
            if not ID.fullmatch(id_) or not isinstance(url, str):
                continue
            p = urllib.parse.urlsplit(url)
            if (p.scheme != 'https' or p.hostname != host or p.username or p.password or
                    p.port not in (None,443) or not EXT.search(p.path) or
                    Path(urllib.parse.unquote(p.path)).stem != id_):
                continue  # An image for a different form must not be assigned.
            if id_ in found and found[id_] != url:
                raise ValueError(f'No.{id_}の異なる画像URLが競合しています')
            found[id_] = url
    return found


def generate(catalog_dir:Path,csv_path:Path,host:str,permission_ref:str,attribution:str='Technophere'):
    if not host or '://' in host or '/' in host or not permission_ref.strip():
        raise ValueError('ホスト名と許諾管理番号が必要です')
    observed=discover(catalog_dir,host)
    existing={}
    if csv_path.exists():
        with csv_path.open(encoding='utf-8-sig',newline='') as f:
            reader=csv.DictReader(f)
            if not set(FIELDS).issubset(reader.fieldnames or []):
                raise ValueError('既存CSVのヘッダーが不正です')
            for row in reader:
                id_=row['id'].strip()
                if not ID.fullmatch(id_) or id_ in existing:
                    raise ValueError('既存CSVに不正または重複するNo.があります')
                existing[id_]={k:row.get(k,'') for k in FIELDS}
    additions=0
    for id_,url in observed.items():
        if id_ not in existing:
            existing[id_]={'id':id_,'url':url,'license':'Owner-reported redistribution permission',
                           'permission_reference':permission_ref,'attribution':attribution}
            additions+=1
    csv_path.parent.mkdir(parents=True,exist_ok=True)
    temp=csv_path.with_suffix('.csv.tmp')
    with temp.open('w',encoding='utf-8',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(existing[k] for k in sorted(existing,key=lambda v:int(v)))
    temp.replace(csv_path)
    return {'catalog_image_candidates':len(observed),'newly_queued':additions,'queue_total':len(existing)}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--catalog',type=Path,default=Path('public/catalog'))
    p.add_argument('--csv',type=Path,default=Path('config/approved-icon-sources.csv'))
    p.add_argument('--host',required=True)
    p.add_argument('--permission-reference',required=True,help='ユーザーが管理する許諾証跡ID。架空の許諾IDを作らないでください')
    p.add_argument('--attribution',default='Technophere')
    args=p.parse_args()
    print(json.dumps(generate(args.catalog,args.csv,args.host,args.permission_reference,args.attribution),ensure_ascii=False))

if __name__=='__main__':main()
