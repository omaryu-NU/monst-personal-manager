# v0.5 → v0.6 更新ガイド

## 更新前に必ず行うこと

1. **公開中のv0.5で「設定・同期」→「JSONバックアップ」を実行**。ローカルデータの実ファイルはこの開発環境にはありません。
2. 現在のv0.5フォルダを丸ごと複製して保存。
3. Firestore Consoleの `/users/{UID}/data/` を確認。同期完了を確認し、他端末から同時編集しないでください。
4. v0.6 ZIPを解凍し、v0.5の `.env` と `.firebaserc` をコピー。`.env` はZIPに同梱していません。

## 追加した保存データ

- `AppState.quests` (新規): クエスト名・難易度・属性・ギミック・メモ・ゲームアカウントID。
- `Team.questId` (任意): クエスト参照ID。
- `Team.history`, `favorite`, `notes`, `updatedAt` (任意): 編集履歴、お気に入りなど。
- `Team.slots` は従来の**所持個体IDの配列**のままです。`accountId` は編成管理アカウントを示し、選択した個体の `accountId` とは独立です。
- `schemaVersion: 1` およびブラウザの `monst-personal-v1` キーを維持しています。古いバックアップの `quests` がなくても空配列に変換します。
- クエスト情報を新しいFirestoreドキュメント `users/{UID}/data/quests` へ保存します。**`firestore.rules`の更新が必要です。**

## Macでのコマンド

```bash
npm install
npm test
npm run build
npx firebase-tools deploy --only firestore:rules
npm run build && npx firebase-tools deploy --only hosting
```

**必ずFirestoreのルールを先にデプロイしてください。** v0.5のルールのままだと `quests` の保存が拒否されます。デプロイ前に `firebase use` と `.env` のプロジェクトID一致を確認してください。

## Emulator

Java JDKとFirebase CLIをセットアップ後、次を実行してください。

```bash
npx firebase-tools emulators:exec --project demo-monst-personal-v06 --only auth,firestore "npm run test:emulator"
```

本番環境での2端末同期は、Macでクエスト・編成を登録し、スマホで反映を確認した後、スマホから名前・枠を更新してMacで反映確認してください。競合時には上書きを止め、JSONバックアップを取得してから解決してください。

## 注意

- ギミック対応判定は名称の一致に基づく補助機能で、適正ランキング・実際の発動条件を保証するものではありません。
- 画像エクスポートは独自のSVG出力です。キャラクターの著作物画像は転載しません。
- Firestoreの同時編集競合は既存のセクション単位のリビジョン検出を利用しています。自動マージは実装していません。
- `teams`・`quests` のデータが非常に多くなる場合は、現行のセクション1文書あたりのFirestore容量制限に注意してください。
