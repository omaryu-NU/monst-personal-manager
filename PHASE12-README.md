# Phase 12: 画像補完の進捗管理と失敗再試行

## 課題と修正
- Phase11 は `cursor` を「画像未登録レコードの並び順」に対して保持。成功した候補が未登録一覧から消えるため、次回 `cursor=5` から開始すると、その次の5件を飛ばすことがありました。
- Phase12 は **図鑑No.（`lastProcessedID`）** を保存し、候補を図鑑No.昇順で並べます。既存 Phase11 状態ファイル（`{"cursor":5}` など）は自動認識し、未登録候補の先頭から安全に再開します。
- HTTP 404、画像形式違いなどは `retry` に失敗理由と再試行予定の「実行回数」を記録。最短2実行分の間隔を置き、最大32実行分まで延長します。
- HTTP 429 の場合は停止し、制限された候補は失敗として確定せず、次回改めて確認します。
- デフォルトはドライラン。`--apply` を明示した場合のみ、通信でWebP応答を確認したURLを `public/catalog/characters-*.json` に追加します。
- Firebase/Firestore、所持キャラ、編成データは変更しません。自動GitHub Actions組み込みも行いません。

## 適用前

1. プロジェクト直下の作業変更を `git status --short` で確認し、必要に応じてバックアップ。
2. `public/catalog/` と `local-reports/image-backfill/state.json` の現在の内容を保存。特にGitHub Actionsとローカルの図鑑JSON更新が競合しないようにしてください。
3. パッチをプロジェクト直下に解凍。 `scripts/catalog_image_backfill.py` は第11段階版から更新されます。第11段階の既存単体テストはそのまま使えます。

## コマンド

```bash
unzip -o ~/Downloads/monst-catalog-phase12-backfill-resume-patch.zip
python3 -m unittest discover -s scripts -p 'test_catalog_image_backfill.py'
python3 -m unittest discover -s scripts -p 'test_catalog_phase12.py'

# 最初は読み取り専用。オンラインアクセスは最大5件、間隔3秒。
TECHNOPHERE_REUSE_APPROVED=true python3 scripts/catalog_image_backfill.py public/catalog \
  --online-limit 5 --delay 3 --output local-reports/image-backfill/phase12-dry-run.json

# 内容を確認し、許可条件を守って適用する場合のみ実行。
TECHNOPHERE_REUSE_APPROVED=true python3 scripts/catalog_image_backfill.py public/catalog \
  --online-limit 5 --delay 3 --apply --output local-reports/image-backfill/phase12-apply.json

# 保存後の図鑑全体を再確認
python3 scripts/catalog_image_audit.py public/catalog --output local-reports/image-audit-after-phase12
cat local-reports/image-audit-after-phase12/summary.json
```

## 変更ファイル
- `scripts/catalog_image_backfill.py`（上書き）
- `scripts/test_catalog_phase12.py`（追加）
- `PHASE12-README.md`（追加）

## git

```bash
git add scripts/catalog_image_backfill.py scripts/test_catalog_phase12.py PHASE12-README.md
git commit -m "fix: resume image backfill by stable character ID"
git status --short
# ワークツリーが安全に同期できる状態になってから
git pull --rebase origin main
git push origin main
```

**注意**: `public/catalog/characters-*.json` はローカル適用時に更新されますが、GitHub Actionsが同じファイルを自動更新します。競合を避けるため、今回のコードコミットに図鑑JSONを含めないでください。未コミットの図鑑JSONの変更を破棄する前に、必ずバックアップを取ってください。補完した画像を公開図鑑に確実に反映するには、収集ジョブと補完ジョブの一元的な統合が別途必要です。

## 検証範囲
- ローカルのモックHTTP応答を使う第11段階6件＋第12段階5件、合計11テスト合格。
- 実際の本番データ3928件に対するマージ検証、画像内容のキャラクター一致検証、GitHub Actions連携は未実施。
- `state.json` の `cursor` → `lastProcessedID` 移行後は、成功済み図鑑No.が JSON に残っていれば重複アクセスしません。
