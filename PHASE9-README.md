# 第9段階：画像URL・詳細抽出の安全性改善

基礎：第8段階 `scripts/technophere_catalog.py`。ZIPにはコードと新規テストのみ含みます。`public/catalog`、state、Firebase設定は含みません。

## 改善した点

1. 画像候補として `data-src`、`data-lazy-src`、`data-original`、`src`、`srcset`、`data-srcset` を参照。
2. 同じ形態ブロック内で、画像URLの**ファイル名（拡張子なし）が図鑑No.に完全一致**し、元サイトのHTTPS画像である場合にのみ採用。ロゴや他形態の画像を誤って保存しない。
3. `Lv極` / `Lv120` ステータス表のHP・攻撃力・スピードを取り出し、`タス最大値`は混ぜない。
4. アビリティ／ゲージ／コネクト／SS／友情コンボの表ラベルの一部表記ゆれに対応。
5. 既存の画像・詳細情報は、今回の取得が不完全でも削除しない。

## 適用前

VSCodeのプロジェクト直下で `git status --short` と `git pull --ff-only origin main`。未コミット変更がある場合は先に退避／保存し、同期できてから解凍する。

```bash
unzip -o ~/Downloads/monst-catalog-phase9-details-patch.zip
python3 -m pip install -r scripts/requirements-catalog.txt
python3 -m unittest discover -s scripts -p 'test_catalog_*.py'
git add scripts/technophere_catalog.py scripts/test_catalog_phase9.py PHASE9-README.md
git commit -m 'fix: match form images by id and improve stat extraction'
```

**push前の推奨手順**： `git status --short` で生成ファイルの変更を確認し、必要ならバックアップしてから `git stash push -m 'generated files before sync' -- catalog-coverage.json catalog-audit-summary.json` のように対象を限定して退避する。続けて `git pull --rebase origin main` → `git push origin main`。競合時は作業を止め、無理にforce pushしない。

GitHub Actionsの `AUTO_DEPLOY_HOSTING=false` でまず手動収集を検証。 `catalog-coverage.json` と `catalog-audit-summary.json` の画像・詳細数を前回と比較。データが検証された後で公開再開。

## 制限

- 個別ページの取得数は現行ワークフローの制限（例: 5件/実行）に依存します。今回はリクエスト数を増やしていません。
- 実Web HTMLの完全なテストはできていません。形態ブロックのレイアウトが異なると抽出できない可能性があります。
- URLが画像を返すか（HTTP/画像内容）、その画像がキャラ本人か、網羅率は未検証です。
- リンク先サイトのアクセス制限・許可を尊重してください。HTTP 429の停止・再試行制御は既存コードを維持しています。
