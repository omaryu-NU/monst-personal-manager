#!/usr/bin/env python3
"""Backup only local generated coverage changes; never runs pull/push or discards other changes."""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import subprocess
from pathlib import Path

TARGET='catalog-coverage.json'

def run(repo,*args):
    return subprocess.run(['git','-C',str(repo),*args],capture_output=True,text=True,check=True).stdout

def prepare(repo, *, apply=False, backup_root='local-reports/git-sync-backups'):
    repo=Path(repo).resolve()
    root=Path(run(repo,'rev-parse','--show-toplevel').strip()).resolve()
    if repo!=root:raise ValueError('Run from repository root')
    status=run(root,'status','--porcelain','--untracked-files=no')
    changed=[line[3:] for line in status.splitlines() if line]
    if TARGET not in changed:
        return {'status':'nothing_to_backup','changed':changed,'applied':False}
    if not (root/TARGET).is_file():raise ValueError('coverage is not a regular file')
    if run(root,'diff','--cached','--name-only','--',TARGET).strip():
        raise ValueError('Staged coverage changes: refuse auto-restore')
    if run(root,'ls-files','--',TARGET).strip()!=TARGET:
        raise ValueError('coverage not tracked: refuse')
    raw=(root/TARGET).read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    planned=root/backup_root/f'{TARGET.removesuffix(".json")}-{digest[:16]}.json'
    if not planned.is_relative_to(root) or planned==root/TARGET:
        raise ValueError('backup must be in repository subdirectory')
    result={'status':'backup_required','changed':changed,'backup':str(planned),'sha256':digest,'applied':False}
    if apply:
        planned.parent.mkdir(parents=True,exist_ok=True)
        if planned.exists() and planned.read_bytes()!=raw:
            raise ValueError('Backup path collision')
        planned.write_bytes(raw)
        if hashlib.sha256(planned.read_bytes()).hexdigest()!=digest:
            raise IOError('backup verification failed')
        run(root,'restore','--worktree','--',TARGET)
        result['applied']=True
        result['status']='backed_up_and_restored_generated_coverage'
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--repo',default='.');p.add_argument('--apply',action='store_true')
    a=p.parse_args();print(json.dumps(prepare(a.repo,apply=a.apply),ensure_ascii=False,indent=2))

if __name__=='__main__':main()
