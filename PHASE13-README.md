# Phase 13: 画像補完の証拠とGitHub Actionsとの安全な連携

## 検証結果
- Phase12 追加5件 (134,138,142,146,150)、保存後の画像URL合計70件。オンライン5件成功・HTTP429なし。
- **全70件が画像内容まで正しいことはまだ保証できません**。すべての画像URLは技術的検査の結果で、画像内容の同一性は別の検査が必要です。
- Phase13 新規単体テスト6件成功。実際の GitHub Actions 更新は未実施。

## 目的
- ローカルでHTTP200 + WebPファイル署名を確認したURLを、図鑑チャンクとは独立した `catalog-image-evidence.json` に保存します。
- スクレイパーが `characters-*.json` を再生成した後でも、証拠に記録されたURLだけをオフラインで復元できます。
- 不一致がある場合は例外で止め、データを勝手に上書きしません。
- Firestoreやユーザーの所持・編成には一切アクセスしません。画像URL自体はTechnophereのホスト名/図鑑No.一致を検査します。

## 1. バックアップ
作業ディレクトリ（リポジトリ直下）で `git status --short` を確認し、ローカル画像補完を反映済みの `public/catalog` と `local-reports/image-backfill` をバックアップしてください。`git pull` や `git restore` で未コミットの画像差分が消えないようにします。**この段階では図鑑チャンクの変更をコミットしない**方針です。

## 2. 最新の図鑑JSONと適用レポートの照合
```bash
unzip -o ~/Downloads/monst-catalog-phase13-image-evidence-patch.zip
python3 -m unittest discover -s scripts -p 'test_catalog_image_evidence.py'

# 第12段階で5件を適用済みの図鑑JSONを使います。
python3 scripts/catalog_image_evidence.py import --catalog public/catalog \
  --report local-reports/image-backfill/phase12-apply.json

# 「newEvidence:5」が示されても、この時点では書き込みなしです。
python3 scripts/catalog_image_evidence.py import --catalog public/catalog \
  --report local-reports/image-backfill/phase12-apply.json --apply
```
**注意**: apply-report の画像URLが現在の図鑑JSONに存在しなければ、安全のため `ValueError` で止めます。先に `git pull` や Actions 実行で画像が消えていたら、復元前のローカルJSONのバックアップから調べてください。成功したとの記録だけで存在しないURLを無条件に投入しません。

第11段階の5件 (112,114,116,118,120) も反映済みであれば、同様に元の `local-reports/image-backfill/apply-report.json` を読み込み、`import --report <path> --apply` を実行します。このレポートがない場合は第11段階の5件を取り込めないので、無理に仮のレポートを作らないでください。

## 3. 証拠ファイルの適用前チェック
```bash
python3 scripts/catalog_image_evidence.py replay --catalog public/catalog
python3 scripts/catalog_image_evidence.py replay --catalog public/catalog --apply
python3 scripts/catalog_image_audit.py public/catalog --output local-reports/image-audit-phase13
```
画像URLがすでに一致していれば `toRestore` は0です。ローカルでURLを削除してみるなどのテストは、**必ず図鑑JSONのコピー上**で行ってください。

## 4. コミット（証拠だけ）
```bash
git add scripts/catalog_image_evidence.py scripts/test_catalog_image_evidence.py PHASE13-README.md catalog-image-evidence.json
git commit -m "feat: preserve HTTP-verified catalog image evidence"
```
`public/catalog/characters-*.json` は add に含めません。別のコミットで増えた GitHub Actions の図鑑との差分競合を避けるためです。

## 5. 自動収集と連携（ワークフロー編集は手動で）
**今回のZIPは `.github/workflows/catalog-update.yml` を変更しません。** 既存ワークフローを直接確認できていないため、まずGitHubにパッチを送ってから現在のワークフローを確認してください。

元の自動スクレイピングが完了した後、**既存の整合性検査とコミットの前**に次のステップを挿入します。

```yaml
- name: Restore HTTP-verified catalog image URLs
  run: |
    python3 scripts/catalog_image_evidence.py replay \
      --catalog public/catalog \
      --evidence catalog-image-evidence.json \
      --apply \
      --output local-reports/image-evidence/actions-replay.json
```

これにより、スクレイピングが画像を消しても、今回証拠に登録した画像だけが復元されます。既存画像に別URLがあるとエラーで止まるため、手動の確認が必要です。

**重要**: このステップは、`catalog-image-evidence.json` がコミット済みであることが前提です。ワークフローの環境が `local-reports` を無視する設定なら、生成された診断ファイルはコミット対象にしないでください。GitHub Actionsの手動実行時は `AUTO_DEPLOY_HOSTING=false` にして検証してください。

## 6. 検査結果の読み方
- `newEvidence`: 証拠ファイルに新規登録する件数
- `totalEvidence`: 証拠ファイルに保持する画像件数（最大70件にはまだ達しない場合があります）
- `toRestore`: 証拠はあるが、現在の図鑑JSONには画像が無いため復元できる件数
- `missingCatalogIDs`: 現在の図鑑に存在しないID。キャラを自動生成しません
- `conflicts`: 異なる画像URLがあれば停止し、上書きしません

**制限事項**: これは過去のHTTP検証結果の保存・再適用です。画像URLが後日404になることも、画像が別キャラに変わることも検出しません。画像内容の目視・別ソースとの照合も別途必要です。
