# 第5段階：収録データの整合性ゲートと進捗レポート

このパッチは **オフラインの品質検査のみ** を追加します。Technophereへの追加アクセス、Firestoreの変更はしません。

## 手順

1. プロジェクト直下にZIPを解凍
2. `python3 -m unittest discover -s scripts -p 'test_catalog_integrity.py'`
3. `python3 scripts/catalog_integrity.py public/catalog --output catalog-integrity-report`
4. `python3 scripts/install_phase5_workflow.py`（既存GitHub Actions YAMLにチェックと成果物保存を追加）
5. `git diff -- .github/workflows/catalog-update.yml` で既存Hosting処理が残っているか確認
6. `git add scripts/catalog_integrity.py scripts/test_catalog_integrity.py scripts/install_phase5_workflow.py .github/workflows/catalog-update.yml PHASE5-README.md`
7. `git commit -m 'test: gate corrupt catalog and publish integrity report'`
8. `git pull --rebase origin main && git push origin main`（競合時は中断して確認）
9. Actionsを手動実行し、Artifactsの`catalog-integrity-report`をダウンロード

## 安全性と注意

* **構造的な破損**（件数不一致・重複ID・不正な属性等）は終了コード1で停止し、commitやHostingデプロイより前にブロックします。
* **欠損は報告のみ**（画像やアビリティの不足で既存サイトを止めない）。このパッチだけでは不足データは埋まりません。
* HTML取得・画像URLのHTTP検証・全キャラ照合は実施しません。全50ページの巡回率はmanifestの保存済みcoverageから判断します。
* Actionsへの変更は既存YAMLの `Commit validated catalog` ステップ直前に挿入するので、Firebase Secretsや通常の公開処理は変更しません。
* `catalog-integrity-report/` はローカルで生成されるのでGitにコミットしないでください。`.gitignore`にこのフォルダを追加することを推奨します。
* 次は最新の `catalog-coverage.json` / `catalog-audit-summary.json` / report summary を用いて、残ページ・未検証系統の検査と全形態の照合を進めます。
