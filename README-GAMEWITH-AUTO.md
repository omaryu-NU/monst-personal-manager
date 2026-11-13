# GameWith既存4,455件データから画像を自動登録するパッチ

GameWithで過去に取得済みの図鑑No./画像URL **4,455件**を同梱しています。前回の`gamewith-approved-icons.csv`を手作業で作成する必要はありません。サイトへの再巡回も行いません。

## 既存プロジェクトへ適用

`monst-personal-manager-v10`のルートで以下を実行してください。ZIP内のファイルを配置する前にGit状態を確認してください。

```bash
git status --short
unzip -o ~/Downloads/monst-gamewith-4455-auto-icons.zip
python3 -m unittest discover -s tests -p 'test_prepare_gamewith_icon_queue.py'
python3 scripts/prepare_gamewith_icon_queue.py \
  --permission-reference 'GameWith-owner-authorization-confirmed-2026-11-13'
```

最後のコマンドは **dry-run** です。出力の`queued`, `rejected_count`を確認してください。生成CSVをローカルでも保存したいときは同じコマンド末尾に `--apply` を付けます。既存の`config/approved-icon-sources.csv`は変更しません。

## GitHub Actionsで画像を徐々に保存

GitHubのRepository Variablesに追加してください。

- `GAMEWITH_PERMISSION_REFERENCE`: 実際の許諾メールの日付/参照番号など。許諾本文・個人情報・秘密情報は入れない
- `GAMEWITH_ICON_IMPORT_ENABLED`: 最初は`false`。CSVとdry-runを検証後、`true`で有効化

既存の`APPROVED_ICON_HOST=game.technophere.com`、`APPROVED_ICON_IMPORT_ENABLED`、`AUTO_DEPLOY_HOSTING`には触れません。別ワークフロー、別CSVです。

```bash
git add .github/workflows/gamewith-approved-icons.yml scripts/prepare_gamewith_icon_queue.py tests/test_prepare_gamewith_icon_queue.py config/data/gamewith-observed-4455.json README-GAMEWITH-AUTO.md
git commit -m 'feat: queue previously verified GameWith icon URLs'
```

まず自分の変更を安全に同期したあとpushしてください。従来の`catalog-coverage.json`未コミット変更があれば既存の同期補助ツールでバックアップしてからrebaseします。**強制push禁止**。

新ワークフロー`Import GameWith approved character icons`を手動で実行し、最初はdry-runを確認します。許諾範囲と配信元への負荷が問題ないことを確認した後、`GAMEWITH_ICON_IMPORT_ENABLED=true`にして手動1回実行し、`downloaded`, `errors`, `denied`を確認します。問題なければ1日1回のscheduleにより毎回最大10枚を取得します。

- 既存の`public/character-icons/manifest.json`へ書き足す（既存No.は取得スキップ）
- 画像データは`public/character-icons/{No}.{拡張子}`
- 権利証跡は`public/character-icons/rights-evidence.json`
- GitHubへ自動コミット
- Hosting反映は従来の`Update Technophere catalog`の`Deploy Hosting only`成功後
- React側の自サイト画像表示パッチが反映済みなら、自動追加された画像も表示できる

**重要:** 4,455件のURLが存在することと、4,455枚が取得できること・現在の全キャラクターを網羅することは別です。403/404や相違が出ればログで確認し、無理にURLを推測したり制限を回避しません。10枚/日のまま4,455枚では理想条件で約446日かかるので、許諾側に許容頻度・一括提供の可否を確認すると期間短縮につながります。
