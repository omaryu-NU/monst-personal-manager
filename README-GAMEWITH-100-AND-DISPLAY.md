# GameWith画像：UTC日付あたり最大100件の取得試行と図鑑表示

既存のGameWith画像ワークフローの取得上限を10→100に変更。再手動実行時に日別上限を超えにくくするため、UTC日付の試行数を`public/character-icons/gamewith-daily-budget.json`に保存し、画像と同時にコミットします。日次cronは既存の`12 7 * * *`（UTC）のまま。遅延3秒は維持、ワークフロータイムアウトは60分。

**注意：** 100件/日とはHTTP取得の最大試行数です。100枚の保存成功を保証しません。GitHub Actionsが異常終了して日別台帳をpushできなかった場合、再実行時に上限を厳密に保証することはできません。追加で実行しないでログを確認してください。取得頻度は利用許可・配信元の負荷条件の範囲にとどめてください。

図鑑画面には`SelfHostedCharacterIcon`を使います。画像は`/character-icons/manifest.json`で一致した図鑑No.の**自サイト画像のみ**を使用し、未登録なら名前の先頭文字。既存検索・フィルタ・Firebase保存を変えません。ブラウザが古いページを開き続けている場合、更新してください。

## 適用

1. 既存プロジェクト直下で `git status --short` を確認。未コミット変更は保護してください。
2. `unzip -o ~/Downloads/monst-gamewith-100-daily-site-display.zip`
3. `python3 scripts/setup_gamewith_100_and_icons.py` （**プレビュー**）
4. `python3 scripts/setup_gamewith_100_and_icons.py --apply`
5. `python3 -m unittest discover -s tests -p 'test_gamewith_daily_icons.py'`
6. `npm run build`
7. `git diff -- .github/workflows/gamewith-approved-icons.yml src/CatalogBrowser.tsx`
8. `git add .github/workflows/gamewith-approved-icons.yml src/CatalogBrowser.tsx src/SelfHostedCharacterIcon.tsx scripts/import_gamewith_daily.py scripts/setup_gamewith_100_and_icons.py tests/test_gamewith_daily_icons.py README-GAMEWITH-100-AND-DISPLAY.md`
9. `git commit -m 'feat: import up to 100 GameWith icons daily and show local icons'`
10. `git status --short`、同期後`git push origin main`。`git pull --rebase` は未コミットの追跡済みファイルがあると失敗します。必ずバックアップ・差分確認してください。強制pushしないでください。
11. `GAMEWITH_ICON_IMPORT_ENABLED=true` と `AUTO_DEPLOY_HOSTING=true` を確認し、GameWith用ワークフローを手動実行。成功と新規画像のコミットを確認。
12. **画像登録ワークフローにはHostingデプロイがありません。** `Update Technophere catalog`ワークフローを実行し`Build React app`および`Deploy Hosting only`成功を確認。本番図鑑を再読み込み。

## 詳細

- セットアップスクリプトは`CatalogBrowser.tsx`内の既知のアイコン要素だけを置換します。すでに変更済みなら冪等です。想定外のコードではエラー停止します。
- `src/SelfHostedCharacterIcon.tsx`がある場合は上書きしません。ない場合は付属テンプレートをコピーします。
- 修正前の追跡ファイルは`*.before-gamewith100.bak`へバックアップします。このバックアップはGitに追加しないでください。
- GameWith用画像登録は`img.gamewith.jp`だけ許可。HTTP 403の回避や画像以外のデータの保存はしません。
- `GAMEWITH_ICON_IMPORT_ENABLED=true`でもスケジュールの自動実行が動くことはFirebase Hostingのデプロイ成功を意味しません。Hostingは別の図鑑ワークフローで実施されます。
