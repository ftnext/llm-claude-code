# LLM Claude Code Plugin Specification

## 概要

`llm-claude-code`は、[simonw/llm](https://github.com/simonw/llm)のプラグインとして、Claude Code SDKを使用してClaude Codeにプロンプトを送信するための実装です。

## 基本設計

### プラグイン名
- パッケージ名: `llm-claude-code`
- モデルID: `claude-code`
- エイリアス: `cc`

### 前提条件
- Claude Code (`claude`コマンド) がインストール済み
- Anthropic APIキーが設定済み（環境変数またはClaude Codeの設定）
- Python 3.8以上

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

### 3. ツール使用
- 初期実装ではツール使用は無効（`allowed_tools=[]`）
- 将来的な拡張のため、内部的にはツール結果の処理機構を実装

### 4. オプション
- 初期実装ではLLMオプション（`-o`）は提供しない
- Claude Code SDKのデフォルト設定を使用

### 5. 出力形式

#### 5.1 メッセージタイプ
以下のメッセージタイプを処理：
- `assistant`: Claude Codeからの応答メッセージ
- `user`: ユーザーメッセージ（内部処理用）
- `result`: 実行結果（最終メッセージ）
- `system`: システムメッセージ（初期化情報など）

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
- リアルタイムでメッセージを表示

### 7. エラーハンドリング
- `CLINotFoundError`: Claude Codeがインストールされていない場合
- `CLIConnectionError`: 接続エラー
- `ProcessError`: プロセス実行エラー
- 適切なエラーメッセージをユーザーに表示

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

### 主要クラス

```python
class ClaudeCode(llm.Model):
    model_id = "claude-code"
    aliases = ("cc",)
    can_stream = True
    
    async def execute(self, prompt, stream, response, conversation):
        # Claude Code SDKを使用した実装
        pass
```

## 技術的な考慮事項

### 1. 非同期処理
- Claude Code SDKは非同期APIを提供
- LLMの`execute`メソッド内で適切に非同期処理を扱う
- `asyncio`を使用した実装

### 2. メッセージフィルタリング
- 不要なシステムメッセージをフィルタリング
- ユーザーに関連する情報のみを表示

### 3. ログ記録
- LLMのログ機能を活用
- `response.response_json`に追加情報を記録
  - 実行時間
  - 使用されたツール（将来の拡張用）
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

### 統合テスト
- 実際のClaude Code SDKとの連携テスト
- ストリーミング動作の確認
- 各種メッセージタイプの処理確認

## 参考資料
- [LLM Plugin Development Guide](https://llm.datasette.io/en/stable/plugins/tutorial-model-plugin.html)
- [Claude Code SDK Documentation](https://docs.anthropic.com/en/docs/claude-code/sdk)
- [claude-code-sdk-python](https://github.com/anthropics/claude-code-sdk-python)