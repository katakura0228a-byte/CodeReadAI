from openai import OpenAI
from app.core.config import get_settings

settings = get_settings()


class LLMService:
    """Service for LLM-based code analysis."""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model

    def analyze_code_unit(
        self, code: str, unit_type: str, name: str, language: str
    ) -> str:
        """Generate description for a function/class/method."""
        prompt = f"""以下の{language}コードを解析し、日本語で説明してください。

【出力形式】
- 概要: 1-2文でこの{unit_type}の目的を説明
- 処理内容: 主要な処理ステップを箇条書き
- 引数: 各引数の役割（あれば）
- 戻り値: 戻り値の説明（あれば）
- 注意点: 使用上の注意や依存関係（あれば）

【コード】
```{language}
{code}
```"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "あなたはソースコードを解析し、わかりやすい日本語ドキュメントを生成するエキスパートです。簡潔かつ正確な説明を心がけてください。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=1000,
        )

        return response.choices[0].message.content

    def summarize_file(
        self, file_path: str, code_unit_summaries: list[dict], language: str
    ) -> str:
        """Generate file-level summary from code unit summaries."""
        summaries_text = "\n".join(
            f"- {u['type']} `{u['name']}`: {u['description'][:200]}..."
            for u in code_unit_summaries
            if u.get("description")
        )

        if not summaries_text:
            summaries_text = "（解析対象のコードユニットなし）"

        prompt = f"""以下はファイル内の各関数・クラスの説明です。
これらを踏まえ、このファイル全体の役割を2-3文で要約してください。

【ファイルパス】{file_path}
【言語】{language}

【含まれる要素】
{summaries_text}

【出力形式】
ファイルの役割を2-3文で簡潔に説明してください。"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "あなたはソースコードを解析し、わかりやすい日本語ドキュメントを生成するエキスパートです。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        return response.choices[0].message.content

    def summarize_directory(
        self, dir_path: str, file_summaries: list[dict], subdir_summaries: list[dict]
    ) -> str:
        """Generate directory-level summary from file and subdirectory summaries."""
        files_text = "\n".join(
            f"- `{f['name']}`: {f['summary'][:150]}..."
            for f in file_summaries
            if f.get("summary")
        )
        subdirs_text = "\n".join(
            f"- `{d['name']}/`: {d['summary'][:150]}..."
            for d in subdir_summaries
            if d.get("summary")
        )

        prompt = f"""以下はディレクトリ内のファイルとサブディレクトリの説明です。
このディレクトリ（モジュール）全体の役割を2-3文で要約してください。

【ディレクトリパス】{dir_path}

【ファイル】
{files_text or "（ファイルなし）"}

【サブディレクトリ】
{subdirs_text or "（サブディレクトリなし）"}

【出力形式】
このディレクトリの役割を2-3文で簡潔に説明してください。"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "あなたはソースコードを解析し、わかりやすい日本語ドキュメントを生成するエキスパートです。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=500,
        )

        return response.choices[0].message.content

    def summarize_repository(
        self, repo_name: str, root_summaries: list[dict]
    ) -> str:
        """Generate repository-level summary from root directories and files."""
        content_text = "\n".join(
            f"- `{item['path']}`: {item['summary'][:150]}..."
            for item in root_summaries
            if item.get("summary")
        )

        prompt = f"""以下はリポジトリのルートにあるファイルとディレクトリの説明です。
このリポジトリ全体の概要を3-5文で説明してください。

【リポジトリ名】{repo_name}

【ルートの構成】
{content_text or "（コンテンツなし）"}

【出力形式】
- リポジトリの目的・用途
- 主要な機能やモジュール
- 技術スタック（判別可能な場合）"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "あなたはソースコードを解析し、わかりやすい日本語ドキュメントを生成するエキスパートです。",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=800,
        )

        return response.choices[0].message.content
