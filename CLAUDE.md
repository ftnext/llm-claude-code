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
- 複数のツールが使用可能（`allowed_tools=["Read", "Write", "Bash", "TodoRead", "TodoWrite"]`）
- ツール実行過程をリアルタイムで表示
- ファイル操作、コード実行、タスク管理が可能

#### 3.1 使用可能なツール
- **Read**: ファイル読み取り
- **Write**: ファイル作成・書き込み
- **Bash**: コマンド実行
- **TodoRead**: タスクリスト読み取り
- **TodoWrite**: タスクリスト書き込み

### 4. オプション
- LLMオプション（`-o`）をサポート
- Claude Code SDKのデフォルト設定を使用
- `max_turns=1`で単発応答に制限
- `allowed_tools=["Read", "Write", "Bash", "TodoRead", "TodoWrite"]`で多様なツールを有効化

#### 4.1 デバッグオプション
```bash
# デバッグモードを有効化
llm -m claude-code -o debug true "プロンプト"

# エイリアスでの使用
llm -m cc -o debug true "プロンプト"
```

デバッグモードでは以下の情報を出力：
- 実行されるツールの詳細情報
- Claude Code SDKへの送信パラメータ
- メッセージ処理の過程
- エラー発生時の詳細情報

#### 4.2 デバッグ出力例
```
🐛 [DEBUG] Starting execution with debug mode enabled
🐛 [DEBUG] Prompt: Hello Worldを出力するPythonスクリプトを作成
🐛 [DEBUG] Stream mode: true
🐛 [DEBUG] Streaming with options: ClaudeCodeOptions(allowed_tools=['Read', 'Write'], max_turns=1, ...)
🐛 [DEBUG] Streaming message type: AssistantMessage
🐛 [DEBUG] Streaming content type: list
🐛 [DEBUG] Tool use detected: Write
🐛 [DEBUG] Tool input: {'file_path': '/path/to/hello.py', 'content': 'print("Hello World")'}
🔧 [Tool: Write] Creating file '/path/to/hello.py'
🐛 [DEBUG] Tool use detected: Bash
🐛 [DEBUG] Tool input: {'command': 'python /path/to/hello.py'}
🔧 [Tool: Bash] Executing: python /path/to/hello.py
✅ Tool execution completed
```

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
🔧 [Tool: Read] Reading file 'example.py'
🔧 [Tool: Write] Creating file 'fibonacci.py'
🔧 [Tool: Bash] Executing: python fibonacci.py
🔧 [Tool: TodoWrite] Writing 3 todo items
✅ Tool execution completed

# アシスタント応答
フィボナッチ数列を生成する関数を作成しました。
```

#### 5.3 色分け仕様
- アシスタントメッセージ: デフォルト色
- ツール使用結果: 青色（🔧 [Tool: ...] 形式）
- ツール完了: 緑色（✅ Tool execution completed）
- エラーメッセージ: 赤色
- 成功メッセージ: 緑色（✓ で始まる）

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
from pydantic import Field
from typing import Optional

class ClaudeCode(llm.Model):
    model_id = "claude-code"
    can_stream = True
    
    class Options(llm.Options):
        debug: Optional[bool] = Field(
            description="Enable debug output to show tool execution details",
            default=False
        )
    
    def execute(self, prompt, stream, response, conversation=None):
        # デバッグオプションの取得
        debug = False
        if hasattr(prompt, 'options') and prompt.options:
            debug = prompt.options.debug or False
        
        # anyioを使用してClaude Code SDKと連携
        if stream:
            return self._sync_stream_execute(prompt, response, start_time, debug)
        else:
            result = anyio.run(self._execute_single, prompt, debug)
            return [result]

@llm.hookimpl
def register_models(register):
    register(ClaudeCode(), aliases=("cc",))
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
- `ToolUseBlock`の検出とツール実行過程の表示

### 3. プラグイン登録
- `@llm.hookimpl`デコレータを使用
- `register(ClaudeCode(), aliases=("cc",))`でエイリアス付きで登録
- LLMフレームワークの公式エイリアス登録方法を使用

### 4. ログ記録
- LLMのログ機能を活用
- `response.response_json`に追加情報を記録
  - 実行時間
  - モデルID
  - エラー情報

## 将来の拡張

### Phase 2（追加ツールの有効化）
- より多くのツールを有効化するオプション追加
- Bash、Glob、Grepなどの追加ツール対応

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
- プラグイン登録機構（エイリアス`cc`対応）
- 同期・非同期両方の実行方式
- ストリーミング対応
- TextBlockメッセージ処理
- 5つのツールの使用可能（Read, Write, Bash, TodoRead, TodoWrite）
- ツール実行過程のリアルタイム表示
- カラー出力（ツール・エラー・成功メッセージ）
- 包括的なテストスイート
- エラーハンドリング
- **デバッグモード（`-o debug true`）**
  - 実行過程の詳細出力
  - ツール使用の詳細情報
  - メッセージ処理の透明性向上
  - 問題診断の支援

### 📋 技術仕様
- パッケージ: `claude-code-sdk>=0.0.11`
- 非同期ライブラリ: `anyio>=3.0.0`
- Python要件: >=3.10
- テスト: pytest + pytest-asyncio
- フォーマッタ: ruff
- オプション管理: pydantic Field を使用したLLM標準オプション

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
# 基本的なテスト
uv run llm -m claude-code "こんにちは"

# エイリアスでのテスト
uv run llm -m cc "こんにちは"

# ツール使用のテスト
uv run llm -m cc "Hello Worldを出力するPythonスクリプトを作成"

# デバッグモードでのテスト
uv run llm -m cc -o debug true "Hello Worldを出力するPythonスクリプトを作成"
```

### 開発環境セットアップ
```bash
uv sync --extra test --extra dev
```

## 参考資料
- [LLM Plugin Development Guide](https://llm.datasette.io/en/stable/plugins/tutorial-model-plugin.html)
- [Claude Code SDK Documentation](https://docs.anthropic.com/en/docs/claude-code/sdk)
- [Claude Code SDK PyPI](https://pypi.org/project/claude-code-sdk/)