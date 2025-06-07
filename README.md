# MCP Whisper Transcription Server

OpenAI Whisper APIを使用した音声文字起こし用のMCP（Model Context Protocol）サーバーです。

## 機能

- **音声文字起こし**: OpenAI Whisper APIを使用した高精度な音声文字起こし
- **音声チャット**: OpenAIの音声対応モデルを使用した音声分析
- **音声変換**: 音声ファイルの形式変換（mp3, wav）
- **音声圧縮**: ファイルサイズの圧縮
- **音声合成**: テキストから音声への変換（TTS）
- **ファイル情報取得**: 音声ファイルのメタデータ取得

## サポートされる音声形式

- MP3
- WAV
- FLAC
- MP4
- MPEG
- MPGA
- M4A
- OGG

## 必要な環境

- Python 3.11以上
- OpenAI API キー

## インストール

### Dockerイメージを使用する場合（推奨）

```bash
# GitHub Container Registryから最新イメージを取得
docker pull ghcr.io/toshikazu-takemasa/mcp_whisper_transcription:latest

# MCPサーバーを起動
docker run -e OPENAI_API_KEY="your-openai-api-key" \
  -v $(pwd)/audio_files:/app/audio_files \
  ghcr.io/toshikazu-takemasa/mcp_whisper_transcription:latest
```

### devcontainerを使用する場合

1. このリポジトリをクローンします
2. VS Codeでプロジェクトを開きます
3. "Reopen in Container"を選択します
4. 環境変数を設定します：
   ```bash
   export OPENAI_API_KEY="your-openai-api-key"
   ```

### ローカル環境での使用

```bash
# 依存関係のインストール
pip install -r requirements.txt

# 開発用インストール
pip install -e .
```

## 使用方法

### MCPサーバーとして起動

```bash
python -m mcp_whisper_transcription
```

### 利用可能なツール

#### 1. transcribe_audio
音声ファイルをテキストに変換します。

```json
{
  "input_file_path": "/path/to/audio.mp3",
  "response_format": "text",
  "prompt": "音声の内容に関するヒント"
}
```

#### 2. transcribe_with_enhancement
事前定義されたプロンプトを使用して音声を文字起こしします。

```json
{
  "input_file_path": "/path/to/audio.mp3",
  "enhancement_type": "detailed"
}
```

利用可能な enhancement_type:
- `detailed`: 詳細な文字起こし（非言語音も含む）
- `storytelling`: 自然な会話形式
- `professional`: プロフェッショナルな形式
- `analytical`: 技術的な分析形式

#### 3. chat_with_audio
音声ファイルを分析し、カスタムプロンプトで処理します。

```json
{
  "input_file_path": "/path/to/audio.mp3",
  "system_prompt": "あなたは音声分析の専門家です",
  "user_prompt": "この音声の要約を作成してください"
}
```

#### 4. convert_audio
音声ファイルの形式を変換します。

```json
{
  "input_file_path": "/path/to/audio.wav",
  "target_format": "mp3"
}
```

#### 5. compress_audio
音声ファイルを圧縮します。

```json
{
  "input_file_path": "/path/to/large_audio.mp3",
  "max_mb": 25
}
```

#### 6. create_speech
テキストを音声に変換します。

```json
{
  "text_prompt": "こんにちは、これはテスト音声です。",
  "voice": "nova",
  "speed": 1.0
}
```

#### 7. get_file_support
音声ファイルの情報とサポート状況を確認します。

```json
{
  "file_path": "/path/to/audio.mp3"
}
```

## 設定

### 環境変数

- `OPENAI_API_KEY`: OpenAI APIキー（必須）
- `AUDIO_FILES_PATH`: 音声ファイルのベースパス（オプション）

## 開発

### コードフォーマット

```bash
black src/
isort src/
```

### 型チェック

```bash
mypy src/
```

### テスト実行

```bash
pytest
```

## ライセンス

MIT License

## 貢献

プルリクエストやイシューの報告を歓迎します。

## 注意事項

- OpenAI APIの使用には料金が発生します
- 大きな音声ファイルの処理には時間がかかる場合があります
- 音声ファイルのアップロード制限にご注意ください
