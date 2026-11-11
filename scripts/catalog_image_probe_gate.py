#!/usr/bin/env python3
"""Validate a bounded, nonmutating Phase15 image dry-run report (no network)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def verify_report(report, max_attempts=3, require_dry_run=True):
    issues=[]
    if not isinstance(report, dict):
        return ['report is not an object']
    if require_dry_run and report.get('dryRun') is not True:
        issues.append('not a dry-run; stopping')
    attempted=report.get('attempted')
    verified=report.get('verifiedCount')
    updated=report.get('updatedRecords')
    events=report.get('results')
    if not isinstance(attempted,int) or isinstance(attempted,bool) or not 0<=attempted<=max_attempts:
        issues.append('attempt count invalid or limit exceeded')
    if not isinstance(verified,int) or isinstance(verified,bool) or verified<0:
        issues.append('verified count invalid')
    if updated != 0:
        issues.append('dry-run unexpectedly updated records')
    if not isinstance(events,list):
        issues.append('results not a list')
    elif isinstance(attempted,int) and len(events)!=attempted:
        issues.append('result count mismatch')
    if isinstance(verified,int) and isinstance(events,list):
        actual=sum(isinstance(e,dict) and e.get('status')=='verified' and e.get('http_status')==200 for e in events)
        if verified!=actual:
            issues.append('verified count mismatch')
    if report.get('rateLimited') is True:
        issues.append('HTTP 429 rate limit: disable probe and review request frequency')
    return issues


def main():
    p=argparse.ArgumentParser()
    p.add_argument('report',type=Path)
    p.add_argument('--max-attempts',type=int,default=3)
    p.add_argument('--require-dry-run',action='store_true')
    a=p.parse_args()
    result=verify_report(json.loads(a.report.read_text(encoding='utf-8')),
                         max_attempts=a.max_attempts,require_dry_run=a.require_dry_run)
    if result:
        for issue in result: print('FAIL:',issue)
        raise SystemExit(1)
    print('PASS: bounded, read-only image dry-run report; image identity not verified')

if __name__=='__main__':main()
