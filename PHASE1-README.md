# Monst Personal Manager — 段階1パッチ（未完成の完成版ではありません）

## なぜ件数が違う？
- GameWith v9: 4,433件（別収集法。完全な母集団と確認されていない）
- Technophere: 公開図鑑に **3,929系統・50ページ** と明記。同一系統の進化形態は1ページに統合。
- アップロードされた自動収集JSON: **1,999件**（50ページのうち一部を巡回し、代表形態のみ保存。全形態を網羅していない）
- 異なる数え方・取得期間・収集漏れが併存し、差分は「GameWithの方が正しい」ことを意味しません。

## このパッチの変更
1. 一覧に表示された撃種(type)・戦型(style)・種族(race)・代表形態(evolution)を保存。
2. 既存データの詳細フィールドと画像を次回更新で消さない。
3. 巡回したページを状態ファイルに累積保存。 `catalog-coverage.json` と `manifest.json.coverage` に可視化。
4. 429の際は次の個別ページへのアクセスを打ち切り、失敗した一覧ページは次回再試行。
5. 毎回 `catalog-audit-summary.json` に画像・アビリティ・詳細取得数を出力し、重複や件数不一致でデプロイを止める。
6. GitHub Actionsで収集前に単体テストを実行。Firebase設定は直前の成功版ワークフローを維持。

## まだ行っていないこと（重要）
- **全形態の個別ページ抽出**、HP/攻撃力/SS/友情などの深い解析、画像のHTTP実在確認と著作物の許諾範囲の照合。
- 429が直近ログで8回出ているため、強制的な連続巡回・アクセス制限回避は行いません。
- `coverage.listingPagesVisited` は「巡回を記録したページ数」であり、全形態や全詳細の網羅率ではありません。
- 進捗が増えるのはGitHub上の定期実行です。このパッチ自体は実運用へ自動反映されません。

## Macで安全に適用
1. GitHub Actionsが進行していないことを確認。可能ならリポジトリの現在の状態をコミット・バックアップ。
2. このZIPを解凍し、中の `.github/` と `scripts/` の該当ファイルを、既存プロジェクト直下に **同じ相対パス** で上書き・追加。
3. `python3 -m pip install -r scripts/requirements-catalog.txt`（未導入の場合）
4. `python3 -m unittest discover -s scripts -p 'test_catalog_quality.py'`
5. `python3 scripts/catalog_progress.py public/catalog --output catalog-audit-summary.json`
6. 変更ファイルを個別に `git add` してコミット・pushする。
7. GitHub Actionsで `Update Technophere catalog` を手動実行、 `catalog-audit-summary.json` と `catalog-coverage.json` が作られたことを確認。

**既存のキャラ所持/編成データやFirestoreに書き込む処理は含めていません。**
