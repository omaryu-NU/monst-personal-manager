#!/usr/bin/env python3
"""GameWith icon import with a persisted UTC daily request budget.

The budget is per GameWith workflow only; no browser scraping or guessed URLs.
The ledger lives beside downloaded icons so the existing workflow commits it.
"""
import argparse
import datetime as dt
import json
from pathlib import Path

from auto_import_approved_icons import run, atomic_json

BUDGET_NAME = 'gamewith-daily-budget.json'


def remaining_budget(ledger, today, cap):
    if cap < 1 or cap > 100:
        raise ValueError('Daily cap must be between 1 and 100')
    if ledger.get('day') != today:
        return cap
    used = ledger.get('attempts', 0)
    if type(used) is not int or used < 0:
        raise ValueError('Invalid daily usage ledger')
    return max(0, cap - used)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--csv', type=Path, required=True)
    p.add_argument('--allow-host', action='append', required=True)
    p.add_argument('--output', type=Path, default=Path('public/character-icons'))
    p.add_argument('--limit', type=int, default=100)
    p.add_argument('--delay', type=float, default=3.)
    p.add_argument('--allow-denied', action='store_true')
    p.add_argument('--apply', action='store_true')
    p.add_argument('--report', type=Path)
    args = p.parse_args(argv)
    hosts = {h.strip().lower() for h in args.allow_host}
    day = dt.datetime.now(dt.timezone.utc).date().isoformat()
    ledger_file = args.output / BUDGET_NAME
    ledger = json.loads(ledger_file.read_text(encoding='utf-8')) if ledger_file.exists() else {}
    if not isinstance(ledger, dict):
        p.error('Invalid daily budget file')
    try:
        remaining = remaining_budget(ledger, day, args.limit)
        dry = run(args.csv, args.output, hosts, apply=False, limit=1, delay=args.delay)
        attempts = min(remaining, dry['pending'])
        if not args.apply or attempts == 0:
            result = {**dry, 'mode': 'dry-run' if not args.apply else 'daily-budget-exhausted',
                      'attempted': 0, 'daily_remaining': remaining, 'daily_cap': args.limit}
        else:
            # Reserve the daily request budget in this checkout BEFORE the first fetch.
            # The workflow stages this file with imported images in a single commit.
            previous = ledger['attempts'] if ledger.get('day') == day else 0
            atomic_json(ledger_file, {'day': day, 'attempts': previous + attempts, 'cap': args.limit})
            result = run(args.csv, args.output, hosts, apply=True, limit=attempts,
                         delay=args.delay, allow_denied=args.allow_denied)
            result.update(attempted=attempts, daily_remaining=remaining - attempts, daily_cap=args.limit)
        if args.report:
            atomic_json(args.report, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if result['errors'] else 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        p.error(str(exc))


if __name__ == '__main__':
    raise SystemExit(main())
