# 昆布組み合わせ最適化ツール

昆布を指定枚数ずつ袋詰めする際の最適な組み合わせを計算するWebアプリです。

**🌐 デモ**: https://ghx5efvjwmsvzpvjm6frwg.streamlit.app/

## 概要

異なる重量の昆布在庫から、目標重量範囲に収まる組み合わせを見つけ、作成可能な袋数を最大化します。

### 解決する問題

- 在庫: 6.0g〜7.9gの昆布が各種あり
- 目標: 1袋6枚で合計40〜43gに収めたい
- 求めたい: 最大何袋作れるか？どの組み合わせで？

### 使用アルゴリズム

**整数線形計画法 (Integer Linear Programming)** を使用しています。

- 組合せ最適化問題の一種
- ビンパッキング問題・カッティングストック問題に類似
- Google OR-Tools の CBC ソルバーで解を算出

## 使い方

### Webアプリ（Streamlit）

1. https://ghx5efvjwmsvzpvjm6frwg.streamlit.app/ にアクセス
2. CSVファイルをアップロード（または サンプルCSVをダウンロードして編集）
3. 「最適化を実行」をクリック
4. 結果をCSVでダウンロード

### CSVフォーマット

```csv
weights,stock
6.0,20
6.1,3
6.2,6
...
```

| 列名 | 説明 |
|------|------|
| weights | 昆布の重量（g） |
| stock | 在庫数（枚） |

### 設定項目

| 項目 | デフォルト | 説明 |
|------|------------|------|
| 目標重量（最小） | 40.0g | 1袋の最小重量 |
| 目標重量（最大） | 43.0g | 1袋の最大重量 |
| 1袋あたりの枚数 | 6枚 | 袋に入れる昆布の枚数 |

## ローカル実行

### 必要環境

- Python 3.9以上

### インストール

```bash
git clone https://github.com/shinsap/kombu.git
cd kombu
pip install -r requirements.txt
```

### 実行

```bash
# Webアプリ版
streamlit run app.py

# CLI版
python optimize_kombu_v2.py
```

## ファイル構成

```
kombu/
├── app.py                 # Streamlit Webアプリ
├── optimize_kombu_v2.py   # CLI版スクリプト
├── kombu.csv              # サンプル在庫データ
├── requirements.txt       # 依存パッケージ
└── README.md
```

## 技術スタック

- **フロントエンド**: Streamlit
- **最適化エンジン**: Google OR-Tools (CBC Solver)
- **データ処理**: pandas

## ライセンス

MIT License
