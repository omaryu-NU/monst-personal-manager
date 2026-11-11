# 第16段階：画像検証履歴の永続化と、検証済み画像URLの証拠登録

## このパッチで実装すること

- GitHub Actionsで手動実行したときのみ、明示的に許可された画像候補を**最大3件**検証。各リクエスト間は最低4秒。
- `catalog-image-backfill-state.json`（新規、リポジトリ直下）に `lastProcessedID`、`runNumber`、失敗時の `retry` を保存し、図鑑更新と**同一Gitコミット**に含める。
- 収集直後に旧証拠を復元してから未登録候補を探す。同じ画像を繰り返し検査しにくいようにする。
- `catalog_image_backfill.audit(..., apply=True)` がHTTP 200・WebP形式を確認した画像のみローカル図鑑へ追加する。
- 検証ログを `catalog_image_evidence.import_report(..., apply=True)` に渡し、現在のJSONに同じURLが存在することを再検証して証拠ファイルに登録。
- その後に既存の画像統合検査、構造検査を実行。問題があればコミット・Hosting公開を停止。
- `catalog-image-evidence.json`と状態ファイルも`git add`し、再実行時に履歴を維持する。

**重要な限界**：HTTP 200・WebP署名・URL内の図鑑No.を確認しても、絵の内容がそのキャラであることは証明できません。本仕組みの「検証済み」とは通信形式・URL構造に対する確認であり、人物・キャラ画像の意味的同一性を保証しません。初回の手動試行では3枚の画像を目視で確認してから本番公開を再開してください。

## 事前に必要なファイル

既存の第13〜15段階の以下がGitHubにコミット済みであること：

- `scripts/catalog_image_backfill.py`
- `scripts/catalog_image_evidence.py`
- `scripts/catalog_image_integration_audit.py`
- `catalog-image-evidence.json`
- `.github/workflows/catalog-update.yml`

このパッチは上記の既存スクリプトを置き換えず、新規の `scripts/catalog_image_auto.py` と`test_catalog_phase16.py`、ワークフローのみを更新します。

## 作業手順（Mac、プロジェクト直下）

```bash
# 1. 先にGitの状態を確認。未コミット変更があれば個別にバックアップ
 git status --short
 cp .github/workflows/catalog-update.yml ~/catalog-update-before-phase16.yml

# 2. パッチ適用
 unzip -o ~/Downloads/monst-catalog-phase16-image-persistence-patch.zip

# 3. 新規テスト・全テスト
 python3 -m unittest discover -s scripts -p 'test_catalog_phase16.py'
 python3 -m unittest discover -s scripts -p 'test_catalog_*.py'

# 4. ワークフロー差分の確認
 git diff -- .github/workflows/catalog-update.yml

# 5. コードだけコミットする
 git add scripts/catalog_image_auto.py scripts/test_catalog_phase16.py .github/workflows/catalog-update.yml PHASE16-README.md
 git commit -m 'feat: persist verified catalog image backfill state'
```

**同期前**に `git status --short` を確認してください。自動更新された `catalog-coverage.json` や `public/catalog/characters-*.json` が未コミットなら、必要なものをバックアップしてから `git stash push -m "backup before phase16 sync"` を使います。`git pull --rebase origin main` → `git push origin main`。`CONFLICT` が出たら停止し、`--force`は使わないでください。`git stash pop` は図鑑変更の衝突を生む場合があるので、先に差分を確認してください。

## 最初のGitHub Actions試行

Repository Variables（Settings → Secrets and variables → Actions → Variables）:

| Variable | 設定値 | 説明 |
|---|---|---|
| `TECHNOPHERE_REUSE_APPROVED` | `true` | 必須の許可フラグ |
| `IMAGE_PROBE_DRY_RUN` | `false` | 第15段階の検証を無効化（二重アクセス防止） |
| `IMAGE_BACKFILL_ENABLED` | `true` | 第16段階を有効化 |
| `IMAGE_BACKFILL_SCHEDULED` | `false` | まず定期実行を無効のままにする |
| `AUTO_DEPLOY_HOSTING` | `false` | 本番公開を一時停止 |

`Update Technophere catalog` → `Run workflow` を **mainブランチから手動実行**。

- `Phase 16 verified image backfill and evidence registration` が成功すること。
- Artifact `catalog-image-backfill-phase16` の `phase16-apply.json` と `phase16-summary.json` を確認。
- `phase16-apply.json`: `attempted <= 3`, `dryRun=false`, `rateLimited=false`, `verifiedCount == updatedRecords`。
- `phase16-summary.json`: `newEvidence`, `evidenceCount` および `imageIdentityVerified=false` を確認。
- リポジトリ直下の `catalog-image-backfill-state.json` がコミットされ、次回の実行でも`lastProcessedID`を引き継げること。
- `catalog-image-evidence.json` の `images` に新規図鑑No.が追加され、次回の画像復元・統合検査を通ること。
- 3枚の画像が正しいキャラを描いていることは目視確認すること（HTTP検証だけでは保証できない）。

正常確認後も `IMAGE_BACKFILL_SCHEDULED=false` を維持して複数回手動で確かめてください。定期実行に移行する場合だけ `IMAGE_BACKFILL_SCHEDULED=true` にします。3時間ごとの実行では、スクレイピング本体のアクセス数に画像3件分が追加されるため、サイト側の許可範囲を守り、429が出たら無効化してください。

## 問題が出た場合

- 429: ワークフローが失敗し、今回の結果はコミット・公開されません。`IMAGE_BACKFILL_ENABLED=false` に戻し頻度を再確認。
- 画像証拠の衝突: 上書きせず停止。既存証拠と実際のURLを人手で照合。
- git pushの競合: Actionsのコミットが競合した場合、強制pushはせず、最新コミットの取り込みと再検証を行う。

Firebase Hosting以外のFirebaseサービスにはアクセスしません。Firestoreの所持キャラ・編成データは変更しません。
