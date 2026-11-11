# 第23段階：解析済み系統の詳細欠損を限定再検証

## 背景
第22段階（2026-11-11収録分）の診断では、95系統中、4系統・6形態に主要フィールドの欠損あり。特にNo.9530,9532,9533,9549のHP/攻撃力/速度、No.177,178のアビリティ。元サイトの全項目が必ず存在するとは限らない。

## 変更
- `scripts/technophere_catalog.py`: `--detail-refresh 1`を指定した際に、**既に検証済みの系統**でHP・攻撃力・スピードまたはアビリティが欠けるものを最大1系統選び、最新版パーサーで再取得する。
- 追加HTTPリクエストを増やさないため、既定のプロファイル枠（5件）のうち**1件を再検証に割り当てる**。残り4件は通常の未検証系統から選ぶ。
- 取得候補は、欠損した主要フィールド数が多い系統を優先。同点ならURL中のID昇順。
- 再確認した系統は`catalog-update-state.json`の`detailRefreshAfterRun`に次回許可runを保存し、56回の収集実行は再確認しない。これはアクセス頻度管理であり、完了認定ではない。
- 部分的な情報を取得しても既存の正しい値は削除しない。HTTP 429に対する既存処理を維持。
- `catalog-coverage.json`に`detailRefreshSelectedThisRun`、`detailRefreshAttemptedThisRun`を追加。
- デフォルトは`--detail-refresh 0`（以前の実行・旧テストは従来の挙動を維持）。
- `scripts/install_phase23_workflow.py`: 既存ワークフローの1行だけにオプションを追加する。第20段階の`--profile-strategy stratified`が存在しなければ失敗させる。**YAML全体は置換しない**。

## 適用
```
git status --short
cp scripts/technophere_catalog.py ~/technophere_catalog-before-phase23.py
cp .github/workflows/catalog-update.yml ~/catalog-update-before-phase23.yml
unzip -o ~/Downloads/monst-catalog-phase23-detail-refresh-patch.zip
python3 -m unittest discover -s scripts -p 'test_catalog_*.py'
python3 scripts/install_phase23_workflow.py
python3 scripts/install_phase23_workflow.py --apply
git diff -- scripts/technophere_catalog.py .github/workflows/catalog-update.yml
```

`git diff`で想定外の変更があれば中止。特に最新版がこのパッチの元となる第21段階のパーサーと異なる場合は差分を手動でマージする。

```
git add scripts/technophere_catalog.py scripts/test_catalog_phase23.py scripts/test_catalog_phase23_workflow.py scripts/install_phase23_workflow.py .github/workflows/catalog-update.yml PHASE23-README.md
git commit -m "feat: bounded refresh of verified families with detail gaps"
```

GitHub Actionsの手動検証時は`AUTO_DEPLOY_HOSTING=false`、定期画像補完を必要なら一時停止。Git同期前に自動生成ファイルの変更をバックアップし、`git pull --rebase origin main`、`git push origin main`を行う。

## 確認
- `profilesAttemptedThisRun <= 5`
- `detailRefreshSelectedThisRun` が0または1（候補と枠に依存）
- `detailRefreshAttemptedThisRun` が0または1
- 既存の`familiesVerified`が意図せず減少していないこと
- 最新の第22段階監査を再実行し、6形態の欠損状況を比較する

**注意**：同じ元サイトを再取得する行為のため、robots.txt、許可条件、アクセス制限を遵守。ステータス・アビリティが本当に存在しない形態は、空欄のままで正しい。再取得できても全形態網羅の証明ではない。Firebase/Firestoreのユーザー保存データには触れない。
