# Phase 18 — HTTP 429 cooldown persistence & local Git sync guard

対象: 第17段階の `catalog-update.yml` を基にした差分パッチ。`public/catalog` / Firestore / `.env` は同梱せず、ユーザーの最新データを変更しません。

## 変更内容
- `scripts/catalog_image_rate_limit.py`: 画像プローブで**明示的なHTTP 429**を報告した場合だけ `catalog-image-rate-limit.json` を作成。UTCで24時間停止。ファイルが破損していればfail-closed。通常時は通信しません。
- Workflow: 定期・手動の画像補完より前に停止判定。HTTP 429検出時は**停止記録だけをGitへコミット**し、その後にジョブを失敗させるため、図鑑本体・証拠・画像やHostingは公開されません。次の実行では停止期限が過ぎるまで画像補完のみスキップします。通常キャラ収集は継続します。
- `scripts/catalog_local_sync_guard.py`: 既存の `catalog-coverage.json` の未コミット変更だけ、SHA256付きで `local-reports/git-sync-backups/` に保存し、内容を検証してからそのファイルだけ `git restore`。他のファイルを変更せず、pull/pushも自動実行しません。

## 重要な範囲
- HTTP 429の停止は**画像バックフィルが検知する429のみ**です。通常のキャラ収集による429の長期停止は別途対応が必要です。
- URLがWebPとして正常でも、画像とキャラクターの意味的な一致は証明されません。`IMAGE_BACKFILL_SCHEDULED` の運用前に手元で点検してください。
- サイトのアクセス頻度に関する許可条件を優先してください。24時間の停止は保証された適切なアクセス頻度を意味しません。
- 最新GitHubワークフローが第17段階からさらに改修されている場合は、ZIPの上書きを行う前に差分をマージしてください。

## 適用
```bash
# 1. まず手元のコードを確認・バックアップ
cp .github/workflows/catalog-update.yml ~/catalog-update-before-phase18.yml
git status --short
# 2. ZIPをプロジェクトのルートで解凍
unzip -o ~/Downloads/monst-catalog-phase18-safe-operations-patch.zip
# 3. テスト
python3 -m unittest discover -s scripts -p 'test_catalog_phase18.py'
# 4. 変更確認
git diff -- .github/workflows/catalog-update.yml
# 5. ローカルのcoverage変更を診断（書き込みなし）
python3 scripts/catalog_local_sync_guard.py
# 必要な場合だけ、coverageをバックアップしてgitの状態に戻す
python3 scripts/catalog_local_sync_guard.py --apply
# 他に未コミット変更が残る場合は個別に確認してから
# 6. コードのみコミット
git add .github/workflows/catalog-update.yml scripts/catalog_image_rate_limit.py scripts/catalog_local_sync_guard.py scripts/test_catalog_phase18.py PHASE18-README.md
git commit -m 'ci: persist image 429 cooldown and guard local catalog sync'
git status --short
git pull --rebase origin main
git push origin main
```

## GitHub Actions検証
- 初回は `AUTO_DEPLOY_HOSTING=false`、`IMAGE_BACKFILL_SCHEDULED=false` で手動実行。
- `Phase 18 persistent image pause guard` が成功し、画像補完の実行に問題がないか確認。
- **意図的にHTTP 429を発生させてテストしないでください。** この分岐はローカルのモックテストで確認します。
- 429が自然に発生した場合、`catalog-image-rate-limit.json` がGitにコミットされ、その実行は失敗になり、カタログ更新と公開は行われないことを確認してください。
- 停止判定だけをローカルで確認する場合:
```bash
python3 scripts/catalog_image_rate_limit.py check --state catalog-image-rate-limit.json
```

## 診断結果を共有するとき
`Phase 18 persistent image pause guard` のログ、Actions成功・失敗ログ、Git同期の警告（発生時）を共有してください。設定値・認証キーは貼り付け不要です。
