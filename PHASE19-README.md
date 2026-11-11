# 第19段階：全系統・進化形態・詳細欠損のオフライン監査

## 目的
最新版の `public/catalog/manifest.json` と全 `characters-*.json`、`catalog-update-state.json` を突き合わせ、どのキャラのどの項目が欠けているかをCSVで可視化します。**本パッチは読み取り専用で、ネットワーク通信・Firebase操作・GitHub Actions変更・既存JSON更新を行いません。**

第18段階のワークフローやコードを上書きしない、独立したスクリプトと単体テストのみを含みます。

## インストール
プロジェクト直下で実行：

```bash
unzip -o ~/Downloads/monst-catalog-phase19-coverage-audit-patch.zip
python3 -m unittest discover -s scripts -p 'test_catalog_phase19.py'
python3 -m unittest discover -s scripts -p 'test_catalog_*.py'
python3 scripts/catalog_phase19.py public/catalog --state catalog-update-state.json --output local-reports/phase19
cat local-reports/phase19/summary.json
```

## 出力ファイル
- `summary.json`: レコード数、図鑑No.重複、一覧の未巡回、系統検証状態、フィールド欠損数
- `family-status.csv`: 系統別の検証状態と、認識済み図鑑No.の照合
- `missing-fields.csv`: 図鑑No.別・フィールド別の未収録項目
- `missing-listing-pages.csv`: 未巡回ページ
- `form-state-discrepancies.csv`: 状態ファイルにある検証済み形態がカタログにないケース等
- `structural-issues.csv`: ID重複、manifest件数不一致、欠損チャンクなど

検証済み系統という状態は「一度解析に成功した」ことを示すだけで、サイトの全進化形態が収録された保証ではありません。そのため `allFormsProvenComplete` は常に `false` です。

**重要:** `manifest.json`と`catalog-update-state.json`が同時点でないと、`form-state-discrepancies.csv`に偽の不一致が表示される場合があります。GitHub Actionsが更新した**同じコミットのファイル**を使って検証してください。

`stateAvailable=false`の場合、系統の検証状態は`unknown_no_state`になり、憶測で検証済みにしません。`manifest.coverage`がある場合に限り一覧巡回数を代用します。

## GitHubへの反映
```bash
git add scripts/catalog_phase19.py scripts/test_catalog_phase19.py PHASE19-README.md
git commit -m 'test: add offline phase19 catalog coverage audit'
git status --short
# 自動生成ファイルの変更がある場合は、内容を確認してバックアップ・退避してから以下を実行
git pull --rebase origin main
git push origin main
```

この段階ではGitHub Actionsに自動追加しません。まずCSVに含まれる欠損・不一致を確認してから、次の収集ロジック改善に進みます。

## 次に共有してほしいもの
- `local-reports/phase19/summary.json`
- `local-reports/phase19/form-state-discrepancies.csv`
- `local-reports/phase19/family-status.csv`
- 最新の `catalog-coverage.json`

本パッチの単体テストはHTTPアクセスしません。実サイトの最新件数や全形態の網羅性は、このテストだけでは確認できません。
