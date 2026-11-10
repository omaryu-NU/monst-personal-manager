# Technophere図鑑マスター：導入・運用

既存のMonst Personal Manager v1.0を拡張したものです。ユーザーの `monst-personal-v1`、Firestore保存パス、所持個体ID・編成ID・JSONバックアップには変更を加えません。

## 重要な権利確認
GameWithおよびMIXIの許可はTechnophereのデータ・画像・定期収集・再配信の許可とは別です。Technophereから取得・再利用・再配布・画像の埋め込みまたは配信・自動巡回に必要な許可を得た場合に限り、GitHubのRepository Variablesに `TECHNOPHERE_REUSE_APPROVED=true` を登録してください。利用規約・robots.txtも確認します。ソースサイトへのDoS対策として取得間隔と上限を設けています。アクセス制限を回避する処理はありません。

## 初回準備

```bash
python3 -m pip install -r scripts/requirements-catalog.txt
TECHNOPHERE_REUSE_APPROVED=true python3 scripts/technophere_catalog.py --pages 5 --profiles 15 --delay 1.5
npm install
npm test
npm run build
```

初回は最新ページ＋既存ページ4枚の一部のみです。以前の4,455件のGameWithデータを自動転用しません。図鑑マスターが空の場合はローカル図鑑を使います。アクセス不可や構造変化で0件となれば既存JSONを保持し、公開済みデータを全削除しません。

## GitHub Actions（3時間間隔）

1. v1.0の既存GitHubリポジトリへこの差分をコミットしてプッシュします。GitHub Actionsのスケジュールは**デフォルトブランチ**上のworkflowからのみ動きます。
2. GitHub Repository Settings > Secrets and variables > Actions > Variables: `TECHNOPHERE_REUSE_APPROVED=true`（許可取得後）
3. Actions > Update Technophere catalog > Run workflow で初回確認。
4. 毎日UTCの00:17、03:17、06:17、...に更新を試みます。スケジュールは遅延・スキップされる場合があります。5ページを巡回し、新着を優先して最大15件のプロフィールを検査します。
5. 更新成功時は `public/catalog/manifest.json` と分割JSON・`catalog-update-state.json` をコミットします。個人Firestoreは変更しません。
6. Firebase Hostingまで自動公開する場合は、追加でRepository Variables `AUTO_DEPLOY_HOSTING=true` と `FIREBASE_PROJECT_ID`、Repository Secret `FIREBASE_SERVICE_ACCOUNT`（最小権限のサービスアカウントJSON）を設定してください。設定しなければGitHubだけが更新されるので、Hostingへは手動デプロイが必要です。

### GitHub実行時の注意
Actionsの書込権限を許可（Settings > Actions > General > Workflow permissions）してください。GitHub Actionsの定期実行はリポジトリが長期間非アクティブの場合停止する場合があります。頻繁なコミットを避けたい場合は実行・コミット条件を変更してください。

## データ仕様
`public/catalog/manifest.json`がチャンク一覧です。`characters-NNNN.json`は200件ずつ。サイト側の1/50ページ表示は「系統」の件数で、すべての進化形態のレコード数ではありません。技術的には現行コードは一覧の代表形態だけを収録し、すべての形態やHP/SSなどの完全収集には別工程が必要です。画像は実ページに見つかったときだけURL登録。画像ファイルをZIPに保存しません。

画面では外部図鑑を読み取り専用として表示し、所持登録時のみ選択したキャラの最小スナップショットを既存の個人データへ追加します。こうして既存のID参照を保ったまま、マスターを巨大なFirestore文書へ保存することを避けます。外部図鑑の読み込みに失敗した場合は従来のローカル図鑑にフォールバックします。

## ロールバック
旧版ZIPに戻す。外部図鑑は独立ファイルのため、Firestoreの保存形式やIDを移行する必要はありません。更新前にJSONバックアップを取得してください。画像・属性は出典元の内容を確認して利用してください。

## 未検証項目
実サイトへの定期収集、GitHub Actionsの実行、Firebaseの本番自動デプロイ、iPhone/Androidでの表示はこの環境では実施していません。これらは成功と報告しません。
