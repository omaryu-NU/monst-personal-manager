# Monst Personal Manager v0.5

v0.4に追加して、所持キャラの個体別編集・わくわくの実/目標のスロット管理・厳選自動判定・育成・英雄の書・タス値・紋章メモ・ソウルスキル・お気に入り・タグ・個体複製・一括編集・変更履歴を追加した個人用Webアプリです。

## 起動

```
cp .env.example .env
npm install
npm test
npm run build
npm run dev
```

Firebaseを使う場合は従来の`.env`を移してください。変更ファイルと安全なアップグレード手順については`UPGRADE-v05.md`を参照してください。

## データ移行

- Firebaseスキーマバージョン1を維持し、所持個体のID、編成4枠の参照、アカウントIDはそのままです。
- 旧形式の`fruits: string[]`と`targetFruits: string[]`を構造化スロットへ互換移行します。文字列フィールドも継続保存します。
- v0.4からの初回ローカル変換時は元JSONを`monst-personal-v04-migration-backup`に保管します。ブラウザのデータ削除ではこのバックアップも消えるため、アップグレード前のJSONエクスポートは必須です。
- 古い紋章情報は`emblem`と`soulSkills`で保持し、新しい個体編集画面で編集できます。

## テスト上の制約

作成環境で`npm test`相当の14件の単体/構造テスト、TypeScript/TSX構文解析を実行しました。ネットワークへのアクセス制限でnpm依存パッケージを取得できず、完全ビルド・Emulator実行・実機同期は未実施です。
