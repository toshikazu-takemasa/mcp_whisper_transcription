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

# ポートを公開
EXPOSE 30007

# MCPサーバーを起動
CMD ["python", "-m", "mcp_whisper_transcription"]
