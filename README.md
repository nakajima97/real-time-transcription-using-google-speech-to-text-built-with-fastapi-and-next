# リアルタイム文字起こしアプリケーション

Google Cloud Speech-to-Text APIを使用したリアルタイム文字起こしアプリケーションです。FastAPIとNext.jsを使用して構築されています。

## 機能

- リアルタイムでの音声認識
- 日本語対応

## 必要要件

### フロントエンド
- Node.js 18.0.0以上
- yarn

### バックエンド
- Docker
- Docker Compose

### その他
- Google Cloud Platform アカウント
- Google Cloud Speech-to-Text API の有効化
- サービスアカウントキー（JSON形式）

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/real-time-transcription-using-google-speech-to-text-built-with-fastapi-and-next.git
cd real-time-transcription-using-google-speech-to-text-built-with-fastapi-and-next
```

### 2. フロントエンドのセットアップ

```bash
cd frontend
yarn install
```

環境変数の設定:
```bash
cp .env.example .env
```
必要に応じて `.env` ファイルの内容を編集してください。

### 3. バックエンドのセットアップ

1. Google Cloud の設定:
   - Google Cloud Console で新しいプロジェクトを作成
   - Speech-to-Text API を有効化
   - サービスアカウントを作成し、キーをJSONとしてダウンロード
   - ダウンロードしたJSONファイルを `server/api/google-cloud-key.json` として配置

2. 環境変数の設定:
   ```bash
   cd server/api
   cp .env.example .env
   ```
   必要に応じて `.env` ファイルの内容を編集してください。

3. Dockerコンテナの起動:
   ```bash
   cd server
   docker compose up -d
   ```

## アプリケーションの起動

### フロントエンド

```bash
cd frontend
yarn dev
```

フロントエンドは http://localhost:3000 で起動します。

### バックエンド

バックエンドは Docker Compose によって自動的に http://localhost:8000 で起動します。

コンテナのログを確認する場合:
```bash
docker compose logs -f api
```

## 使用方法

1. ブラウザで http://localhost:3000 にアクセス
2. 「録音を開始」ボタンをクリック
3. マイクへのアクセスを許可
4. 話し始めると、リアルタイムで文字起こしが表示されます

## 注意事項

- マイクへのアクセス権限が必要です
- Google Cloud Speech-to-Text API の利用料金が発生する可能性があります
- 安定したインターネット接続が必要です

## トラブルシューティング

### コンテナの再起動
```bash
cd server
docker compose restart api
```

### ログの確認
```bash
docker compose logs -f api
```

### コンテナの停止
```bash
docker compose down
```
