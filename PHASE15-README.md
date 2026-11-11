# Phase 15: GitHub Actionsの画像候補検証（安全なドライラン）

## 目的と制限
- GitHub Actionsの通常のキャラクター収集・画像証拠復元・整合性検査・コミット・Hostingは変更しません。
- **手動実行 (`workflow_dispatch`) かつ GitHub Repository Variable `IMAGE_PROBE_DRY_RUN=true` の場合だけ**画像候補の通信検証を追加します。
- 1回につき **最大3件、4秒間隔**。`TECHNOPHERE_REUSE_APPROVED=true` 前提。サイトの最新の利用条件・robots.txtを守ります。
- `--apply` を指定せずJSONを変更しません。実行前後のcatalog内JSONハッシュを比較し、変化があれば停止します。
- HTTP 429時はこの検証ステップを失敗させます（レポートはArtifactに残します）。
- URLが有効なWebPを返してもキャラクターの本人確認にはなりません。**公開データへの自動保存はまだ行いません**。
- 毎回最初の候補を検証するドライランであり、継続的な画像補完ではありません。

## 前提
既存の第12段階 `scripts/catalog_image_backfill.py` および第13・14段階の仕組みがGitHub側にコミット済みであること。

## 適用
```
cp .github/workflows/catalog-update.yml ~/catalog-update-before-phase15.yml
unzip -o ~/Downloads/monst-catalog-phase15-image-probe-patch.zip
python3 -m unittest discover -s scripts -p 'test_catalog_image_probe_gate.py'
python3 -m unittest discover -s scripts -p 'test_catalog_*.py'
git diff -- .github/workflows/catalog-update.yml
```
**ZIPは第14段階の配布ワークフローを基にしています。GitHub上で後から編集している場合は、差分を確認してから統合してください。**

```
git add .github/workflows/catalog-update.yml scripts/catalog_image_probe_gate.py scripts/test_catalog_image_probe_gate.py PHASE15-README.md
git commit -m "ci: add manual read-only image probe"
git status --short
```
未コミット変更がある場合は、バックアップ・stashなどで退避後、`git pull --rebase origin main`、`git push origin main`を実行します。コミットの競合が出たら強制pushせず確認してください。

## GitHub Actionsで手動確認
1. Settings → Secrets and variables → Actions → Variables で `IMAGE_PROBE_DRY_RUN=true`を追加。
2. `AUTO_DEPLOY_HOSTING=false` にし、Actions → Update Technophere catalog → Run workflow を実行。
3. `Phase 15 optional image candidate dry run` と `Upload Phase 15 image probe report` を確認。
4. Artifact `catalog-image-probe-dry-run`から `actions-dry-run.json`をダウンロードして内容を確認。
5. 検証後は `IMAGE_PROBE_DRY_RUN=false` に戻す。ドライランが通常スケジュールで走ることはありません。

## 注意
第11/12段階のローカル画像補完がGitHub上へ安全に復元できているかどうかは第14段階の統合ゲートが判定します。今回の追加は**そのゲートの代わりではありません**。また新規URLを`catalog-image-evidence.json`に追記しません。
