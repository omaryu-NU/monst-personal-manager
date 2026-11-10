# Monst Personal Manager v0.4 → v0.5

## 更新概要

- v0.4の`src/App.tsx`・`src/types.ts`・`src/persistence.ts`・`src/styles.css`を更新し、`src/OwnedManager.tsx`・`src/owned-v05.ts`・`tests/owned-v05.test.mjs`を追加。
- Firebaseのコレクション構造、保存キー`monst-personal-v1`、`schemaVersion: 1`、編成の個体ID参照を変更していません。
- **既存のソースに単に一部の新規ファイルをコピーするだけでは動作しません。** ZIP内の更新済みファイルを含めて適用してください。

## 実データを保護する手順

1. **必須**：公開中v0.4の設定画面で「JSONバックアップ」を取り、Mac内に保存。Firebase側のドキュメントも必要に応じてエクスポートしてください。
2. v0.4のプロジェクトフォルダを別フォルダとして丸ごとコピー。
3. v0.5のZIPを展開。v0.4の`.env`および`.firebaserc`をv0.5へコピー（ZIPに認証設定は含めない）。
4. `npm install`、`npm test`、`npm run build`、`npm run dev`の順に実行。既存の個体ID、同じキャラの複数個体、編成スロットが保持されているか確認。
5. ローカルのv0.4データを最初に読み込むと、新しく追加した各種フィールドを**既存フィールドを保持したまま**補完し、最初の変換前JSONをブラウザの`localStorage`キー`monst-personal-v04-migration-backup`に一度だけ保存します。`monst-personal-v1`は継続使用します。
6. v0.5で新しい項目を編集した後も、従来の`fruits`および`targetFruits`配列を併せて更新します。旧バージョンに戻す際は必ずJSONバックアップを使用してください。
7. 開発環境でFirebase同期とデータが確認できた後だけ、本番公開：`npm run build && npx firebase-tools deploy --only hosting`。

## 新しい画面

所持キャラ画面で個体の詳細を開くと、レベル・ラック・タス値・育成状況・英雄の書、実（現在と目標）、紋章メモ・ソウルスキル・タグ・お気に入り・最大40件の変更履歴を編集できます。個体の複製と複数個体の一括編集にも対応しました。編成選択欄には個体IDと厳選/育成の状況を表示します。

## 保持されるv0.4機能

ダッシュボード、図鑑データの差分インポート、所持管理、編成、EX周回、絆、ToDo、イベント、計算、分析、JSONバックアップ/復元、Firebaseリアルタイム同期・競合判定・オフライン保存・PWA。

## 制約

- v0.5の紋章欄は個体に付ける**メモとソウルスキル情報**です。ゲーム側のアカウント・属性ごとの紋章装着制約を自動検証するものではありません。
- わくわくの実はデータの管理と目標照合を提供します。実際のゲームによる装着可能枠数・特殊効果・効果重複等は自動検証しません。最大4枠まで手動登録できます。
- 履歴は各所持個体のFirestore `owned` セクション内に保存され、最大40件です。Firebaseでの独立した監査ログではありません。入力のたびに記録されるため履歴の粒度は細かくなります。
- v0.4と同じFirestoreのドキュメントサイズ制限があります。大量の個体・履歴を扱う場合はセクション分割を検討してください。
- 実機のFirebase Emulator統合テストとスマホ・Mac間の同期確認は、このZIPの作成環境では実行できていません。v0.4での成功をv0.5の成功と見なさないでください。

## テスト

```
npm install
npm test
npm run build
npx firebase-tools emulators:exec --project demo-monst-personal-v03 --only auth,firestore "npm run test:emulator"
```

ローカルでビルドとFirebaseの検証が成功した場合にのみHostingを更新してください。既存データが同期されているブラウザで新しいバージョンを開く際は他端末で同時編集を避けてください。
