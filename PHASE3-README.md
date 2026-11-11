# Phase 3: 図鑑の検証済み判定の信頼性を向上

## 目的と注意

- 第2段階では個別ページから少なくとも1形態を取得できれば、その系統を `verifiedFamilyURLs` に記録していました。実際の代表形態と無関係な部分だけを抽出しても、次回以降の再試行対象から外れてしまう問題があります。
- このパッチは、一覧で確認した図鑑No.の少なくとも1件が個別ページの抽出形態に含まれることを検証した後でのみ検証済みとします。
- 以前の状態ファイルには確認済み図鑑No.の一覧がないため、従来の「検証済み」URLは再検証の対象に戻します。これは正常な挙動です。**全形態の完全取得が証明されたことを意味しません。**
- 新しく `verifiedFamilyFormIDs` と `unmatchedRepresentativeProfilesThisRun` を状態ファイル・カバレッジに記録します。
- 画像URLは未検証です。収集先サイトから429が返る場合はアクセスを打ち切り、実行頻度を高めて突破しません。

## 適用手順（Mac / VSCode、プロジェクトのルートにて）

1. `git status` で未コミット変更を確認し、必要なら先にコミット。
2. `git pull --ff-only origin main`。GitHub Actionsが先行コミットしていれば追従する。
3. ZIPをプロジェクト直下で解凍：`unzip -o ~/Downloads/monst-catalog-phase3-validation-patch.zip`
4. `python3 -m pip install -r scripts/requirements-catalog.txt`
5. `python3 -m unittest discover -s scripts -p 'test_catalog_*.py'` （9 tests OKが目安）
6. `git add scripts/technophere_catalog.py scripts/catalog_progress.py scripts/test_catalog_phase3.py PHASE3-README.md`
7. `git commit -m 'fix: validate representative forms before marking family verified'`
8. `git pull --rebase origin main`、問題なければ `git push origin main`。
9. GitHub Actionsの「Update Technophere catalog」を手動実行。最初は `AUTO_DEPLOY_HOSTING=false` にして、catalogの差分とレポートを確認することを推奨。
10. `catalog-audit-summary.json` の `progress`、`catalog-coverage.json` の `familiesRemaining` と `unmatchedRepresentativeProfilesThisRun` を確認。

## 完了条件

- `listingPagesVisited == totalPages`（全一覧ページ巡回済み）
- `familiesRemaining == 0`（全発見系統の最低1形態を検証済み）
- 画像や詳細フィールドの充足率を別に確認（上記2条件でも全形態の網羅は未証明）

## 運用上の注意

プログラムはGitHub Actionsの既存設定を使います。Firestore、ユーザーの所持キャラ・編成情報を直接変更するコードは含みません。状態と図鑑JSONの更新は既存ワークフローがコミットします。
