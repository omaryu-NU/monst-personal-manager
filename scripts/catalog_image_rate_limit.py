#!/usr/bin/env python3
"""Persisted image-request pause gate. Offline only; no HTTP or catalog mutation."""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def dt(value):
    if not isinstance(value, str): raise ValueError('timestamp required')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None: raise ValueError('timezone required')
    return result.astimezone(timezone.utc)


def check(path, *, now=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None: raise ValueError('timezone required')
    p=Path(path)
    if not p.exists(): return {'allowed': True, 'reason': 'no_prior_rate_limit'}
    try:
        content=json.loads(p.read_text(encoding='utf-8'))
        if content.get('schema') != 1 or content.get('reason') != 'HTTP_429':
            raise ValueError('schema mismatch')
        until=dt(content['pauseUntil'])
        happened=dt(content['observedAt'])
        if until <= happened or until-happened > timedelta(hours=72):
            raise ValueError('invalid pause duration')
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {'allowed':False,'reason':'invalid_pause_state'}
    if now < until:
        return {'allowed':False, 'reason':'rate_limit_cooldown', 'pauseUntil':until.isoformat()}
    return {'allowed':True, 'reason':'cooldown_expired', 'pauseUntil':until.isoformat()}


def record(path, report, *, now=None, hours=24):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None or not 24 <= hours <= 72:
        raise ValueError('24..72 hour cooldown required')
    data=json.loads(Path(report).read_text(encoding='utf-8'))
    if data.get('rateLimited') is not True or not any(
        x.get('status') == 'rate_limited' and x.get('http_status') == 429
        for x in data.get('results',[]) if isinstance(x,dict)
    ):
        raise ValueError('Refusing to pause without an explicit HTTP 429 report')
    path=Path(path)
    # Never shorten an active prior pause; malformed state blocks recording.
    previous=check(path,now=now)
    if previous['reason']=='invalid_pause_state':
        raise ValueError('Existing pause state invalid; manual review required')
    until=now+timedelta(hours=hours)
    if 'pauseUntil' in previous:
        until=max(until,dt(previous['pauseUntil']))
    result={'schema':1,'reason':'HTTP_429','observedAt':now.isoformat(),
            'pauseUntil':until.isoformat(), 'minimumPauseHours':hours,
            'note':'Only image probe HTTP 429. Does not indicate catalog scraper rate limits.'}
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(path)
    return result


def main():
    p=argparse.ArgumentParser()
    sp=p.add_subparsers(dest='command',required=True)
    q=sp.add_parser('check');q.add_argument('--state',default='catalog-image-rate-limit.json');q.add_argument('--github-output')
    r=sp.add_parser('record');r.add_argument('--state',default='catalog-image-rate-limit.json');r.add_argument('--report',required=True);r.add_argument('--hours',type=int,default=24)
    a=p.parse_args()
    result=check(a.state) if a.command=='check' else record(a.state,a.report,hours=a.hours)
    print(json.dumps(result,ensure_ascii=False))
    if a.command=='check' and a.github_output:
        with open(a.github_output,'a',encoding='utf-8') as f:f.write('allowed='+str(result['allowed']).lower()+'\n')

if __name__=='__main__':main()
