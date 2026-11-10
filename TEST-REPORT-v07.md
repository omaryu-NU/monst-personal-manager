# v0.7 テスト結果

- ベース: v0.6 のソース一式をコピーして差分実装。
- `npm test`: 31件成功（既存テスト + 新規 `tests/play-v07.test.mjs` 9件）。
- `npm install`: 失敗。実行環境から npm registry にアクセスできず `EAI_AGAIN`。
- `npm run build`: 実行したが、上記依存が不足し React/Firebase 等のモジュール未検出のため失敗。完全ビルド成功の保証なし。
- Firebase Emulator: 未実施（SDKを取得できないため）。v0.7の `playLogs` に対する所有者/他ユーザー/リビジョン検査をテストに追加した。
- PC・スマホ実機同期: 未実施。利用者による動作確認が必要。

**npm test は純粋な計算・構造テストであり、ブラウザやFirebase実環境の統合動作を保証しない。**
