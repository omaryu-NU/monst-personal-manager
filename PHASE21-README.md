# 第21段階：形態別ステータス・アビリティ解析の精度改善

## 目的

第19段階では3,948件中、アビリティ3,838件、HP・攻撃力・スピード各3,842件が欠損していました。未解析系統へのアクセスは既存GitHub Actionsに任せ、今回は**取得済みHTMLの読み取り誤りを減らす**改修です。欠損を一括補完したり、収集アクセス件数を増やしたりするものではありません。

## 内容

- HP/攻撃力/スピードの明示的な列見出しがある場合、列名に対応させて数値を読む。見出しが矛盾する場合は推測せず保留。
- `Lv極`と`Lv120`両方がある場合、`Lv極`を優先。`Lv極`がない数値のみ`Lv120`から補完する。従来と同じ単一値の公開スキーマを維持（レベルごとの複数値は保存しない）。
- 数値と別の文字が混在するセルは採用しない。タス最大値は加算しない。
- 複数列に分かれたアビリティ／ゲージ／コネクトの抽出、および同一項目の重複除去。
- 形態ごとの表を別々に解析し、他形態から値を混ぜない。
- フォーム検証、再試行、HTTP 429、画像証拠、Hosting、Firestore処理は変更しない。

注意：このパッチは**Phase20互換性修正の `technophere_catalog.py` を基礎**にしています。最新GitHub側でその後に編集した場合、解凍で上書きする前に差分を確認してください。

## Macでの安全な適用

1. プロジェクト直下で `git status --short` を確認する。
2. `cp scripts/technophere_catalog.py ~/technophere_catalog-before-phase21.py` でバックアップ。
3. `unzip -o ~/Downloads/monst-catalog-phase21-profile-details-patch.zip`
4. `python3 -m unittest discover -s scripts -p 'test_catalog_phase21.py'`
5. `python3 -m unittest discover -s scripts -p 'test_catalog_*.py'`
6. `git diff -- scripts/technophere_catalog.py` で確認。
7. テスト成功後に次のコードだけをcommit。

```bash
git add scripts/technophere_catalog.py scripts/test_catalog_phase21.py PHASE21-README.md
git commit -m "fix: parse per-form stats by named columns and stabilize level choice"
```

`git pull --rebase origin main` の前に `git status --short` を確認してください。`catalog-coverage.json` が変更されていたら第18段階の `python3 scripts/catalog_local_sync_guard.py --apply` を使用し、バックアップを取ってから同期してください。その他の変更は個別確認。`git push --force`は使用しません。

## GitHub Actionsでの確認

`AUTO_DEPLOY_HOSTING=false`、`IMAGE_BACKFILL_SCHEDULED=false` として手動実行し、全テスト、収集、画像統合ゲート、構造チェックが成功することを確認します。改善の効果は収集後の新しい `catalog-audit-summary.json` と `catalog-coverage.json` を以前と比較して評価します。

## 検証範囲と限界

- 新規11テスト成功。第20段階のライブ取得順序・互換性テスト14件も合わせて25件成功（作成時の環境）。
- これは合成HTMLによる単体テストです。Technophereの最新HTML全体を取得して網羅検証したわけではありません。
- 明示的列見出しがない表は、従来の3列順序を仮定します。列順不明の古いHTMLに対する完全性は保証されません。
- 今回のコードは既存の`hp/attack/speed`の意味を`Lv極`優先に統一します。既に別レベルの数値で上書きされたレコードについては次回の個別ページ再解析後に改善されます。
- 全進化形態の網羅性は未証明であり、未解析系統の収集は引き続き必要です。
