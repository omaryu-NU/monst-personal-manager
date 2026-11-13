#!/usr/bin/env python3
"""Minimal, guarded source edit: replace only the catalog card icon element.
Does not overwrite the rest of CatalogBrowser.tsx, app state, or Firebase code.
"""
import argparse
import difflib
import re
from pathlib import Path

OLD_ICON = re.compile(r'<span\s+className="char-icon"\s*>.*?</span>', re.DOTALL)
NEW_ICON = '<SelfHostedCharacterIcon id={c.id} name={c.name} />'
IMPORT = "import SelfHostedCharacterIcon from './SelfHostedCharacterIcon';\n"


def patch_source(content: str) -> str:
    if NEW_ICON in content:
        if IMPORT not in content:
            raise ValueError('アイコンは置換済みですがimportがありません。手動確認してください。')
        return content
    matches = list(OLD_ICON.finditer(content))
    if len(matches) != 1:
        raise ValueError(f'char-iconが{len(matches)}個見つかりました。想定と異なるため変更しません。')
    old = matches[0].group(0)
    if 'c.image' not in old and 'c.name' not in old:
        raise ValueError('既存のアイコン表示構造が異なります。変更しません。')
    result = content[:matches[0].start()] + NEW_ICON + content[matches[0].end():]
    if "import SelfHostedCharacterIcon" in result:
        raise ValueError('別形式の同名importがあります。変更しません。')
    result = IMPORT + result
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--file', default='src/CatalogBrowser.tsx')
    p.add_argument('--apply', action='store_true')
    args = p.parse_args()
    file = Path(args.file)
    before = file.read_text(encoding='utf-8')
    after = patch_source(before)
    if before == after:
        print('Already installed. No changes.')
        return
    changes = ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True), fromfile=str(file), tofile=str(file) + ' (proposed)'))
    if args.apply:
        backup = file.with_suffix(file.suffix + '.before-local-icons.bak')
        if backup.exists():
            raise SystemExit(f'バックアップが既にあります: {backup}。上書きを避けるため停止しました。')
        backup.write_text(before, encoding='utf-8')
        file.write_text(after, encoding='utf-8')
        print(f'Applied. Backup: {backup}')
    else:
        print('DRY RUN (no files changed):\n' + changes)


if __name__ == '__main__':
    main()
