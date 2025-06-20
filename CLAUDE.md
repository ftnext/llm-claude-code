# LLM Claude Code Plugin Specification

## 概要

`llm-claude-code`は、[simonw/llm](https://github.com/simonw/llm)のプラグインとして、Claude Code SDKを使用してClaude Codeにプロンプトを送信するための実装です。

## 基本設計

### プラグイン名
- パッケージ名: `llm-claude-code`
- モデルID: `claude-code`
- エイリアス: `cc`

### 前提条件
- Claude Code CLI: `npm install -g @anthropic-ai/claude-code`
- Node.js: Claude Code CLI実行に必要
- Anthropic APIキーが設定済み（環境変数またはClaude Codeの設定）
- Python 3.10以上

## 機能仕様

### 1. 基本機能
```bash
# 基本的な使用方法
llm -m claude-code "Pythonでフィボナッチ数列を生成する関数を書いて"

# エイリアスを使用
llm -m cc "hello worldを出力するスクリプトを作成"
```

### 2. 認証
- プラグイン側での認証設定は不要
- Claude Code SDKが既存の認証情報（環境変数`ANTHROPIC_API_KEY`など）を使用
- Claude Code CLIの認証設定を継承

### 3. ツール使用
- 初期実装ではツール使用は無効（`allowed_tools=[]`）
- 将来的な拡張のため、内部的にはツール結果の処理機構を実装

### 4. オプション
- 初期実装ではLLMオプション（`-o`）は提供しない
- Claude Code SDKのデフォルト設定を使用
- `max_turns=1`で単発応答に制限
- `allowed_tools=[]`でツール使用を無効化

### 5. 出力形式

#### 5.1 メッセージタイプ
Claude Code SDKからのメッセージを処理：
- `Message`オブジェクトから`content`フィールドを抽出
- `TextBlock`オブジェクトの`text`フィールドを取得
- リスト形式のコンテンツ（複数TextBlock）に対応

#### 5.2 表示形式
```
# アシスタントメッセージ（デフォルト色）
フィボナッチ数列を生成する関数を作成します。

# ツール使用結果（色付き表示）
[Tool: Read] ファイル 'example.py' を読み込みました
[Tool: Write] ファイル 'fibonacci.py' を作成しました

# 最終結果
✓ 正常に完了しました（実行時間: 2.3秒）
```

#### 5.3 色分け仕様
- アシスタントメッセージ: デフォルト色
- ツール使用結果: 青色（ANSIエスケープコード使用）
- エラーメッセージ: 赤色
- システムメッセージ: 灰色

### 6. ストリーミング
- Claude Code SDKの非同期ストリーミングをLLMのストリーミング機能として実装
- `can_stream = True`を設定
- `anyio`を使用した非同期→同期変換
- リアルタイムでメッセージを表示

### 7. エラーハンドリング
- `ProcessError`: SDK実行エラー
- 適切なエラーメッセージをユーザーに表示
- `response.response_json`にエラー情報と実行時間を記録

## 実装構造

### ファイル構成
```
llm-claude-code/
├── pyproject.toml
├── llm_claude_code.py
├── README.md
├── LICENSE
└── tests/
    └── test_claude_code.py
```

### 主要クラスと実装

```python
from claude_code_sdk import query, ClaudeCodeOptions
import anyio

class ClaudeCode(llm.Model):
    model_id = "claude-code"
    aliases = ("cc",)
    can_stream = True
    
    def execute(self, prompt, stream, response, conversation=None):
        # anyioを使用してClaude Code SDKと連携
        if stream:
            return self._sync_stream_execute(prompt, response, start_time)
        else:
            result = anyio.run(self._execute_single, prompt)
            return [result]

@llm.hookimpl
def register_models(register):
    register(ClaudeCode())
```

## 技術的な考慮事項

### 1. 非同期処理と同期変換
- Claude Code SDKは非同期APIを提供
- LLMフレームワークは同期的なインターフェースを期待
- `anyio.run`を使用して非同期→同期変換を実装
- ストリーミング時は`_collect_async_generator`で収集後に同期ジェネレータとして返却

### 2. メッセージ処理
- `TextBlock`オブジェクトから`text`フィールドを抽出
- リスト形式のコンテンツ（複数TextBlock）をループ処理
- 文字列コンテンツ、オブジェクトコンテンツの両方に対応

### 3. プラグイン登録
- `@llm.hookimpl`デコレータを使用
- `register_models(register)`関数でモデルを登録
- `llm.default_model`は使用不可のため独自の登録機構を実装

### 4. ログ記録
- LLMのログ機能を活用
- `response.response_json`に追加情報を記録
  - 実行時間
  - モデルID
  - エラー情報

## 将来の拡張

### Phase 2（ツール使用の有効化）
- 特定のツールを有効化するオプション追加
- `-o tools read,write`のような形式

### Phase 3（高度なオプション）
- `system_prompt`のカスタマイズ
- `max_turns`の設定
- `cwd`（作業ディレクトリ）の指定

### Phase 4（会話の継続）
- LLMの会話機能を使用したセッション管理
- Claude Codeのセッション状態の保持

## テスト計画

### 単体テスト
- モデルの登録確認
- エイリアスの動作確認
- エラーハンドリングのテスト
- メッセージ処理のテスト
- カラー出力のテスト

### 統合テスト
- Claude Code SDKの`query`関数をモック化
- ストリーミング動作の確認
- TextBlockオブジェクトの処理確認
- 非同期→同期変換の動作確認

## 実装完了状況

### ✅ 完了した機能
- Claude Code SDKとの統合（`claude-code-sdk` v0.0.11）
- プラグイン登録機構
- 同期・非同期両方の実行方式
- ストリーミング対応
- TextBlockメッセージ処理
- カラー出力（ツール・エラー・成功メッセージ）
- 包括的なテストスイート
- エラーハンドリング

### 📋 技術仕様
- パッケージ: `claude-code-sdk>=0.0.11`
- 非同期ライブラリ: `anyio>=3.0.0`
- Python要件: >=3.10
- テスト: pytest + pytest-asyncio
- フォーマッタ: ruff

## 開発コマンド

### テスト実行
```bash
uv run pytest
```

### コードフォーマット
```bash
uv run ruff format
```

### リント実行（自動修正付き）
```bash
uv run ruff check --fix --extend-select I
```

### プラグインのテスト実行
```bash
uv run llm -m claude-code "こんにちは"
```

### 開発環境セットアップ
```bash
uv sync --extra test --extra dev
```

## 参考資料
- [LLM Plugin Development Guide](https://llm.datasette.io/en/stable/plugins/tutorial-model-plugin.html)
- [Claude Code SDK Documentation](https://docs.anthropic.com/en/docs/claude-code/sdk)
- [Claude Code SDK PyPI](https://pypi.org/project/claude-code-sdk/)