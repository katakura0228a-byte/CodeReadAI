# CodeReadAI

AIによるソースコード意味解析・ドキュメント生成システム

## 概要

CodeReadAIは、ソースコードをAIで意味解析し、人間が理解しやすい自然言語ドキュメントを自動生成するWebアプリケーションです。

### 解決する課題

- 大規模コードベースの全体像把握が困難
- 新メンバーのオンボーディングに時間がかかる
- 既存コードの意図・役割が不明確

### 主な機能

- **GitHubリポジトリインポート**: GitHub URLからリポジトリを直接インポート
- **階層的コード解析**: 関数・クラス → ファイル → ディレクトリ → リポジトリのボトムアップ解析
- **増分更新**: 変更があったファイルのみを再解析
- **ツリービュー**: 階層的な構造でドキュメントを閲覧

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| Frontend | Next.js 14 (App Router), TailwindCSS, React Query |
| Backend | FastAPI (Python), SQLAlchemy |
| Database | PostgreSQL |
| Job Queue | Celery + Redis |
| Parser | tree-sitter (Python, TypeScript, JavaScript, Java, Go, Rust, C, C++) |
| LLM | OpenAI API |

## クイックスタート

### 前提条件

- Docker & Docker Compose
- GitHub OAuth App (オプション: プライベートリポジトリ対応)
- OpenAI API Key

### 1. 環境変数の設定

```bash
cp .env.example .env
```

`.env`ファイルを編集:

```env
# GitHub OAuth (オプション)
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret

# OpenAI API (必須)
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5-nano

# Application
SECRET_KEY=your_random_secret_key
```

### 2. アプリケーションの起動

```bash
docker-compose up -d
```

### 3. アクセス

- **フロントエンド**: http://localhost:3000
- **バックエンドAPI**: http://localhost:8000
- **API ドキュメント**: http://localhost:8000/docs

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                        Web Frontend                             │
│                        (Next.js)                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API Server (FastAPI)                        │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│    GitHub     │      │  PostgreSQL   │      │     Redis     │
│     API       │      │               │      │  (Job Queue)  │
└───────────────┘      └───────────────┘      └───────────────┘
                                │                       │
                                └───────────┬───────────┘
                                            ▼
                            ┌───────────────────────────┐
                            │    Analysis Worker        │
                            │       (Celery)            │
                            │  - tree-sitter Parser     │
                            │  - OpenAI LLM Analyzer    │
                            └───────────────────────────┘
```

## API エンドポイント

### リポジトリ管理

| Method | Path | 説明 |
|--------|------|------|
| POST | `/api/repositories` | リポジトリ登録 |
| GET | `/api/repositories` | リポジトリ一覧 |
| GET | `/api/repositories/{id}` | リポジトリ詳細 |
| DELETE | `/api/repositories/{id}` | リポジトリ削除 |
| POST | `/api/repositories/{id}/sync` | 再解析実行 |

### 解析結果取得

| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/repositories/{id}/tree` | ファイルツリー取得 |
| GET | `/api/repositories/{id}/directories/{path}` | ディレクトリ詳細 |
| GET | `/api/repositories/{id}/files/{path}` | ファイル詳細 |
| GET | `/api/code-units/{id}` | コードユニット詳細 |

### ジョブ管理

| Method | Path | 説明 |
|--------|------|------|
| GET | `/api/jobs` | ジョブ一覧 |
| GET | `/api/jobs/{id}` | ジョブ詳細・進捗 |
| POST | `/api/jobs/{id}/cancel` | ジョブキャンセル |

## 開発

### ローカル開発環境

```bash
# バックエンド
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Celeryワーカー
celery -A app.worker.celery_app worker --loglevel=info

# フロントエンド
cd frontend
npm install
npm run dev
```

### プロジェクト構造

```
CodeReadAI/
├── backend/
│   ├── app/
│   │   ├── api/           # APIエンドポイント
│   │   ├── core/          # 設定・データベース
│   │   ├── models/        # SQLAlchemyモデル
│   │   ├── services/      # ビジネスロジック
│   │   └── worker/        # Celeryタスク
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/           # Next.js App Router
│   │   ├── components/    # Reactコンポーネント
│   │   ├── lib/           # ユーティリティ
│   │   └── types/         # TypeScript型定義
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## 対応言語

tree-sitterでサポートされる以下の言語に対応:

- Python
- TypeScript / JavaScript
- Java
- Go
- Rust
- C / C++

## ライセンス

MIT License
