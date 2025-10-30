# cc-plugin-mcp

Claude CodeプラグインにMCP（Model Context Protocol）経由でアクセスするためのMCPサーバーです。

## 概要

Claude CodeのプラグインシステムとのインタフェースをMCPプロトコルで提供し、プラグイン一覧の取得や詳細情報の参照を可能にします。MCPクライアント（Claude Desktop、Cursor等）から利用できます。

## 主な機能

- **MCPプロトコル対応**: Model Context Protocolに準拠したサーバー
- **プラグイン管理**: Claude Codeプラグインの一覧取得と要素読み込み
- **セキュリティ**: パストトラバーサル対策、入力検証、エラーハンドリング
- **パフォーマンス**: LRUキャッシュによる高速化
- **運用性**: 包括的なロギング、29個のテストケース

## MCP ツール

- `list_plugins` - 利用可能なプラグインの一覧を取得
- `load_elements` - 指定されたプラグインの要素（skills, agents, commands）を読み込み

## 設定方法

MCPクライアントの設定ファイル（例：Claude Desktopの`claude_desktop_config.json`）に以下を追加：

```json
{
  "mcpServers": {
    "cc-plugin-mcp": {
      "command": "uvx",
      "args": ["cc-plugin-mcp"]
    }
  }
}
```

## インストール

```bash
# uvxで直接実行（推奨）
uvx cc-plugin-mcp

# またはPyPIからインストール
pip install cc-plugin-mcp

# 開発環境の場合
git clone https://github.com/ppspps824/cc-plugin-mcp.git
cd cc-plugin-mcp
uv sync --all-extras
```

## 使い方

MCPサーバーとして動作するため、MCPクライアントから直接呼び出されます。手動でテストする場合：

```bash
# uvxでMCPサーバーとして起動（推奨）
uvx cc-plugin-mcp

# または開発環境の場合
uv run python -m cc_plugin_mcp.main
```

## AI ツールとの MCP 統合

Cursor、Claude Desktop など MCP 対応の AI ツールで、このMCPサーバーを最適に活用するために：

### Cursor での使用方法
1. Cursor の設定（`.cursor/settings.json` など）に MCP サーバーを追加
2. 上記の「設定方法」セクションで示された設定を含める
3. **重要**: システムプロンプトまたは最初のメッセージで、AI に MCP ツールを使用するよう指示してください。特に、最初に利用可能な MCP ツールを読み込むように指示することが重要です。

### Claude Desktop での使用方法
1. 設定ファイル `claude_desktop_config.json` に設定を追加（上記「設定方法」セクション参照）
2. Claude Desktop を再起動して MCP サーバーを有効化
3. Claude がすぐに MCP ツールを利用できるようになります

### MCP ツール使用時のベストプラクティス
- **ツールを最初に読み込む**: AI に最初に利用可能な MCP ツールを確認するよう指示してください
- **システムプロンプトを確認**: システムプロンプトまたは初期指示に MCP ツール使用ガイダンスが含まれていることを確認してください
- **機能を発見**: 特定の機能をリクエストする前に、ツールを使ってプラグインとその要素を探索してください

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

### MCPクライアントで認識されない場合
1. MCPクライアントの設定ファイルが正しく設定されているか確認
2. `uvx`コマンドが利用可能か確認（`uvx --version`）
3. MCPクライアントのログでエラーメッセージを確認

### テストが失敗する場合
```bash
uv sync --all-extras --refresh
uv run pytest -v
```

## ライセンス

MIT

## リポジトリ

https://github.com/ppspps824/cc-plugin-mcp
