# Monst Personal Manager v0.5

**v0.5更新情報：** `README-v05.md` と `UPGRADE-v05.md` を先にご確認ください。

# Monst Personal Manager v0.3

v0.2の既存コードを拡張した同期安定化版です。移行手順と制約は **[UPGRADE-v03.md](UPGRADE-v03.md)** を参照。

# Monst Personal Manager v0.2

React / TypeScript / Vite / Firebase による個人用ゲーム情報管理Webアプリ（非公式）。ゲーム運営会社とは無関係です。

## 重要：アップデート前にバックアップ

1. **旧アプリをまだ閉じないでください。** 旧アプリの設定→「JSONバックアップ」をクリックして、Mac内の安全な場所に保存します。
2. Firebase Console → Firestore Database → データ → `users/{UID}/private/state` に旧データがある場合は、削除しないでください。v0.2は読み取りだけを行います。
3. 念のためZIPで**元のプロジェクトを丸ごと別名保存**してください（`.env`を含める場合は他人と共有しない）。
4. 新版への切替後、JSONが正しく読めることを確認してから本番公開してください。

**このZIPにMac上の実際のデータは入っていません。** ブラウザのローカルストレージやユーザーのFirebaseへのアクセス権はありません。

## Macで起動

Node.jsは Vite 7 に対応した版（20.19+ または 22.12+）を使ってください。

```bash
cp .env.example .env
# .env に Firebase Web アプリの設定を入力（未設定ならローカルのみ）
npm install
npm run dev
```

`.env`はGitにコミットしないでください。FirebaseのWeb APIキーはサービスアカウント秘密鍵とは異なりますが、セキュリティルールは必須です。

## v0.1からの移行

- v0.1と同じorigin（例：同じ localhost または同じFirebase Hosting URL）で起動すれば、以前のローカル保存キー `monst-personal-v1` を引き継ぎます。
- 初回ログイン時にv0.2の `users/{UID}/data/*` があればそちらを読み込みます。なければv0.1の `users/{UID}/private/state` を読み込みます。
- **読み込んだ内容は、すぐにクラウドを上書きしません。** 内容を確認して、「現在データをクラウドへ上書き」を押すとv0.2形式へ移行できます。
- 旧Firestore文書 `users/{UID}/private/state` は削除しません。
- 別のドメインで起動し、ローカルのデータを引き継ぎたいときは、旧画面で出力したJSONを新画面の「JSONバックアップから復元」でインポートします。
- 新版でクラウドデータを読み込むと、読み込み前のローカルデータが `monst-personal-v2-recovery` に一時保存されます。「直前のローカル復旧データを読み込む」機能で戻せます（ブラウザデータ消去には耐えられません）。

## Firebase設定

1. Firebase ConsoleでWebアプリを登録。AuthenticationのGoogleログインを有効化。Authorized domainsに本番のHostingドメインと、開発用途で必要なら`localhost`を追加。
2. Cloud Firestore（Standard edition / `(default)`）を作成。
3. `.env.example`を`.env`へコピーし、Webアプリ設定から値を入れる。
4. **このv0.2の `firestore.rules` をデプロイ**（古いv0.1ルールでは新版に書き込めません）。
5. `npm run build`が成功したことを確認してから、Hostingを公開する。

```bash
npx firebase-tools login
npx firebase-tools use --add
npx firebase-tools deploy --only firestore:rules
npm run build
npx firebase-tools deploy --only hosting
```

公開後、必ずMacとスマホで**同じGoogleアカウント**にログインして内容が反映されることを確認してください。

## 同期設計

- Firestoreのパスは`users/{UID}/data/{section}`。`section`: `catalog`, `accounts`, `activeAccountId`, `owned`, `teams`, `todos`, `runs`, `bonds`, `events`。
- 各セクションは`value`, `revision`, `updatedAt`を保存。書き込みはFirestoreトランザクション内で現在の`revision`を読み、読み取り時の値と一致する場合だけ更新します。
- Firestoreリスナーで他端末の変更を検知し、編集がないときのみ取り込みます。ローカルに未保存変更がある場合は競合として自動上書きを停止します。
- 通信が切れた場合、ローカル保存は保持します。回復後は「保存を再試行」またはクラウドの読み直しを選択。トランザクションは完全なオフライン書き込みではありません。
- 競合時は**先にJSONバックアップ**してから、クラウド読込か手動上書きを選択してください。手動上書きは他端末の変更を失う可能性があります。
- 旧形式の文書は読み取り専用に残します。

### 現在の制約

- 複数セクションの書き込みを1トランザクションとして扱います。1セクション内の異なる行を別端末で同時に編集すると競合として停止します。自動マージはありません。
- v0.2の全セクションは分割されていますが、`catalog`および各セクションの1文書が**大きくなりすぎる場合**は保存を拒否します（上限を避けるため概算850KB未満）。巨大な図鑑を同期するには、将来キャラ単位の分割管理または明示許可された別配信手段へ変更してください。
- ブラウザのローカル保存は端末ごとに存在し、ブラウザデータ削除・プライベートモードには耐えません。重要な内容はJSONを別に保存してください。
- PWAはWebシェルのキャッシュに対応しますが、ネットがない環境でのFirestoreトランザクション実行はできません。オンライン復帰後の再試行が必要です。
- この版は認証済みGoogleアカウントそれぞれが自分用データを作れる方式であり、特定のGoogleアカウントのみログイン許可するわけではありません。
- 実際のFirebase接続テストとブラウザ上の回帰試験は、利用者のFirebaseプロジェクト上で実施してください。

## 図鑑JSONの形式

`sample-catalog.json`を参照。`id`、`name`、`attribute`（火/水/木/光/闇/その他）、`abilities`（文字列配列）は必須。
任意フィールドは `type`, `style`, `race`, `image`（HTTPS）、`evolution`, `friendship`, `ss`, `source`。

既存の同じIDがあれば更新、未登場IDは保持します。**取り込んだデータが正確・最新・許諾済みであることは自動判定しません。** 出典・利用条件を確認し、利用許可のない画像やスクレイピングしたデータを取り込まないでください。

## テスト

```bash
npm run test
npm run build
```

構造テストは構文・ルール・PWA設定を検査します。Firebase接続を実際に動作保証するものではありません。

## 改修の範囲

- v0.1で存在した図鑑、所持、編成、EX周回、絆、ToDo、イベント、計算、分析は保持。
- 図鑑の進化形態フィルタ、詳細表示、差分インポートを追加。
- 所持キャラの厳選目標、紋章、ソウルスキルの入力を追加。
- PWAマニフェストとホーム画面アイコン、静的シェルのService Workerを追加。
- 今後の課題：わくわくの実の種類・等級を構造化、クエストの適正・ギミック検索高度化、イベント月間ビュー、正確なダメージ式とテスト、図鑑の大規模分割、データの自動取得（権利確認後）。

---

## v0.4 図鑑強化

`src/catalog-v04.ts`に入力スキーマ・ライセンス確認フラグ・差分取り込み・複合AND検索の純粋関数を実装。`src/CatalogBrowser.tsx`に進化形態・撃種・戦型・種族・属性・アビリティ・所持済みの検索と詳細ダイアログを実装。

新しい図鑑JSONの例は`sample-catalog-v04.json`をご覧ください。**実際のゲーム素材は同梱していません。** 利用条件を確認できたデータのみ取り込んでください。v0.3と同じFirebase保存構造と旧データキーを維持しています。

更新手順とテストの注意事項：`UPGRADE-v04.md`。

## v0.6 クエスト・編成管理

v0.5を保持したまま、`src/QuestManager.tsx` と `src/quest-v06.ts` を追加しました。

- クエストの名前・属性・難易度・ギミック・メモの登録編集削除
- 所持個体IDに基づく4枠編成（同一キャラ・同一個体の複数枠選択可）
- メイン・サブを横断した所持個体選択（チェックで切替）
- ギミック対応検索（アビリティ名に基づく参考値）
- 保存編成の比較、コピー、お気に入り、変更履歴の復元
- 保存編成のJSON・独自SVG画像エクスポート
- `quests` コレクションセクションをFirestoreルールに追加

既存の`schemaVersion:1`、ローカル保存キー、所持個体IDと編成ID、全既存機能は継続。v0.5のバックアップでは`quests`がないので空配列へ自動補完されます。アップグレード手順は `UPGRADE-v06.md` を確認してください。

---

## v0.7 追加機能

既存の React/TypeScript/Vite/Firebase アプリに、以下のプレイ支援機能を追加しました。旧データ形式との互換を保っています。

- `src/play-v07.ts`: 基本加撃・一部複合加撃の効果と重複抑止、倍率入力による概算ダメージ、経験値・周回計算、EX集計、CSV変換、プレイ勝率などの純粋関数。
- `src/PlayTools.tsx`: 保存編成・個体の攻撃力参照、加撃・倍率・経験値の入力画面、EX履歴、絆履歴、ToDo、イベント予定、プレイ記録。
- `src/types.ts`: 既存のフィールドを維持したまま、ToDo/絆/イベントにオプション項目を追加。`PlayLog` を定義。
- `src/persistence.ts`, `src/sync.ts`, `firestore.rules`: `playLogs` セクションを追加。旧 `schemaVersion:1` と旧ローカル保存キーを維持。
- `tests/play-v07.test.mjs`: 新規計算テスト8件。`tests/emulator.test.mjs`: 新セクションのアクセス制御テストを追加。

加撃効果値の参照元: [AppMediaのわくわくの実の効果表](https://appmedia.jp/monst/2177008)。一部補足: [真・モンストWiki](https://w.atwiki.jp/gamemonst/pages/306.html)。ゲーム運営公式の計算保証ではないため、式に未対応の補正は計算されません。キャラクター画像や外部サービスのゲームデータは新たに同梱していません。

**更新手順:** `UPGRADE-v07.md` を参照してください。**テストの実施結果:** `TEST-REPORT-v07.md` を参照してください。

## v0.8 追加：統計ダッシュボード
- `src/analytics-v08.ts`：集計・CSV出力用純粋関数
- `src/AnalyticsDashboard.tsx`：各種グラフ・アカウント比較・画面間フィルタ
- `tests/analytics-v08.test.mjs`：境界条件テスト
- `UPGRADE-v08.md`：v0.7からの更新・バックアップ・同期確認手順
- `TEST-REPORT-v08.md`：実行結果と未検証項目

所持個体数・図鑑所持率・厳選・育成・EX・プレイ履歴・絆・アカウント差分を可視化します。統計用のFirestoreセクションは増設していません。図鑑データを別途インポートしていない場合、所持率の分母は登録済み図鑑のみとなります。

## v1.0 UI・PWA追加

- スマホ下部5項目ナビと「その他」メニュー、PCサイドバー折りたたみ
- 図鑑の仮想スクロール、100体以上の所持キャラ簡易一覧の仮想スクロール
- 図鑑の検索条件保存・復元・プリセット（端末内のみ）
- 所持キャラの検索語・表示条件の保持（端末内のみ）
- 編成4枠の上下交換ボタン
- 同期状態・未同期セクション数の表示
- 新サービスワーカーの安全な手動更新、対応環境でのPWAインストール案内
- 小画面、キーボードフォーカス、タップ領域の調整

移行手順は `UPGRADE-v09.md`、検証状況は `TEST-REPORT-v09.md` を参照してください。

## v1.0 安定化機能

- **データ診断**: 所持キャラ、キャラID、編成4枠、クエストID、ToDo、プレイ履歴の参照整合性を検査。
- **復元前プレビュー**: JSONの件数・容量・重大エラー・警告を表示し、重大エラーのあるバックアップは復元を停止。
- **端末内バックアップ履歴**: 最大5世代。復元・初期化前の明示バックアップに対応。端末内履歴はブラウザ削除や容量不足で消えるため、JSONの外部保存を推奨。
- **PWA更新保護**: 未同期・競合・オフラインの場合、更新操作を無効にする。v1.0のService Workerキャッシュ名へ更新。
- **データ互換性**: v1.0と同じ `schemaVersion:1`、`monst-personal-v1`、Firestoreの `users/{UID}/data/{section}` を使用。IDを振り直さない。
- **テスト**: `npm test`、`npm run build`、Emulator実行、`npx playwright install chromium && npm run test:e2e`。

詳しくは `UPGRADE-v10.md`、`TEST-REPORT-v10.md`、`OPERATIONS-v10.md` を参照してください。
