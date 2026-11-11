#!/usr/bin/env python3
"""Enable one bounded, verified-family refresh in an existing Actions command.

Refuses unrecognized workflows; does not replace the complete YAML.
"""
from pathlib import Path
import argparse


def patch(source):
    matching=[line for line in source.splitlines() if 'run: python scripts/technophere_catalog.py ' in line]
    if len(matching)!=1:
        raise ValueError('Expected exactly one catalog collection command')
    line=matching[0]
    if '--profile-strategy stratified' not in line:
        raise ValueError('Phase20 stratified collection must already be enabled')
    if '--detail-refresh 1' in line:
        return source,False
    if '--detail-refresh' in line:
        raise ValueError('Existing detail-refresh setting needs manual review')
    return source.replace(line,line+' --detail-refresh 1',1),True


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--workflow',default='.github/workflows/catalog-update.yml')
    p.add_argument('--apply',action='store_true')
    args=p.parse_args()
    path=Path(args.workflow)
    original=path.read_text(encoding='utf-8')
    updated,changed=patch(original)
    print('change_needed='+str(changed).lower())
    if args.apply and changed:
        path.write_text(updated,encoding='utf-8')
        print('workflow_updated=true')
    elif not args.apply:
        print('dry_run=true')

if __name__=='__main__':main()
