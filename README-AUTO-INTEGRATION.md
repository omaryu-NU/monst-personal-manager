# Monst Personal Manager：画像候補の自動生成→自サイト配信

このパッチは**既存のキャラ一覧画面、図鑑データ、Firestoreを変更しません**。

## 何が自動になるか

- 既存 `public/catalog/manifest.json` と `characters-*.json` を読み、画像URLが登録されている図鑑No.から `config/approved-icon-sources.csv` を自動生成
- `APPROVED_ICON_IMPORT_ENABLED=true`なら1日最大10件だけ画像データを検証し、`public/character-icons/`に登録
- 403画像は30日間再試行を控え、GitHub Actionsのレポートに記録。拒否された画像を回避して取得しません
- 追加画像、マニフェスト、候補CSVをGitHubにコミット。既存 `catalog-update.yml` による次回Hosting公開後にサイトへ反映
- すでに登録したNo.は再取得しない

**制限**: この処理は、図鑑JSONに既に明示された画像URLだけから候補を作ります。画像URLのない残り数千キャラのURLは推測しません。Technophereの画像配信元が403を返す場合、画像は保存されません。許可済みファイル配布・ダウンロード可能な配信経路を提供元に確認してください。403を回避するヘッダー偽装・Cookie・プロキシは入っていません。

## 前提

前回の画像表示パッチの `src/local-character-icons.ts` と `src/technophere-feed.ts` が正常に統合済みであること。`CatalogBrowser.tsx`はパッチ適用前の版に戻して `npm run build`が通ること。画面に壊れた画像が残る場合は表示側を別途調整する必要があります。

## 適用（プロジェクト直下）

```bash
npm run build
unzip -o ~/Downloads/monst-icon-auto-integration.zip
python3 -m unittest discover -s tests -p 'test_auto_import_approved_icons.py'
python3 -m unittest discover -s tests -p 'test_generate_icon_candidates.py'
# 既存の図鑑から候補を作る（ネットアクセスなし）
python3 scripts/generate_icon_candidates.py --catalog public/catalog \
  --csv config/approved-icon-sources.csv \
  --host game.technophere.com \
  --permission-reference 'owner-declared-Technophere-image-reuse-authorization'
# 取得前の検証（ネットアクセスなし）
python3 scripts/auto_import_approved_icons.py --csv config/approved-icon-sources.csv \
  --allow-host game.technophere.com
npm run build
```

生成されたCSVにはユーザー自身が宣言した許可についての識別子を記録しています。契約書等の証拠を自動確認した意味ではありません。

## GitHub Actions

新しい `.github/workflows/approved-icons.yml` を追加・更新します。`catalog-update.yml`は変更しません。

既存Variablesは

- `APPROVED_ICON_HOST=game.technophere.com`
- `APPROVED_ICON_IMPORT_ENABLED=false`（初回は維持）
- `TECHNOPHERE_REUSE_APPROVED=true`
- `AUTO_DEPLOY_HOSTING=true`

手動で `Import approved character icons` を実行した場合、falseでは候補生成+ドライラン+レポートだけ実施し、画像を取得しません。レポート `approved-icons-report` を確認してください。

画像の直接URLが403を返さないことを提供元と確認できたら、`APPROVED_ICON_IMPORT_ENABLED=true`へ変更できます。1日最大10件、403は30日待機します。

画像が登録された後、通常の`Update Technophere catalog`の次回Hostingデプロイが成功すれば、`https://monst-personal-manager.web.app/character-icons/<番号>.webp`等で確認できます。Hostingへの即時反映ではありません。

## Git操作

```bash
git status --short
git add .github/workflows/approved-icons.yml scripts/generate_icon_candidates.py scripts/auto_import_approved_icons.py \
  tests/test_generate_icon_candidates.py tests/test_auto_import_approved_icons.py \
  config/approved-icon-sources.csv README-AUTO-INTEGRATION.md
git commit -m "feat: queue approved icons from catalog and import safely"
# git pull --rebase は追跡済み未コミット変更が無いことを確認してから
git pull --rebase origin main
git push origin main
```

GitHub Actionsで増えた画像を大量にGitへ記録すると容量が膨らみます。大規模になった場合はFirebase Storage/CDNへの移行を検討してください。

## 安全性

- 著作権利用条件とサイトからのHTTPアクセス許可は別。
- 画像の再配布可能範囲は権利者との合意に従う。
- 図鑑No.と画像ファイル名が一致するもののみ採用。
- Firestoreのユーザーデータは編集しない。
- 403・404・形式不一致は登録しない。403のみ長期クールダウン。
