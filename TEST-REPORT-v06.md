# v0.6 テスト報告

## 完了

- `NODE_PATH=/opt/nvm/versions/node/v22.16.0/lib/node_modules npm test`：**22件成功 / 0件失敗**（Nodeテスト。グローバルに既存のTypeScriptをテスト時のみ解決）。
- `tsc --noEmit src/quest-v06.ts src/persistence.ts src/owned-v05.ts src/types.ts --target ES2022 --module ESNext --moduleResolution Bundler --skipLibCheck --strict`：成功。
- `transpileModule`によるTSX/TS構文チェック：成功。
- 旧 v0.5 の `quests` 欠落を `[]` に移行するテスト成功。編成IDと個体参照維持確認。

## 未完了（環境制約）

- `npm install --offline`：`ENOTCACHED`（React/Firebase等のnpm依存ライブラリのキャッシュが存在しない）。
- `npm run build`：依存ライブラリがないため未完了。Mac上で必ず実行すること。
- Firebase Emulator統合テスト：Firebase CLI / Firebase SDKがこの環境にないため未実施。`tests/emulator.test.mjs`にv0.6 questsルール権限テストを追加。
- PC・スマホ実機同期：ユーザー端末とFirebaseプロジェクトへのアクセスがないため未実施。

## 完了条件（Mac）

1. `npm install && npm test && npm run build`
2. `npx firebase-tools emulators:exec --project demo-monst-personal-v06 --only auth,firestore "npm run test:emulator"`
3. `npx firebase-tools deploy --only firestore:rules`（**Hosting公開前**）
4. 既存所持/編成ID保持とMac・スマホ双方向同期を検証。
5. `npm run build && npx firebase-tools deploy --only hosting`
