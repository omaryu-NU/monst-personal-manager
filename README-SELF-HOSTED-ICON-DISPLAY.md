# Monst Personal Manager：自サイト画像を図鑑へ安全に表示

## 目的
GitHub Actionsで取得し `public/character-icons/manifest.json` に登録した画像だけを図鑑カードに表示する。画像がない/読めない場合はキャラ名の先頭文字を表示。既存の検索・フィルタ・所持管理・編成・Firebaseを変更しない。

## 重要
- **既存の `src/CatalogBrowser.tsx` をZIPで上書きしません。** 小さなインストーラーが現行ファイルの1か所だけを置換します。想定外のコードならエラーで停止します。
- `src/SelfHostedCharacterIcon.tsx` は新規追加です。
- ブラウザからTechnophere画像を直接参照しません。ローカルの `manifest.json` に存在する画像だけ表示します。
- 図鑑詳細モーダルの大きなイラストは今回の対象外です。
- **Gitにコミットするのはテストとビルドが成功した後**にしてください。

## 手順（Mac、VSCodeのプロジェクト直下）

```bash
# 1. 現状でビルドが通るか確認
npm run build

# 2. このZIPを解凍（CatalogBrowser.tsx自体はZIPに含まれません）
unzip -o ~/Downloads/monst-self-hosted-icon-display.zip

# 3. 変更予告（実際のファイルはまだ書き換えません）
python3 scripts/connect_self_hosted_icons.py

# 4. 既存画面をバックアップし1か所だけ修正
python3 scripts/connect_self_hosted_icons.py --apply

# 5. テスト・ビルド
python3 -m unittest discover -s tests -p 'test_connect_self_hosted_icons.py'
npm run build

# 6. 差分チェック
git diff -- src/CatalogBrowser.tsx
git status --short
```

ビルド失敗時は **pushしない**でください。バックアップは `src/CatalogBrowser.tsx.before-local-icons.bak` に残ります。復旧は `cp src/CatalogBrowser.tsx.before-local-icons.bak src/CatalogBrowser.tsx`。バックアップを作り直す前に原因を確認してください。

確認できた場合のみ：

```bash
git add src/CatalogBrowser.tsx src/SelfHostedCharacterIcon.tsx scripts/connect_self_hosted_icons.py tests/test_connect_self_hosted_icons.py README-SELF-HOSTED-ICON-DISPLAY.md
git commit -m "fix: render self-hosted character icons in catalog"
git status --short
# 未コミットの追跡済み変更を別途整理した後に同期
git pull --rebase origin main
git push origin main
```

`AUTO_DEPLOY_HOSTING=true`で図鑑更新用ActionsのHostingデプロイが成功すれば本番反映。ブラウザを再読込して確認。GitHub Actions「Import approved character icons」は別のワークフローで毎日最大10枚を追加します。

## 自動で全キャラ揃うか
**現時点では揃いません。** 最後の実行では画像URL候補306件・取得成功10件。図鑑は約4,032件なので、大半は画像URL候補さえありません。対象の候補数が増えなければ、306件を取り終わった後は自動収集対象がなくなります。また10枚/日では306件でも約31日が理論上の下限です。GitHub Actionsの定期実行とHosting公開の成功が条件です。Technophereの利用許可を保持したまま、未登録IDの画像URL発見ロジックを別途改善する必要があります。
