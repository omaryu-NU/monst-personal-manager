# v0.3 → v0.4 更新ガイド

## データを壊さず更新する

1. **v0.3の設定画面で「JSONバックアップ」を先に保存**。保存したJSONを開き、`schemaVersion: 1`と既存の`owned`/`teams`の件数を確認。
2. v0.3プロジェクトフォルダをコピーして退避。
3. v0.4フォルダを展開し、旧フォルダの`.env`（必要なら`.firebaserc`）を新しいフォルダへコピー。`.env`は第三者に送らないこと。
4. `npm install && npm test && npm run build && npm run dev`を実行。
5. **まずMac側で所持個体・編成・図鑑が保持されているか確認**。次にFirebaseへログインし、同期状態を確認。従来のデータを消す処理は追加していません。
6. 問題なければ `npx firebase-tools deploy --only hosting` を実行。Firestoreルールと同期ドキュメント構造はv0.3から変更していません。

## 図鑑データの取り込み

- 新ファイル例：`sample-catalog-v04.json`。架空のキャラを1件含む**自作サンプル**です。実在のモンストキャラデータ・画像は入っていません。
- 設定画面 → 図鑑JSONインポート → 検証 → 新規／更新／未変更の件数を確認 → 「差分更新を確定」。既存ID以外を消さない方式です。
- 取り込み前に`permissionConfirmed: true`を設定するには、**人間がデータ元の権利・利用条件を実際に調べて利用が認められていることを確認**する必要があります。アプリ自身はWeb上の許諾を法的に検証するものではありません。
- v0.3の`character-catalog.json`や`sample-catalog.json`はライセンス情報を持たない旧形式のため、そのままでは新しい取り込み画面で拒否されます。本人が権利を確認したデータに限り、`characters`配列を新形式の`provenance`付きのJSONに包んで読み込んでください。**v0.3から既に保存済みの図鑑は変更せず表示できます。**
- 一度に最大50,000件を形式検証できますが、**v0.3と同じFirestoreの単一catalogドキュメント同期を維持するため、更新後の保存サイズが約800KiBを超える場合は反映を中止します。** 全キャラ図鑑の大容量同期には、将来バージョンで分割保存設計が必要です。画像URLは`https://`のみ受け入れ、入力に重複ID・不正属性・不正な数値がある場合は**全件を取り込みません**。
- 図鑑はv0.3と同じ`AppState.catalog`と`schemaVersion: 1`に保存されます。既存の`owned[*].characterId`と`teams[*].slots`は変更しません。

## ローカルテスト

- `npm test`：基本構造チェック＋図鑑バリデーション・差分・検索単体テスト
- `npm run build`：TypeScript型検査とViteビルド
- `npx firebase-tools emulators:exec --project demo-monst-personal-v04 --only auth,firestore "npm run test:emulator"`：Firebase Emulator統合テスト（Java JDKが必要）

## 互換性・未実装

- v0.1/v0.2/v0.3の保存状態を`validateState`で引き続き読み込み可能です。図鑑の拡張フィールドは任意です。
- 保存・同期用のFirestoreコレクションやルールの変更はありません。
- 実キャラの自動収集・自動配信は行いません。許諾を確認したデータの**手動差分取り込み**です。
- 同名／異IDのキャラを自動同一視しません。IDが変わると所持と編成の参照が切れ得るため、データ提供元の恒久的IDを使用してください。
- v0.3既知の同期競合・同時編集の制約は引き続き適用されます。
