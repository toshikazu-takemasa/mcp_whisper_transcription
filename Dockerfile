FROM python:3.11-slim

# システムの依存関係をインストール
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリを設定
WORKDIR /app

# 依存関係ファイルをコピー
COPY requirements.txt pyproject.toml ./

# Python依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY src/ ./src/

# パッケージをインストール
RUN pip install --no-cache-dir -e .

# 必要なディレクトリを作成
RUN mkdir -p /app/audio_files /app/output

# 環境変数のデフォルト値を設定
ENV AUDIO_FILES_PATH=/app/audio_files
ENV PYTHONUNBUFFERED=1

# MCPサーバーを起動（stdioモードで）
CMD ["mcp-whisper-transcription"]
