# v0.9 検証記録

- `npm test`: **51件成功 / 0件失敗**。v0.8までの44件、v0.9追加7件。
- TypeScript/TSX構文検査：全 `src` ソースについて TypeScript parser を用いた構文検査でエラーなし。
- `npm install --offline`: **失敗**。ローカルnpmキャッシュに `@types/react` 等が不足 (`ENOTCACHED`)。
- `npm install` (オンライン): **未完了**。この実行環境ではパッケージレジストリへの接続が完了しないため時間制限で終了。
- `npm run build`: **失敗**。React/Firebaseの依存モジュール・型定義が未インストールで解決できない。依存関係を含む型チェック完了とはみなさない。
- Firebase Emulator統合テスト：**未実施**（依存関係未導入）。`tests/emulator.test.mjs` はEmulator環境での実行を前提とする。
- Mac・iPhone・Android実機：**未実施**。本環境に実ユーザーのGoogleアカウント、ブラウザ端末、Firebase環境へのアクセスはない。

## v0.9 の自動検査

検索プリセットの追加と空白名、複数単語トークン分割、SWのキャッシュ除外、インストール時の強制更新回避、同期実装の残存、モバイルメニューの存在、編成枠入れ替えの参照維持を検査。

**重要:** 静的テストは画面操作・同期・競合・復旧の実際の正しさを保証しない。Mac側で `npm install && npm test && npm run build`、続いて Firebase Emulator・実機テストを実施するまで本番公開を避けること。
