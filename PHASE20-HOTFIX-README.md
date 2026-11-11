# 第20段階・第4段階互換性修正

第20段階は `--profile-strategy stratified` をGitHub Actionsから明示して呼びます。一方、第4段階の旧テストは `args.profile_strategy` を渡しません。その場合だけ旧来の `newest_first` を使用するようにしました。

- GitHub Actionsの `--profile-strategy stratified` はそのままです。
- `profileRetry`、429対応、収集データ、状態ファイルは変更しません。
- ZIPに状態ファイル・カタログJSON・ワークフローは含めません。

## 適用

```bash
cp scripts/technophere_catalog.py ~/technophere_catalog-before-phase20-hotfix.py
unzip -o ~/Downloads/monst-catalog-phase20-test-compat-hotfix.zip
python3 -m unittest discover -s scripts -p 'test_catalog_*.py'
git diff -- scripts/technophere_catalog.py
git add scripts/technophere_catalog.py scripts/test_catalog_phase20_compat.py PHASE20-HOTFIX-README.md
git commit -m "fix: preserve legacy profile selection for older callers"
```

`git pull --rebase origin main` 前に `git status --short` で未コミット変更を確認してください。`catalog-coverage.json` のみ変更済みなら既存の `python3 scripts/catalog_local_sync_guard.py --apply` でバックアップ後に整理できます。競合時は停止してください。
