import re
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models import Repository, Directory, File, CodeUnit, AnalysisJob
from app.api.schemas import (
    RepositoryCreate,
    RepositoryResponse,
    RepositoryListResponse,
    DirectoryResponse,
    DirectoryDetailResponse,
    FileResponse,
    FileDetailResponse,
    TreeNode,
    AnalysisJobResponse,
)

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


def parse_github_url(url: str) -> tuple[str, str]:
    """Parse GitHub URL to extract owner and repo name."""
    patterns = [
        r"github\.com[:/]([^/]+)/([^/\.]+)",
        r"^([^/]+)/([^/]+)$",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1), match.group(2).replace(".git", "")
    raise ValueError(f"Invalid GitHub URL: {url}")


@router.post("", response_model=RepositoryResponse, status_code=status.HTTP_201_CREATED)
async def create_repository(
    data: RepositoryCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new repository from GitHub URL."""
    try:
        owner, name = parse_github_url(data.github_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Check if repository already exists
    existing = await db.execute(
        select(Repository).where(
            Repository.owner == owner,
            Repository.name == name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Repository already registered")

    # Create repository
    repo = Repository(
        github_url=f"https://github.com/{owner}/{name}",
        owner=owner,
        name=name,
    )
    db.add(repo)
    await db.commit()
    await db.refresh(repo)

    return repo


@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    """List all registered repositories."""
    result = await db.execute(
        select(Repository).offset(skip).limit(limit).order_by(Repository.created_at.desc())
    )
    repositories = result.scalars().all()

    count_result = await db.execute(select(func.count()).select_from(Repository))
    total = count_result.scalar()

    return RepositoryListResponse(repositories=repositories, total=total)


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get repository details."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repo_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a repository and all its data."""
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    await db.delete(repo)
    await db.commit()


@router.post("/{repo_id}/sync", response_model=AnalysisJobResponse)
async def sync_repository(
    repo_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Trigger repository sync and re-analysis."""
    from app.worker.tasks import analyze_repository

    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Determine job type (incremental if we have a commit hash)
    job_type = "incremental" if repo.last_commit_hash else "full"

    # Create analysis job
    job = AnalysisJob(
        repository_id=repo.id,
        job_type=job_type,
        status="pending",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Trigger Celery task
    analyze_repository.delay(str(job.id))

    return job


@router.get("/{repo_id}/tree", response_model=list[TreeNode])
async def get_repository_tree(
    repo_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get repository file tree structure."""
    # Verify repository exists
    result = await db.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # Get all directories and files
    dirs_result = await db.execute(
        select(Directory)
        .where(Directory.repository_id == repo_id)
        .order_by(Directory.path)
    )
    directories = dirs_result.scalars().all()

    files_result = await db.execute(
        select(File)
        .join(Directory)
        .where(Directory.repository_id == repo_id)
        .order_by(File.path)
    )
    files = files_result.scalars().all()

    # Build tree structure
    dir_map = {}
    root_nodes = []

    for d in directories:
        node = TreeNode(
            id=d.id,
            name=d.name,
            path=d.path,
            type="directory",
            summary=d.summary,
            children=[],
        )
        dir_map[d.path] = node
        if d.parent_id is None:
            root_nodes.append(node)

    # Add files to directories
    for f in files:
        file_node = TreeNode(
            id=f.id,
            name=f.name,
            path=f.path,
            type="file",
            summary=f.summary,
            language=f.language,
        )
        dir_path = "/".join(f.path.split("/")[:-1])
        if dir_path in dir_map:
            dir_map[dir_path].children.append(file_node)

    # Build directory hierarchy
    for d in directories:
        if d.parent_id:
            parent_path = "/".join(d.path.split("/")[:-1])
            if parent_path in dir_map:
                dir_map[parent_path].children.append(dir_map[d.path])

    return root_nodes


@router.get("/{repo_id}/directories/{path:path}", response_model=DirectoryDetailResponse)
async def get_directory(
    repo_id: UUID,
    path: str,
    db: AsyncSession = Depends(get_db),
):
    """Get directory details with children and files."""
    result = await db.execute(
        select(Directory)
        .options(selectinload(Directory.children), selectinload(Directory.files))
        .where(Directory.repository_id == repo_id, Directory.path == path)
    )
    directory = result.scalar_one_or_none()
    if not directory:
        raise HTTPException(status_code=404, detail="Directory not found")

    return DirectoryDetailResponse(
        id=directory.id,
        path=directory.path,
        name=directory.name,
        summary=directory.summary,
        created_at=directory.created_at,
        updated_at=directory.updated_at,
        children=[DirectoryResponse.model_validate(c) for c in directory.children],
        files=[FileResponse.model_validate(f) for f in directory.files],
    )


@router.get("/{repo_id}/files/{path:path}", response_model=FileDetailResponse)
async def get_file(
    repo_id: UUID,
    path: str,
    db: AsyncSession = Depends(get_db),
):
    """Get file details with code units."""
    result = await db.execute(
        select(File)
        .options(selectinload(File.code_units))
        .join(Directory)
        .where(Directory.repository_id == repo_id, File.path == path)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    return FileDetailResponse(
        id=file.id,
        path=file.path,
        name=file.name,
        language=file.language,
        summary=file.summary,
        line_count=file.line_count,
        created_at=file.created_at,
        updated_at=file.updated_at,
        code_units=[
            {
                "id": cu.id,
                "type": cu.type,
                "name": cu.name,
                "start_line": cu.start_line,
                "end_line": cu.end_line,
                "signature": cu.signature,
                "description": cu.description,
                "metadata": cu.metadata,
                "created_at": cu.created_at,
                "updated_at": cu.updated_at,
            }
            for cu in file.code_units
            if cu.parent_id is None  # Only top-level units
        ],
    )
