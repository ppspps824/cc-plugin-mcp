# cc-plugin-mcp

Claude CodeプラグインにREST API経由でアクセスするためのサーバーです。

## 概要

Claude Codeのプラグインシステムとのインタフェースを提供し、プラグイン一覧の取得や詳細情報の参照を可能にします。

## 主な機能

- **セキュリティ**: パストトラバーサル対策、入力検証、エラーハンドリング
- **パフォーマンス**: LRUキャッシュによる高速化
- **運用性**: 包括的なロギング、29個のテストケース

## API エンドポイント

- `GET /health` - ヘルスチェック
- `GET /plugins` - プラグイン一覧取得
- `POST /plugins/{plugin_name}/load-elements` - プラグイン要素読み込み

詳細は [API ドキュメント](http://127.0.0.1:8000/docs) を参照してください。

## インストール

```bash
# 依存関係のインストール
uv sync

# 開発環境の場合
uv sync --all-extras
```

## 使い方

```bash
# サーバー起動
uv run python -m cc_plugin_mcp.main

# API ドキュメント
# Swagger UI: http://127.0.0.1:8000/docs
# ReDoc: http://127.0.0.1:8000/redoc
```

## テスト

```bash
# テスト実行
uv run pytest

# カバレッジ付き
uv run pytest --cov=cc_plugin_mcp
```

## トラブルシューティング

### プラグインが見つからない場合
1. `~/.claude/plugins/` ディレクトリの存在確認
2. `~/.claude/plugins/marketplaces/` に marketplace.json があるか確認

### テストが失敗する場合
```bash
uv sync --all-extras --refresh
uv run pytest -v
```

## ライセンス

MIT
