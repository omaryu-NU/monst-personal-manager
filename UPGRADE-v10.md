# v0.9 → v1.0 安全な更新

1. 公開中のv0.9から **設定・同期 → JSONバックアップ**を実行し、外部保存する。v0.9のフォルダ全体を複製する。
2. v1.0 ZIPを解凍する。古い`.env`と`.firebaserc`のみコピーし、`.env`のプロジェクトIDと`.firebaserc`のデプロイ先を照合する。
3. `npm install && npm test && npm run build` を実行する。ビルドに失敗したらデプロイしない。
4. `npm run dev` でログイン前にキャラ・編成・所持個体が揃っているか確認する。
5. 設定画面の「データ診断」で重大エラー・警告がないか確認する。旧データへの修正を自動適用しない。バックアップJSONの復元プレビューを検証する。
6. `npx firebase-tools emulators:exec --project demo-monst-personal-v10 --only auth,firestore "npm run test:emulator"` で権限を検査する。
7. `npm run test:e2e`（必要なら `npx playwright install chromium`）。
8. テスト用アカウントで同期を確認後に `npm run build && npx firebase-tools deploy --only hosting` で公開。Firestoreルール・保存パスは変更していない。

**ロールバック**: 保存済みのv0.9フォルダから再ビルドしてHostingを戻す。v1.0では旧データ項目の追加やID変更を行わない。ただし新しい版で編集された最新データを古い画面で開く場合は、必ずバックアップを取り、旧版の対応範囲を確認する。クラウドへの強制上書きは慎重に実施する。
