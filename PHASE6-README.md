# 第6段階：収集状況の照合（読み取り専用）

**目的**: 最新のGitHub Actionsが生成したカタログと状態ファイルから、全50ページの残り、未検証系統、画像・詳細の欠損を分離して確認する。外部へのアクセスなし。Firebase/Firestoreや既存JSONを変更しない。

## Macで実行

```bash
python3 -m unittest discover -s scripts -p 'test_catalog_phase6.py'
python3 scripts/catalog_phase6.py public/catalog --state catalog-update-state.json --output local-reports/phase6
```

> 注意: GitHub Actionsが更新する `catalog-coverage.json` をローカルで書き換えません。`local-reports/` を `.gitignore` に追加してください。

## 作成するファイル

- `summary.json`: 全体の件数、未巡回ページ、検証状態、欠損件数
- `missing-listing-pages.csv`: 未巡回の一覧ページ番号
- `family-verification.csv`: 系統URL別の検証状態。`parsed_at_least_once` は全進化形態の網羅を証明しません
- `missing-fields.csv`: 図鑑No.別に未登録項目を列挙
- `invalid-sources.csv`: ソースURLが不正なレコード

## 判断基準

- `listingPagesMissing=[]` は50ページ巡回済みのみを表します（サイトのページ総数が一致していることが前提）。
- `familyStatuses.unverified=0` であっても全進化形態が抽出されたことは証明できません。
- `stateAvailable=false` は比較用の状態ファイルが見つからないため、系統の検証状況を確定できないことを意味します。
- `allFormsProvenComplete` は必ず false です。外部の全形態一覧照合・画像URLのHTTP確認なしに完成宣言をしないための安全措置です。

## GitHubへ反映（任意）

```bash
git add scripts/catalog_phase6.py scripts/test_catalog_phase6.py PHASE6-README.md
git commit -m 'test: add phase6 offline coverage reconciliation'
git pull --rebase origin main
git push origin main
```

**推奨**: 最新の `catalog-coverage.json`、`catalog-update-state.json`、`public/catalog/manifest.json`、`local-reports/phase6/summary.json` を共有し、第7段階で全形態と画像の照合を進める。JSONの個人所持データや認証情報は不要。
