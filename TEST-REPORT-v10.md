# Monst Personal Manager v1.0 テスト報告

対象: v0.9の実ソースを複製・拡張したv1.0。

| 実施内容 | 結果 |
|---|---|
| `npm test`（既存+新規計64件） | 64/64 成功 |
| TypeScript/TSX構文解析 | 実施・構文エラーなし |
| 所持10,000件、編成1,500件の参照検査 | Nodeベンチマークとして実行・結果をテスト出力 |
| `npm run build` | 未成功: Node依存パッケージ未導入のためReact/Firebase等の型・モジュール不足 |
| `npm install --offline` | ENOTCACHED（@playwright/test等のキャッシュなし） |
| Firebase Emulator統合テスト | この環境では未実施。既存テストにアクセス制限テストを追加 |
| Playwright E2E | テストコード追加、ブラウザ実行は未実施 |
| Mac/iPhone/Android実機 | 未実施（利用者環境での確認が必要） |

注記：単体テスト成功は実機同期、ビルド、PWA更新、保存の無損失を保証しません。Firestoreルールはv0.9と同じです。クラウドの本番データに対する操作はしていません。

## 実施コマンド（利用者のMac）

```bash
npm install
npm test
npm run build
npx firebase-tools emulators:exec --project demo-monst-personal-v10 --only auth,firestore "npm run test:emulator"
npx playwright install chromium
npm run test:e2e
```

### 実機手順

1. v0.9でJSONバックアップをダウンロードし、現行公開アプリからの復元が可能か確かめる。
2. v1.0のMacローカル画面で「設定・同期」→「v1.0 データ診断・安全なバックアップ」を開く。
3. 旧形式JSONを選択し、参照件数・警告・重大エラーを確認する。重大エラーがあるJSONは復元拒否されること。
4. 元データをバックアップしたうえで、テスト用のアカウントまたはテスト用Firebaseプロジェクトに復元する。
5. Macとスマホで同じUIDにログインし、所持個体・編成・プレイ記録を追加・編集し反映を確認する。
6. 一方をオフラインにし、端末側の未同期表示と復帰後の再接続を確認する。両端末で同一データを編集した場合は競合検出を確認する。
7. 未同期変更がある間はPWAの更新ボタンが無効になることを確認する。
8. iPhoneのSafari・AndroidのChromeでナビゲーション、図鑑、管理、同期表示、バックアップ操作を確認する。

### 未解決・制約

- Firestoreの分割セクション間の複数同時変更には、厳密な全体トランザクション保証を超える障害ケースがあります。
- 端末内履歴はlocalStorageで最大5件。容量上限とブラウザデータ削除による消失に注意。自動クラウド世代管理は未実装。
- PWAのService Worker更新フローは自動化テストと実機で再検証してください。
- Playwrightは追加依存。ブラウザ実体のインストールが必要です。
