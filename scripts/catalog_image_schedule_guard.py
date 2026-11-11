#!/usr/bin/env python3
"""Phase 17: fail-closed, offline cooldown gate for scheduled image requests.

Does not change catalog, image evidence or backfill state; makes no network calls.
The gate is advisory for schedule eligibility; Phase16 still enforces <=3.
"""
from __future__ import annotations
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


def parse_timestamp(s):
    if not isinstance(s, str):
        raise ValueError('timestamp is not a string')
    d = datetime.fromisoformat(s.replace('Z', '+00:00'))
    if d.tzinfo is None:
        raise ValueError('timestamp must include UTC offset')
    return d.astimezone(timezone.utc)


def evaluate(state, evidence, *, now=None, min_hours=6, hosting_enabled=False):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or not 6 <= min_hours <= 48:
        raise ValueError('now must be timezone aware; min_hours must be 6..48')
    result = {'runBackfill': False, 'reason': '', 'minHours': min_hours,
              'checkedAt': now.astimezone(timezone.utc).isoformat(), 'evidenceCount': 0}
    if hosting_enabled:
        result['reason'] = 'hosting_enabled_blocks_unreviewed_image_backfill'
        return result
    try:
        ev=json.loads(Path(evidence).read_text(encoding='utf-8'))
        images=ev.get('images')
        if ev.get('schema') != 1 or not isinstance(images, dict) or not images:
            result['reason']='missing_or_invalid_evidence'
            return result
        result['evidenceCount']=len(images)
    except (OSError, ValueError, AttributeError):
        result['reason']='missing_or_invalid_evidence'
        return result
    try:
        st=json.loads(Path(state).read_text(encoding='utf-8'))
        if st.get('schema') != 2 or not isinstance(st.get('lastProcessedID'),int) or st['lastProcessedID'] < 0:
            result['reason']='missing_or_invalid_state'
            return result
        last=parse_timestamp(st.get('updatedAt'))
    except (OSError, ValueError, TypeError, AttributeError):
        result['reason']='missing_or_invalid_state'
        return result
    if last > now:
        result['reason']='future_state_timestamp'
    elif now-last < timedelta(hours=min_hours):
        result['reason']='cooldown_active'
    else:
        result['runBackfill']=True
        result['reason']='eligible'
    result['lastUpdatedAt']=last.isoformat()
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state', default='catalog-image-backfill-state.json')
    p.add_argument('--evidence', default='catalog-image-evidence.json')
    p.add_argument('--min-hours', type=int, default=6)
    p.add_argument('--github-output', default='')
    p.add_argument('--report',default='local-reports/image-backfill/phase17-schedule-guard.json')
    a=p.parse_args()
    result=evaluate(a.state,a.evidence,min_hours=a.min_hours,
                    hosting_enabled=os.getenv('AUTO_DEPLOY_HOSTING','').lower()=='true')
    out=Path(a.report);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if a.github_output:
        with open(a.github_output,'a',encoding='utf-8') as f:
            f.write('run_backfill='+str(result['runBackfill']).lower()+'\n')
    print(json.dumps(result,ensure_ascii=False))
    # An absent/invalid state SKIPS requests safely rather than blocking the
    # non-image catalog collection; report explains why.

if __name__=='__main__':main()
