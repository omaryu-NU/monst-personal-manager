#!/usr/bin/env python3
"""Idempotently insert audit gate + upload artifact into existing workflow.
Never replaces the existing firebase deployment logic.
"""
from pathlib import Path
p=Path('.github/workflows/catalog-update.yml')
if not p.exists():raise SystemExit('Workflow not found: '+str(p))
s=p.read_text(encoding='utf-8')
if 'Phase 5 catalog structural integrity gate' in s:
    print('Already installed; no changes');raise SystemExit(0)
needle='      - name: Commit validated catalog\n'
if s.count(needle)!=1:raise SystemExit('Expected commit step not found exactly once. No changes made.')
addition='''      - name: Phase 5 catalog structural integrity gate
        run: python scripts/catalog_integrity.py public/catalog --output catalog-integrity-report
      - name: Upload catalog integrity report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: catalog-integrity-report
          path: catalog-integrity-report/
          if-no-files-found: warn
          retention-days: 14
'''
p.write_text(s.replace(needle,addition+needle),encoding='utf-8')
print('Added Phase 5 check before catalog commit and Hosting deploy; preserves existing workflow')
