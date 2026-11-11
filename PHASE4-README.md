# Monst Personal Manager — Phase 4: retry fairness / coverage reporting

## このパッチで解決すること

- 過去の収集結果に未確認系統が多いとき、同じ失敗URLを何度も最初に試して、残りのURLに進めない問題を修正。
- 系統URLの処理順を永続化（`profileCursor`）。失敗URLは `profileRetry` の `failures` と `retryAfterRun` を記録し、最大32実行の待機を挟む。失敗しても別の系統URLへ進める。
- `profileRetryDelayed`、`profilesAttemptedThisRun`、`listingPagesMissing` を `catalog-coverage.json` および manifest の `coverage` に出力。
- 古い `catalog-update-state.json` を壊さず、新フィールドが存在しなければ初期値を適用。
- HTTP 429のときは引き続き当該実行の以後の収集を停止。429の制限回避目的の頻度増加は行わない。

## 事前に確認すること

本パッチは直前のPhase 3パッチ適用済みリポジトリを前提とする。**GitHubのActions最新実行ログ、現時点の `catalog-coverage.json` や `catalog-audit-summary.json` はこの配布ファイルに含まれないため、最新の網羅率はここでは未検証**。

## Mac / VSCode からの適用

1. 変更の退避・コミットを確認する：`git status`。
2. 作業ツリーがクリーンなら `git pull --ff-only origin main`。
3. ZIPをプロジェクト直下で解凍：`unzip -o ~/Downloads/monst-catalog-phase4-retry-patch.zip`。
4. Python依存を導入：`python3 -m pip install -r scripts/requirements-catalog.txt`。
5. テスト：`python3 -m unittest discover -s scripts -p 'test_catalog_*.py'`。**11 tests OK** を目安。
6. `git add scripts/technophere_catalog.py scripts/test_catalog_phase4.py PHASE4-README.md`。
7. `git commit -m 'fix: rotate family retries and report uncovered pages'`。
8. `git pull --rebase origin main`、成功したら `git push origin main`。競合したら一旦止める。
9. 初回は GitHub Repository Variables の `AUTO_DEPLOY_HOSTING=false` を推奨。Actions > Update Technophere catalog > Run workflow を実行。
10. 新規生成された `catalog-coverage.json` と `catalog-audit-summary.json` を取得して確認。データ品質が確認できたらHosting再開。

## 完成判定について

- `listingPagesRemaining == 0` だけでは、全形態の収録を意味しません。
- `familiesRemaining == 0` は少なくとも代表形態の照合に成功したことを表し、個別ページの全形態の完全性を保証しません。
- 画像URLは実際にHTTPで取得して検証していません。技・アビリティ欄もHTML構造と抽出精度の別検査が必要です。
- source site側の規約と許可範囲を順守し、429が続く場合は収集頻度と許可範囲を見直してください。
- ユーザーのFirestore所持キャラ・編成情報は直接変更しません。

## 今回の具体的な追加メトリクス

- `profilesAttemptedThisRun`: 今回選択した系統ページ（実際のHTTP試行件数と一致しない場合がある）
- `profileRetryDelayed`: バックオフ中の未検証系統ページ件数
- `listingPagesMissing`: 一度も収集成功していない一覧ページ番号（歴史的な訪問履歴に基づく）

GitHub Actionsの結果や数値を確認するには最新の `catalog-coverage.json`、`catalog-audit-summary.json`、`catalog-update-state.json` を使ってください。秘密鍵や `.env` はアップロードしないでください。
