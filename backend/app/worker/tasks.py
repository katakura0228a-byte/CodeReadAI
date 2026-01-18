import os
from datetime import datetime
from uuid import UUID
from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import get_settings
from app.core.database import Base
from app.models import Repository, Directory, File, CodeUnit, AnalysisJob
from app.services.git_service import GitService
from app.services.parser_service import ParserService
from app.services.llm_service import LLMService

settings = get_settings()

# Sync database connection for Celery worker
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine)


def get_sync_db() -> Session:
    return SessionLocal()


@shared_task(bind=True, name="analyze_repository")
def analyze_repository(self, job_id: str):
    """Main task to analyze a repository."""
    db = get_sync_db()
    try:
        job = db.execute(select(AnalysisJob).where(AnalysisJob.id == UUID(job_id))).scalar_one()
        repo = db.execute(select(Repository).where(Repository.id == job.repository_id)).scalar_one()

        # Update job status
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()

        git_service = GitService()
        parser_service = ParserService()
        llm_service = LLMService()

        # Step 1: Clone or pull repository
        _, commit_hash, changed_files = git_service.clone_or_pull(repo.owner, repo.name)

        # For incremental updates, filter to only changed files
        if job.job_type == "incremental" and repo.last_commit_hash:
            files_to_process = changed_files
        else:
            # Full analysis - get all supported files
            files_to_process = _get_all_supported_files(
                git_service.get_repo_path(repo.owner, repo.name),
                parser_service
            )

        job.total_files = len(files_to_process)
        db.commit()

        # Step 2: Process files
        for i, file_path in enumerate(files_to_process):
            try:
                _process_file(
                    db, repo, file_path, git_service, parser_service, llm_service
                )
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")

            job.processed_files = i + 1
            job.progress = int((i + 1) / len(files_to_process) * 80) if files_to_process else 0
            db.commit()

        # Step 3: Generate directory summaries (bottom-up)
        _generate_directory_summaries(db, repo, llm_service)
        job.progress = 90
        db.commit()

        # Step 4: Generate repository summary
        _generate_repository_summary(db, repo, llm_service)

        # Update repository and job
        repo.last_commit_hash = commit_hash
        job.status = "completed"
        job.progress = 100
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        job = db.execute(select(AnalysisJob).where(AnalysisJob.id == UUID(job_id))).scalar_one()
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.utcnow()
        db.commit()
        raise
    finally:
        db.close()


def _get_all_supported_files(repo_path, parser_service: ParserService) -> list[str]:
    """Get all files with supported extensions."""
    files = []
    for root, _, filenames in os.walk(repo_path):
        if ".git" in root:
            continue
        for filename in filenames:
            file_path = os.path.join(root, filename)
            rel_path = os.path.relpath(file_path, repo_path)

            # Skip hidden files and common non-code files
            if filename.startswith("."):
                continue
            if filename in ["package-lock.json", "yarn.lock", "Cargo.lock"]:
                continue

            # Check if language is supported
            if parser_service.detect_language(rel_path):
                files.append(rel_path)

    return files


def _process_file(
    db: Session,
    repo: Repository,
    file_path: str,
    git_service: GitService,
    parser_service: ParserService,
    llm_service: LLMService,
):
    """Process a single file."""
    # Ensure directory structure exists
    dir_path = os.path.dirname(file_path)
    directory = _ensure_directory(db, repo, dir_path)

    # Read file content
    content = git_service.get_file_content(repo.owner, repo.name, file_path)
    content_hash = git_service.get_file_hash(repo.owner, repo.name, file_path)

    # Check if file already exists and hasn't changed
    existing_file = db.execute(
        select(File).where(
            File.directory_id == directory.id,
            File.path == file_path
        )
    ).scalar_one_or_none()

    if existing_file and existing_file.content_hash == content_hash:
        # File hasn't changed, skip
        return

    # Parse file
    parse_result = parser_service.parse_file(file_path, content)
    if not parse_result:
        return

    # Create or update file record
    if existing_file:
        file_record = existing_file
        file_record.content_hash = content_hash
        file_record.language = parse_result.language
        file_record.line_count = parse_result.line_count
        # Delete existing code units for re-analysis
        db.execute(
            CodeUnit.__table__.delete().where(CodeUnit.file_id == file_record.id)
        )
    else:
        file_record = File(
            directory_id=directory.id,
            path=file_path,
            name=os.path.basename(file_path),
            language=parse_result.language,
            content_hash=content_hash,
            line_count=parse_result.line_count,
        )
        db.add(file_record)

    db.flush()

    # Process code units
    code_unit_summaries = []
    for unit_info in parse_result.code_units:
        code_unit = _create_code_unit(
            db, file_record, unit_info, llm_service, parse_result.language
        )
        if code_unit and code_unit.description:
            code_unit_summaries.append({
                "type": code_unit.type,
                "name": code_unit.name,
                "description": code_unit.description,
            })

    # Generate file summary
    if code_unit_summaries:
        file_record.summary = llm_service.summarize_file(
            file_path, code_unit_summaries, parse_result.language
        )

    db.commit()


def _ensure_directory(db: Session, repo: Repository, dir_path: str) -> Directory:
    """Ensure directory and parent directories exist."""
    if not dir_path:
        # Root directory
        root_dir = db.execute(
            select(Directory).where(
                Directory.repository_id == repo.id,
                Directory.path == ""
            )
        ).scalar_one_or_none()

        if not root_dir:
            root_dir = Directory(
                repository_id=repo.id,
                path="",
                name=repo.name,
            )
            db.add(root_dir)
            db.flush()

        return root_dir

    # Check if directory exists
    existing = db.execute(
        select(Directory).where(
            Directory.repository_id == repo.id,
            Directory.path == dir_path
        )
    ).scalar_one_or_none()

    if existing:
        return existing

    # Ensure parent exists
    parent_path = os.path.dirname(dir_path)
    parent = _ensure_directory(db, repo, parent_path)

    # Create directory
    directory = Directory(
        repository_id=repo.id,
        parent_id=parent.id,
        path=dir_path,
        name=os.path.basename(dir_path),
    )
    db.add(directory)
    db.flush()

    return directory


def _create_code_unit(
    db: Session,
    file_record: File,
    unit_info,
    llm_service: LLMService,
    language: str,
    parent_id: UUID | None = None,
) -> CodeUnit:
    """Create a code unit and analyze it."""
    # Generate description using LLM
    description = None
    try:
        description = llm_service.analyze_code_unit(
            unit_info.source_code,
            unit_info.type,
            unit_info.name,
            language,
        )
    except Exception as e:
        print(f"Error analyzing {unit_info.name}: {e}")

    code_unit = CodeUnit(
        file_id=file_record.id,
        parent_id=parent_id,
        type=unit_info.type,
        name=unit_info.name,
        start_line=unit_info.start_line,
        end_line=unit_info.end_line,
        signature=unit_info.signature,
        description=description,
        metadata=unit_info.metadata,
    )
    db.add(code_unit)
    db.flush()

    # Process children (nested classes/methods)
    for child_info in unit_info.children:
        _create_code_unit(
            db, file_record, child_info, llm_service, language, parent_id=code_unit.id
        )

    return code_unit


def _generate_directory_summaries(
    db: Session, repo: Repository, llm_service: LLMService
):
    """Generate summaries for directories bottom-up."""
    # Get all directories sorted by depth (deepest first)
    directories = db.execute(
        select(Directory)
        .where(Directory.repository_id == repo.id)
        .order_by(Directory.path.desc())
    ).scalars().all()

    for directory in directories:
        # Get file summaries
        files = db.execute(
            select(File).where(File.directory_id == directory.id)
        ).scalars().all()
        file_summaries = [
            {"name": f.name, "summary": f.summary}
            for f in files if f.summary
        ]

        # Get subdirectory summaries
        subdirs = db.execute(
            select(Directory).where(Directory.parent_id == directory.id)
        ).scalars().all()
        subdir_summaries = [
            {"name": d.name, "summary": d.summary}
            for d in subdirs if d.summary
        ]

        if file_summaries or subdir_summaries:
            try:
                directory.summary = llm_service.summarize_directory(
                    directory.path or repo.name,
                    file_summaries,
                    subdir_summaries,
                )
            except Exception as e:
                print(f"Error summarizing directory {directory.path}: {e}")

    db.commit()


def _generate_repository_summary(
    db: Session, repo: Repository, llm_service: LLMService
):
    """Generate repository-level summary."""
    # Get root-level items
    root_items = []

    # Root directory files
    root_dir = db.execute(
        select(Directory).where(
            Directory.repository_id == repo.id,
            Directory.path == ""
        )
    ).scalar_one_or_none()

    if root_dir:
        root_files = db.execute(
            select(File).where(File.directory_id == root_dir.id)
        ).scalars().all()
        root_items.extend([
            {"path": f.name, "summary": f.summary}
            for f in root_files if f.summary
        ])

        root_subdirs = db.execute(
            select(Directory).where(Directory.parent_id == root_dir.id)
        ).scalars().all()
        root_items.extend([
            {"path": d.name + "/", "summary": d.summary}
            for d in root_subdirs if d.summary
        ])

    if root_items:
        try:
            repo.summary = llm_service.summarize_repository(repo.name, root_items)
        except Exception as e:
            print(f"Error summarizing repository: {e}")

    db.commit()
