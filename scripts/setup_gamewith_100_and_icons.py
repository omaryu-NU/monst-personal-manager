#!/usr/bin/env python3
"""Preview/apply a narrowly-scoped GameWith workflow and catalog icon update."""
import argparse
import difflib
import shutil
from pathlib import Path

WORKFLOW = Path('.github/workflows/gamewith-approved-icons.yml')
CATALOG = Path('src/CatalogBrowser.tsx')
COMPONENT = Path('src/SelfHostedCharacterIcon.tsx')
TEMPLATE = Path(__file__).resolve().parent.parent / 'patch_assets' / 'SelfHostedCharacterIcon.tsx'

OLD_STEP = 'Download validated GameWith images (max 10 per run)'
NEW_STEP = 'Download validated GameWith images (up to 100 per UTC day)'
OLD_CALL = '''          python scripts/auto_import_approved_icons.py \\
            --csv config/gamewith-approved-icon-sources.csv \\
            --allow-host img.gamewith.jp \\
            --limit 10 --delay 3 --allow-denied --apply \\
            --report local-reports/gamewith-icons/import.json'''
NEW_CALL = '''          python scripts/import_gamewith_daily.py \\
            --csv config/gamewith-approved-icon-sources.csv \\
            --allow-host img.gamewith.jp \\
            --limit 100 --delay 3 --allow-denied --apply \\
            --report local-reports/gamewith-icons/import.json'''
OLD_IMG = '<span className="char-icon">{c.image?<img alt="" loading="lazy" referrerPolicy="no-referrer" src={c.image} decoding="async"/>:c.name.slice(0,1)}</span>'
NEW_IMG = '<SelfHostedCharacterIcon id={c.id} name={c.name} />'
IMPORT = "import SelfHostedCharacterIcon from './SelfHostedCharacterIcon';\n"


def update_workflow(source):
    if NEW_STEP in source and NEW_CALL in source:
        return source
    if source.count(OLD_STEP) != 1 or source.count(OLD_CALL) != 1:
        raise ValueError('Workflow does not match expected version; refusing to overwrite')
    result = source.replace(OLD_STEP, NEW_STEP).replace(OLD_CALL, NEW_CALL)
    if 'timeout-minutes: 20' not in result:
        raise ValueError('Unexpected workflow timeout')
    return result.replace('timeout-minutes: 20', 'timeout-minutes: 60', 1)


def update_catalog(source):
    if NEW_IMG in source:
        if IMPORT not in source:
            raise ValueError('Icon component already used but import missing')
        return source
    if source.count(OLD_IMG) != 1:
        raise ValueError('Existing card icon layout differs; refusing to modify')
    if 'SelfHostedCharacterIcon' in source:
        raise ValueError('Unexpected existing component reference')
    return IMPORT + source.replace(OLD_IMG, NEW_IMG)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apply', action='store_true', help='Write changes; otherwise show diffs')
    args = p.parse_args()
    modifications = {}
    for path, fn in ((WORKFLOW, update_workflow), (CATALOG, update_catalog)):
        before = path.read_text(encoding='utf-8')
        after = fn(before)
        if after != before:
            modifications[path] = (before, after)
            print(''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                               fromfile=str(path), tofile=str(path) + ' (new)')))
    if not COMPONENT.exists() and not TEMPLATE.exists():
        raise ValueError('Missing icon component and template')
    if not args.apply:
        print('PREVIEW ONLY. Run with --apply to edit. Component:', 'exists' if COMPONENT.exists() else 'will be installed')
        return
    # Take backups before changing anything. Refuse if a previous backup is present.
    for path in modifications:
        backup = path.with_suffix(path.suffix + '.before-gamewith100.bak')
        if backup.exists():
            raise ValueError(f'Backup already exists: {backup}')
    for path, (before, after) in modifications.items():
        backup = path.with_suffix(path.suffix + '.before-gamewith100.bak')
        backup.write_text(before, encoding='utf-8')
        path.write_text(after, encoding='utf-8')
        print(f'Updated {path} (backup: {backup})')
    if not COMPONENT.exists():
        shutil.copyfile(TEMPLATE, COMPONENT)
        print(f'Installed {COMPONENT}')
    print('Finished. Run tests and npm run build before committing.')

if __name__ == '__main__':
    main()
