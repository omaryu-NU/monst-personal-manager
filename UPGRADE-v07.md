# v0.6 → v0.7 安全なアップデート

## 重要：上書きする前に

1. 公開中の **v0.6** を開き、**設定・同期 → JSONバックアップ** から全データを保存する。
2. クラウドの同期完了を確認する。オフライン編集がある場合は同期またはJSONバックアップを優先する。
3. v0.6 のフォルダ全体をコピーする。既存の Firebase データは削除しない。
4. v0.7 ZIP を解凍し、v0.6 の `.env` と `.firebaserc` をコピーする（`.env` は公開しない）。

## インストール・テスト

```bash
npm install
npm test
npm run build
npm run dev
```

**ビルドが失敗したらデプロイしないこと。** フォルダ名が `monst-personal-manager-v07` になっていることを確認する。

## Firestore セキュリティルール

v0.7 は `users/{UID}/data/playLogs` に新しいプレイ履歴セクションを作成する。v0.6 の Firestore セクション、リビジョン方式、古いローカル保存キー `monst-personal-v1` はそのまま保持する。

```bash
npx firebase-tools use --add
npx firebase-tools deploy --only firestore:rules
```

`use --add` は未設定のときのみ実行。`.firebaserc` のプロジェクトIDと `.env` のプロジェクトIDを必ず一致させる。

**新旧データ保護:** `schemaVersion` は `1` のまま。v0.6 にない `playLogs` は読み込み時に `[]` に補完する。既存 ID や編成スロット参照を書き換えない。旧 `users/{UID}/private/state` は引き続き読み取り専用。

### Emulator 統合テスト

```bash
npx firebase-tools emulators:exec --project demo-monst-personal-v07 --only auth,firestore "npm run test:emulator"
```

実際の Firestore に接続するものではない。Java と Firebase CLI、Firebase SDK のインストールが必要。

## 公開

```bash
npm run build && npx firebase-tools deploy --only firestore:rules,hosting
```

## Mac・スマホ実機テスト

1. v0.6 と同数の所持個体・編成・クエストが表示されることを確認。
2. Mac でプレイ履歴1件を追加し、「同期完了」を確認する。
3. スマホの同じアカウントで再読み込みし、プレイ履歴が反映されることを確認する。
4. スマホで EX 周回記録を追加し、Mac に反映されることを確認する。
5. Mac とスマホで **同じセクションを同時編集** し、競合状態となり無条件で上書きしないことを確認する。検証前にJSONバックアップを取得すること。
6. オフラインで ToDo を作成し、接続復帰後に同期できるか確認する。
7. JSONエクスポート→復元で新旧データが保持されることを確認する（復元は検証用環境で行う）。

**注意:** v0.6 での編集を継続しながら v0.7 を並行使用しない。v0.6 のクライアントは新しい `playLogs` を理解しないため、複数端末を同時に更新することを推奨。

## 制限

- 加撃表は検証済みの代表的な実・等級のみ。未検証の組み合わせは計算から除外し表示。
- ダメージは実ダメージではなく、入力倍率を掛けた概算である。
- ランク別の累計経験値は推測で埋めず、確認したJSON表を手動で読み込む。
- OSのプッシュ通知、ゲームイベントの自動取得、実データの自動収集は未実装。
- 周回・プレイ記録もFirestoreの1ドキュメント上限の影響を受ける。大量のログはCSV/JSONバックアップを保存する。
