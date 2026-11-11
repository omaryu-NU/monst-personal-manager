# 第14段階：画像証拠と自動収集の整合性ゲート

第13段階のコードがGitHubに反映済みのプロジェクト向けです。**本パッチは画像の取得数を増やしません**。画像証拠の消失、IDの欠落、異なる画像URLによる競合を検出し、問題があれば通常の整合性検査・コミット・Hosting公開の前に停止します。

## 内容
- `scripts/catalog_image_integration_audit.py`：完全オフライン・読み取り専用監査。`--strict`指定時は検査不合格でexit 1。JSONレポートを出力。
- `scripts/test_catalog_image_integration_audit.py`：8件のテスト。
- `.github/workflows/catalog-update.yml`：第13段階のワークフローに「画像統合ゲート」「診断Artifact」を追加。実行順は収集→画像復元→画像統合検査→従来の監査→整合性検査→コミット→Hosting公開。最低1件の証拠が必要。

## 0. バックアップと差分確認

```bash
cp .github/workflows/catalog-update.yml ~/catalog-update-before-phase14.yml
git status --short
unzip -o ~/Downloads/monst-catalog-phase14-integration-gate-patch.zip
git diff -- .github/workflows/catalog-update.yml
```

`git pull --rebase`がローカル変更で失敗する場合、退避内容を確認し、`git stash -u`等で保護してから同期してください。未コミットの図鑑データはバックアップなしで破棄しないでください。

## 1. ローカル検査

```bash
python3 -m unittest discover -s scripts -p 'test_catalog_image_integration_audit.py'
python3 -m unittest discover -s scripts -p 'test_catalog_*.py'
python3 scripts/catalog_image_integration_audit.py --catalog public/catalog --evidence catalog-image-evidence.json --min-evidence 1 --strict --output local-reports/image-integration/local.json
cat local-reports/image-integration/local.json
```

証拠が5件のみなら`evidenceCount: 5`で正常です。**画像補完した10件全部を保護したい場合は、証拠が10件そろうまで後述のインポートを確認してください。**

## 2. 旧画像補完レポートを突き合わせる

第11段階のapply-reportが `local-reports/image-backfill/apply-report.json`、第12段階のapply-reportが `local-reports/image-backfill/phase12-apply.json` にある場合の例です。手元の実際のパスを確認してください。

```bash
python3 scripts/catalog_image_integration_audit.py --catalog public/catalog --evidence catalog-image-evidence.json --applied-report local-reports/image-backfill/phase12-apply.json --strict --output local-reports/image-integration/phase12.json
```

`verifiedReportEntriesMissingFromEvidence`にIDが出た場合は、**同じURLが現在の図鑑にもあることを確認**してから次の既存ツールで取り込みます。

```bash
python3 scripts/catalog_image_evidence.py import --catalog public/catalog --report local-reports/image-backfill/phase12-apply.json --apply
```

第11段階の適用レポートについても同様です。画像が図鑑にない場合はインポートが拒否されます。無理に書き換えないでください。`catalog-image-evidence.json`の更新はGitHubにコミットする必要があります。

## 3. GitHubへ反映

```bash
git add scripts/catalog_image_integration_audit.py scripts/test_catalog_image_integration_audit.py .github/workflows/catalog-update.yml PHASE14-README.md
# 確認後、取り込んだ証拠データがあれば追加
git add catalog-image-evidence.json
git commit -m "ci: gate catalog updates on verified image consistency"
git status --short
# 未コミット変更が無い状態になってから
git pull --rebase origin main
git push origin main
```

`AUTO_DEPLOY_HOSTING=false`にしてGitHub Actionsの`Update Technophere catalog`を手動実行し、`catalog-image-integration-report` Artifactの`passed: true`を確認してください。

## 意味と限界
- `imageURLsPresent`は図鑑に値があるレコード数です。画像のHTTP再検証数ではありません。
- `passed: true`でも画像内容がキャラクターに一致することや全キャラの画像収録を保証しません。
- GitHub Actionsはローカルapply-reportを参照できません。`--applied-report`はローカルで使い、証拠ファイルをGitHubに反映します。
- この監査はJSONとローカルファイルを読むだけで、Firestore・Firebaseの所持キャラ・編成データを変更しません。
