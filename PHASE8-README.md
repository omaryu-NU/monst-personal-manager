# 第8段階：個別ページの形態解析欠損を検知する

## 背景
2026-11-11に共有された状態ファイルでは一覧25/50ページ、発見済み3,589系統、解析済み15系統です。これは第7段階適用前のスナップショットであり、最新のGitHub状態とは限りません。

個別ページに2形態の見出しが存在し、片方しか図鑑No.を解析できない場合、従来は1形態でも取得できると系統を検証済み扱いにしてしまいました。

## 改修内容
- 形態ごとのステータスとアビリティ節の認識可能な h3 見出し数と、抽出できたユニークID数を比較する。
- 数が一致しない場合、抽出できた正しいレコードは保持したまま、その系統は検証済みにせず次回以降再試行する。
- `catalog-coverage.json` の `incompleteFormSectionsThisRun` に未完成解析件数を出力する。
- HTTP429での停止、アクセス間隔、個別ページの処理件数は変更しない。

**限界**：この検査は認識可能な見出しの取りこぼしを検出するもので、サイト内の全形態が揃ったことの証明ではありません。見出し表記そのものが未知の場合などは検出できません。画像のHTTP実在確認・詳細情報の完全性も別工程です。

## 適用前
`git status` で未コミットの変更を確認し、必要ならバックアップ。自動公開はまず `AUTO_DEPLOY_HOSTING=false` で検証。

## 適用
ZIP内の `scripts/technophere_catalog.py` と `scripts/test_catalog_phase8.py` をプロジェクトの対応する場所へコピー。既存の `.github` 設定・状態ファイル・公開JSONは含まれません。

```
python3 -m pip install -r scripts/requirements-catalog.txt
python3 -m unittest discover -s scripts -p 'test_catalog_*.py'
git add scripts/technophere_catalog.py scripts/test_catalog_phase8.py PHASE8-README.md
git commit -m "fix: retry profiles with incomplete form sections"
git pull --rebase origin main
git push origin main
```

## 実行後確認
GitHub Actionsの `catalog-coverage.json` の `incompleteFormSectionsThisRun` 、 `familiesVerified` 、 `familiesRemaining`、`listingPagesRemaining` を確認。新たに未完全と判定された系統は検証済みに数えない。既存の `verifiedFamilyURLs` については本パッチは再検査を強制しないため、**過去の検証済みすべてが完全だとはまだ言えません**。
