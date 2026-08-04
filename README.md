# tradermade_cfd

> **状態: 個人Windows環境向けに作成されたCFDデータ処理prototypeです。現在のままでは再現・継続運用できません。**

TraderMade APIから価格データを取得し、Parquet・CSV・Feather・DuckDB等へ保存して、統合・指標計算・表示を試したコードを保存しています。稼働中のデータサービス、再現可能な分析package、売買systemではありません。

## 現在確認できる処理

| ファイル | 役割 |
|---|---|
| `src/main_fetch.py` | real-time、historical、time-series APIの呼び出しとfile保存 |
| `src/data_integrator.py` | 複数の取得fileを統合 |
| `src/indicator_calculator.py` | basisやrolling Z-score等の計算 |
| `src/view.py` / `src/view.ipynb` | IPython・Notebook向け表示 |
| `src/config.py` | symbol、期間、保存先、API key等の設定 |

コードが存在することは確認できますが、これらを順番に実行すれば現在も正常に完走することは確認していません。

## 現在の主要な制約

### 個人環境への固定

`src/config.py`は次のWindows絶対pathを前提にしています。

```text
D:\_investos\CFD\cfd
D:\_investos\CFD
```

READMEに書かれたrepository相対の`data/`構成とは一致しません。別PC、WSL、Linux、CI環境では設定変更なしに動作しません。

### 依存定義の不一致

`src/main_fetch.py`は`pyarrow`と`duckdb`をimportしますが、現行`requirements.txt`には両方がありません。README旧版の依存説明も実装全体を網羅していません。

したがって、次の手順は現在の再現可能なquick startではありません。

```bash
pip install -r requirements.txt
python src/main_fetch.py
```

### データと計算結果

- API応答の取得日時、provider request、timezone、単位、symbol identityを一貫して保存する契約がありません
- committed outputを最新データとして利用できません
- basis、年率換算、Z-score、市場regimeの計算前提を一つの正準schemaで固定していません
- CI、自動test、freshness、欠損、重複、schema driftの検証を確認できません

## APIキー

コードは`TRADERMADE_API_KEY`環境変数を参照します。APIキーをrepository、Notebook出力、log、生成物へ保存しないでください。過去に露出した可能性があるキーは、文字列を削除するだけでなくprovider側で失効・再発行してください。

## 現在できないこと

- clone直後の再現可能な実行
- 定期的・無人のCFDデータ収集
- outputの鮮度・完全性・正確性の保証
- 本番運用、売買執行、投資判断への利用

## 再開する場合の最低条件

1. 保存先をrepository相対pathまたは設定fileへ移行する
2. `pyproject.toml`とlock fileで全依存を固定する
3. raw response、取得時刻、provider、symbol、timezone、単位を保存する
4. spot・forward・CFD等のinstrument identityと計算式をschema化する
5. 欠損・重複・freshness・API error・rate limitをtestする
6. clean Windows/Linux環境でCIを通す
7. outputにdata as-of、source、code commit、設定hashを付与する

## 位置づけ

本リポジトリは、TraderMadeを用いたCFDデータ処理の過去prototypeです。コードの参考資料としてのみ扱い、現行基盤として利用する前に構造・依存・credential・provenanceを再設計してください。

**README監査日:** 2026-08-05
